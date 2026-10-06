"""Wire values <-> Python objects, driven by the generated schema.

Inputs : image/labels -> ndarray (TIFF path or shared-memory ndarray), table -> DataFrame (CSV path),
         file -> Path, scalars coerced and range-checked.
Outputs: ndarray -> TIFF, DataFrame/dict/list -> CSV, matrices -> JSON, dict -> JSON.
numpy/pandas/tifffile are imported lazily, only when a tool actually uses those types.
"""

import math
from pathlib import Path
from typing import Any

from .structures import Result, ToolSchema
from .types import ToolError

DEFAULT_AXES = {2: "YX", 3: "ZYX", 4: "CZYX"}


def load_inputs(schema: ToolSchema, inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate `inputs` against the tool schema and return keyword arguments for the tool function."""
    kwargs = {}
    for param in schema["inputs"]:
        name, value = param["name"], inputs.get(param["name"])
        if value is None:
            if param["required"]:
                raise ToolError("missing_parameter", "'%s' is required" % param["label"])
            kwargs[name] = param.get("default")
            continue
        kwargs[name] = _load_one(param, value)
    return kwargs


def _load_one(param, value):
    kind, name = param["type"], param["name"]
    if kind in ("image", "labels"):
        return _check_dimensions(param, _read_image(value))
    if kind == "table":
        import pandas as pd

        return pd.read_csv(value)
    if kind == "file":
        return Path(value)
    if kind == "folder":
        path = Path(value)
        if not path.is_dir():
            raise ToolError("folder_not_found", "'%s': folder not found: %s" % (param["label"], path))
        return path
    if kind == "integer":
        if isinstance(value, bool) or int(value) != value:
            raise ToolError("invalid_parameter", "'%s' must be an integer" % param["label"])
        return _check_range(param, int(value))
    if kind == "float":
        number = float(value)
        if not math.isfinite(number):
            raise ToolError("invalid_parameter", "'%s' must be a finite number" % param["label"])
        return _check_range(param, number)
    if kind == "boolean":
        return bool(value)
    if kind == "choice":
        if value not in param["choices"]:
            raise ToolError("invalid_parameter", "'%s' must be one of %s" % (name, param["choices"]))
        return value
    return str(value)


def _check_range(param, value):
    if "minimum" in param and value < param["minimum"]:
        raise ToolError("invalid_parameter", "'%s' must be >= %s" % (param["label"], param["minimum"]))
    if "maximum" in param and value > param["maximum"]:
        raise ToolError("invalid_parameter", "'%s' must be <= %s" % (param["label"], param["maximum"]))
    return value


def _check_dimensions(param, array):
    """A declared `Axes("YX")` means the tool wants exactly that many dimensions: say so clearly instead of failing deep inside."""
    axes = param.get("axes")
    if axes and array.ndim != len(axes):
        raise ToolError(
            "wrong_dimensions",
            "'%s' must be a %dD image (%s) but got %dD with shape %s"
            % (param["label"], len(axes), axes, array.ndim, tuple(array.shape)),
        )
    return array


def _read_image(value):
    if isinstance(value, dict) and value.get("appose_type") == "ndarray":
        return _ndarray_from_shared_memory(value)
    path = Path(value)
    if not path.is_file():
        raise ToolError("file_not_found", "image file not found: %s" % path)
    try:
        if path.suffix.lower() in (".tif", ".tiff", ".btf"):  # also .ome.tif
            import tifffile

            array = tifffile.imread(path)
        else:
            array = _read_other_format(path)
        if array.size == 0:  # tifffile only warns about some damaged headers and returns an empty array
            raise ToolError("unreadable_image", "cannot read %s: the file contains no image data" % path.name)
        return array
    except ToolError:
        raise
    except Exception as error:  # noqa: BLE001 - any reader failure is the user's file problem
        raise ToolError("unreadable_image", "cannot read %s: %s" % (path.name, error)) from error


def _read_other_format(path):
    """PNG/JPEG/BMP/... through imageio when the app has it; otherwise say what to do."""
    try:
        import imageio.v3 as iio
    except ImportError:
        raise ToolError(
            "unsupported_format",
            "'%s' is not a TIFF and this app has no imageio to read it; save it as TIFF" % path.name,
        ) from None
    return iio.imread(path)


def _ndarray_from_shared_memory(descriptor):
    from multiprocessing import shared_memory

    import numpy as np

    shm = shared_memory.SharedMemory(name=descriptor["shm"]["name"])
    try:
        view = np.ndarray(tuple(descriptor["shape"]), dtype=descriptor["dtype"], buffer=shm.buf)
        return view.copy()
    finally:
        shm.close()


def build_results(schema: ToolSchema, returned: Any, job_dir: str | Path) -> list[Result]:
    """Turn the tool's return value into the list of typed results declared by the schema."""
    outputs = schema["outputs"]
    values = [returned] if len(outputs) == 1 else list(returned or [])
    if len(outputs) != len(values):
        raise ToolError("bad_return", "tool returned %d values, declared %d" % (len(values), len(outputs)))
    return [
        _write_one(out, value, Path(job_dir)) for out, value in zip(outputs, values)
    ]  # lengths checked just above (strict= needs 3.10)


def _write_one(out, value, job_dir):
    kind, name = out["type"], out["name"]
    if kind in ("image", "labels"):
        import numpy as np
        import tifffile

        array = portable_dtype(np.asarray(value))
        path = job_dir / (name + ".tif")
        tifffile.imwrite(path, array)
        axes = out.get("axes") or DEFAULT_AXES.get(array.ndim, "")
        return {"type": kind, "name": name, "path": str(path), "axes": axes}
    if kind == "table":
        import pandas as pd

        frame = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
        path = job_dir / (name + ".csv")
        frame.to_csv(path, index=False)
        return {"type": "table", "name": name, "path": str(path)}
    if kind == "file":
        return {"type": "file", "name": name, "path": str(value)}
    if kind == "values":
        return {"type": "values", "name": name, "values": {str(k): _plain(v) for k, v in dict(value).items()}}
    if kind == "affine":
        return {"type": "affine", "name": name, "matrix_yx": _as_3x3(value), **out.get("display", {})}
    raise ToolError("bad_return", "unsupported output type %r" % kind)


def _plain(value):
    """A value that survives strict JSON: numpy scalars become Python numbers (not strings), NaN/inf become null."""
    if hasattr(value, "item") and getattr(value, "ndim", None) == 0:  # numpy scalar or 0-d array
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return value


def _as_3x3(matrix):
    import numpy as np

    m = np.asarray(matrix, float)
    if m.shape == (2, 3):
        m = np.vstack([m, [0, 0, 1]])
    if m.shape != (3, 3):
        raise ToolError("bad_return", "affine must be 3x3 (got %s)" % (m.shape,))
    return m.tolist()


def portable_dtype(array: Any) -> Any:
    """Cast to a dtype every host can open (ImageJ's TIFF reader has no float64, int64, uint32/64, bool or int8)."""
    import numpy as np

    kind, size = array.dtype.kind, array.dtype.itemsize
    if kind == "b":
        return array.astype(np.uint8)
    if kind == "f":
        return array if array.dtype == np.float32 else array.astype(np.float32)
    if kind == "u":
        return array if size <= 2 else array.astype(np.float32)
    if kind == "i":
        if size == 1:
            return array.astype(np.int16)
        return array if size == 2 else array.astype(np.float32)
    return array
