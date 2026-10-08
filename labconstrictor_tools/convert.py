"""Wire values <-> Python objects, driven by the generated schema.

Inputs : image/labels -> ndarray (TIFF path or shared-memory ndarray), table -> DataFrame (CSV path),
         file -> Path, scalars coerced and range-checked.
Outputs: ndarray -> TIFF, DataFrame/dict/list -> CSV, matrices -> JSON, dict -> JSON.
numpy/pandas/tifffile are imported lazily, only when a tool actually uses those types.
"""

import logging
import math
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .structures import OutputSchema, ParamSchema, Result, ToolSchema
from .types import ToolError

UINT16_MAX = (
    65535  # integer images within the 16-bit ranges are narrowed to uint16 / int16, which every host opens
)
INT16_MIN, INT16_MAX = -32768, 32767
DEFAULT_AXES = {2: "YX", 3: "ZYX", 4: "CZYX"}
IMAGE_DTYPE_KINDS = (
    "biuf"  # bool, signed/unsigned integer, float: the only element kinds a TIFF that hosts can open holds
)
SHARED_MEMORY_DTYPE_KINDS = (
    "biufc"  # what a host may put in a shared-memory block (complex is read, the tool decides)
)
AFFINE_SIZE = 3
_PLAIN_TYPE_NAMES = {
    str: "text",
    bytes: "bytes",
    list: "a list",
    tuple: "a list",
    dict: "an object",
    bool: "true/false",
    int: "an integer",
    float: "a number",
    type(None): "nothing (None)",
}


def _describe_type(value: Any) -> str:
    """The kind of `value` in the words a person uses, for error messages ('text', 'a list', ...)."""
    return _PLAIN_TYPE_NAMES.get(type(value), "a value of type %s" % type(value).__name__)


def _is_json_number(value: Any) -> bool:
    """True for a JSON number (int or float, never a boolean): the only thing an integer/float parameter accepts."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _path_text(label: str, value: Any) -> Path:
    """The path a host sent: it must be text (a number, list or object is a mistake of the host, not a file name)."""
    if not isinstance(value, str):
        raise ToolError(
            "invalid_parameter",
            "'%s' must be a path (text), got %s: the host must send the file or folder path as text"
            % (label, _describe_type(value)),
        )
    return Path(value)


def load_inputs(schema: ToolSchema, inputs: dict[str, Any], fn: Any = None) -> dict[str, Any]:
    """Validate `inputs` against the tool schema and return keyword arguments for the tool function.
    With `fn`, a `choice` parameter annotated with an Enum arrives as that Enum member (not as its value)."""
    kwargs: dict[str, Any] = {}
    for param in schema["inputs"]:
        name, value = param["name"], inputs.get(param["name"])
        if value is None:
            if param["required"]:
                raise ToolError("missing_parameter", "'%s' is required" % param["label"])
            kwargs[name] = param.get("default")
            continue
        kwargs[name] = _load_one(param, value)
    return _restore_enums(fn, kwargs) if fn is not None else kwargs


def _restore_enums(fn: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    import enum
    from typing import get_type_hints

    from .introspection import _unwrap

    hints = get_type_hints(fn, include_extras=True)
    for name, value in kwargs.items():
        if value is None or name not in hints:
            continue
        base = _unwrap(hints[name])[0]
        if isinstance(base, type) and issubclass(base, enum.Enum):
            kwargs[name] = base(value)
    return kwargs


def _load_one(param: ParamSchema, value: Any) -> Any:
    kind, name = param["type"], param["name"]
    if kind in ("image", "labels"):
        array = _read_image(value, param["label"])
        if array.size == 0:  # a file is checked while reading; shared memory is checked here
            raise ToolError(
                "empty_image", "'%s' contains no image data (shape %s)" % (param["label"], tuple(array.shape))
            )
        return _check_dimensions(param, array)
    if kind == "table":
        import pandas as pd

        return pd.read_csv(value)
    if kind == "file":
        return _path_text(param["label"], value)
    if kind == "folder":
        path = _path_text(param["label"], value)
        if not path.is_dir():
            raise ToolError("folder_not_found", "'%s': folder not found: %s" % (param["label"], path))
        return path
    if kind == "integer":
        if not _is_json_number(value):
            raise ToolError(
                "invalid_parameter",
                "'%s' must be an integer, got %s" % (param["label"], _describe_type(value)),
            )
        if isinstance(value, float) and not (math.isfinite(value) and value.is_integer()):
            raise ToolError("invalid_parameter", "'%s' must be an integer" % param["label"])
        return _check_range(param, int(value))
    if kind == "float":
        if isinstance(value, bool):
            raise ToolError("invalid_parameter", "'%s' must be a number, not true/false" % param["label"])
        if not _is_json_number(value):
            raise ToolError(
                "invalid_parameter", "'%s' must be a number, got %s" % (param["label"], _describe_type(value))
            )
        try:
            number = float(value)
        except OverflowError:  # an integer beyond the float range
            number = math.inf
        if not math.isfinite(number):
            raise ToolError("invalid_parameter", "'%s' must be a finite number" % param["label"])
        return _check_range(param, number)
    if kind == "boolean":
        if not isinstance(value, bool):  # bool("false") is True: never guess
            raise ToolError(
                "invalid_parameter", "'%s' must be true or false, got %r" % (param["label"], value)
            )
        return value
    if kind == "choice":
        if not any(
            type(value) is type(c) and value == c for c in param["choices"]
        ):  # 1 == True in Python: compare types too
            raise ToolError("invalid_parameter", "'%s' must be one of %s" % (name, param["choices"]))
        return value
    return str(value)


def _check_range(param: ParamSchema, value: Any) -> Any:
    if "minimum" in param and value < param["minimum"]:
        raise ToolError("invalid_parameter", "'%s' must be >= %s" % (param["label"], param["minimum"]))
    if "maximum" in param and value > param["maximum"]:
        raise ToolError("invalid_parameter", "'%s' must be <= %s" % (param["label"], param["maximum"]))
    return value


def _check_dimensions(param: ParamSchema, array: Any) -> Any:
    """A declared `Axes("YX")` means the tool wants exactly that many dimensions: say so clearly instead of failing deep inside."""
    axes = param.get("axes")
    if axes and array.ndim != len(axes):
        raise ToolError(
            "wrong_dimensions",
            "'%s' must be a %dD image (%s) but got %dD with shape %s"
            % (param["label"], len(axes), axes, array.ndim, tuple(array.shape)),
        )
    return array


def _read_image(value: Any, label: str = "image") -> Any:
    if isinstance(value, dict) and value.get("appose_type") == "ndarray":
        return _ndarray_from_shared_memory(value, label)
    path = _path_text(label, value)
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
    except (
        Exception
    ) as error:  # readers raise anything for a bad file: becomes a ToolError for the person, traceback logged
        logging.getLogger("labconstrictor.convert").error("cannot read image %s", path, exc_info=True)
        raise ToolError("unreadable_image", "cannot read %s: %s" % (path.name, error)) from error


def _read_other_format(path: Path) -> Any:
    """PNG/JPEG/BMP/... through imageio when the app has it; otherwise say what to do."""
    try:
        import imageio.v3 as iio
    except ImportError:
        raise ToolError(
            "unsupported_format",
            "'%s' is not a TIFF and this app has no imageio to read it; save it as TIFF" % path.name,
        ) from None
    return iio.imread(path)


def _ndarray_from_shared_memory(descriptor: dict[str, Any], label: str = "image") -> Any:
    """Copy the image out of the host's shared-memory block. A block that is gone (the host freed it, a stale descriptor) or a
    descriptor that is incomplete or inconsistent is `unreadable_image` with a message that says what the host must send.
    """
    from multiprocessing import shared_memory

    import numpy as np

    try:
        name = descriptor["shm"]["name"]
        dtype = np.dtype(descriptor["dtype"])
        if dtype.kind not in SHARED_MEMORY_DTYPE_KINDS:
            raise ValueError("dtype %s is not a number type" % dtype)
        shape = tuple(descriptor["shape"])
        shm = shared_memory.SharedMemory(name=name)
    except (KeyError, TypeError, ValueError, OSError) as error:
        logging.getLogger("labconstrictor.convert").error(
            "unusable shared-memory descriptor for %s", label, exc_info=True
        )
        raise ToolError("unreadable_image", _shared_memory_message(label, error)) from error
    try:
        view = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
        return view.copy()
    except (TypeError, ValueError) as error:  # shape/dtype larger than the block, or a negative dimension
        raise ToolError("unreadable_image", _shared_memory_message(label, error)) from error
    finally:
        shm.close()


def _shared_memory_message(label: str, error: Exception) -> str:
    """Why a shared-memory image cannot be read and what the host must do (keep the block until the task ends, send all fields)."""
    return (
        "the shared-memory image for '%s' is gone or malformed (%s: %s): the host must keep the block alive until the task "
        'ends and send {"appose_type": "ndarray", "shm": {"name": ...}, "shape": [...], "dtype": ...}'
        % (label, type(error).__name__, error)
    )


def build_results(schema: ToolSchema, returned: Any, job_dir: str | Path) -> list[Result]:
    """Turn the tool's return value into the list of typed results declared by the schema. Anything that is not what the
    declaration promised is `bad_return` with a message that names the output and what was expected, never a raw exception.
    """
    outputs = schema["outputs"]
    if len(outputs) == 1:
        values = [returned]
    elif returned is None:
        values = []
    elif isinstance(returned, (tuple, list)):
        values = list(returned)
    else:
        raise ToolError(
            "bad_return",
            "tool returned %s, declared %d outputs: return a tuple with one value per output"
            % (_describe_type(returned), len(outputs)),
        )
    if len(outputs) != len(values):
        raise ToolError("bad_return", "tool returned %d values, declared %d" % (len(values), len(outputs)))
    return [
        _write_one(out, value, Path(job_dir)) for out, value in zip(outputs, values)
    ]  # lengths checked just above (strict= needs 3.10)


def _bad_return(kind: str, name: str, expected: str, value: Any) -> ToolError:
    """The one wording of a wrong kind of returned value: which output, what it must be, what the tool returned."""
    return ToolError(
        "bad_return",
        "the %s output '%s' must be %s, got %s" % (kind, name, expected, _describe_type(value)),
    )


def _as_frame(kind: str, name: str, value: Any) -> Any:
    """A DataFrame, a dict of equal-length lists/arrays, or a list of dicts, as a DataFrame; anything else is `bad_return`.
    The shape is checked here, before pandas sees it: pandas' own errors differ between versions (AttributeError, TypeError,
    ValueError) and some mixed lists are accepted by one version and crash another."""
    import numpy as np
    import pandas as pd

    expected = "a DataFrame, a dict of lists or a list of dicts"
    if isinstance(value, pd.DataFrame):
        return value
    column_types = (list, tuple, np.ndarray, pd.Series)
    if isinstance(value, Mapping):
        columns = list(value.values())
        if not all(isinstance(c, column_types) and np.ndim(c) == 1 for c in columns):
            raise _bad_return(kind, name, expected + " (every column must be a 1-D list)", value)
        if len({len(c) for c in columns}) > 1:
            raise ToolError(
                "bad_return",
                "the %s output '%s' must be %s: the columns have different lengths" % (kind, name, expected),
            )
    elif isinstance(value, (list, tuple)):
        if not all(isinstance(row, Mapping) for row in value):
            raise _bad_return(kind, name, expected + " (every row must be a dict)", value)
    else:
        raise _bad_return(kind, name, expected, value)
    try:
        return pd.DataFrame(value)
    except (TypeError, ValueError, AttributeError) as error:  # whatever the pandas version objects to
        raise ToolError(
            "bad_return", "the %s output '%s' must be %s (%s)" % (kind, name, expected, error)
        ) from error


def _write_one(out: OutputSchema, value: Any, job_dir: Path) -> Result:
    kind, name = out["type"], out["name"]
    if kind in ("image", "labels"):
        import tifffile

        array = portable_dtype(_as_array(kind, name, value), name)
        path = job_dir / (name + ".tif")
        tifffile.imwrite(path, array)
        axes = out.get("axes") or DEFAULT_AXES.get(array.ndim, "")
        return {"type": kind, "name": name, "path": str(path), "axes": axes}
    if kind == "table":
        frame = _as_frame("table", name, value)
        path = job_dir / (name + ".csv")
        frame.to_csv(path, index=False)
        return {"type": "table", "name": name, "path": str(path)}
    if kind == "file":
        if not isinstance(value, (str, os.PathLike)):
            raise _bad_return("file", name, "a path (pathlib.Path or text)", value)
        return {"type": "file", "name": name, "path": str(value)}
    if kind == "values":
        if not isinstance(value, Mapping):
            raise _bad_return("values", name, "a dict of JSON-able values", value)
        return {"type": "values", "name": name, "values": {str(k): _plain(v) for k, v in value.items()}}
    if kind == "affine":
        return {"type": "affine", "name": name, "matrix_yx": _as_3x3(value, name), **out.get("display", {})}
    if kind == "message":
        if not isinstance(value, str):
            raise _bad_return("message", name, "text", value)
        text = value.strip()
        if not text:
            raise ToolError("bad_return", "the message output '%s' is empty" % name)
        return {"type": "message", "name": name, "text": text}
    if kind == "points":
        return _write_points(name, value, job_dir, out.get("display", {}))
    if kind == "shapes":
        return _write_shapes(name, value, job_dir, out.get("display", {}))
    raise ToolError("bad_return", "unsupported output type %r" % kind)


def _write_points(name: str, value: Any, job_dir: Path, display: dict[str, str]) -> Result:
    """Points as a CSV with the columns y and x (finite pixel coordinates) plus any properties."""
    import numpy as np
    import pandas as pd

    frame = _as_frame("points", name, value)
    missing = [c for c in ("y", "x") if c not in frame.columns]
    if missing:
        raise ToolError(
            "bad_return",
            "the points output '%s' needs the columns y and x (missing: %s)" % (name, ", ".join(missing)),
        )
    for column in ("y", "x"):
        numbers = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(numbers).all():
            raise ToolError(
                "bad_return",
                "the points output '%s' has a %s coordinate that is not a finite number" % (name, column),
            )
        frame[column] = numbers
    others = [c for c in frame.columns if c not in ("y", "x")]
    frame = frame[["y", "x"] + others]
    path = job_dir / (name + ".csv")
    frame.to_csv(path, index=False)
    return {
        "type": "points",
        "name": name,
        "path": str(path),
        "n": int(len(frame)),
        "columns": list(frame.columns),
        **display,
    }


def _ring(name: str, number: int, vertices: Any, ring_name: str = "polygon") -> list[list[float]]:
    """One ring of (y, x) vertices -> a closed GeoJSON ring of [x, y] (finite, at least 3 distinct vertices)."""
    import numpy as np

    try:
        array = np.asarray(vertices, dtype=float)
    except (TypeError, ValueError):
        raise ToolError(
            "bad_return",
            "the shapes output '%s': %s %d is not a list of (y, x) vertices" % (name, ring_name, number),
        ) from None
    if array.ndim != 2 or array.shape[1] != 2:
        raise ToolError(
            "bad_return",
            "the shapes output '%s': %s %d must be an array of (y, x) vertices, got shape %s"
            % (name, ring_name, number, array.shape),
        )
    if not np.isfinite(array).all():
        raise ToolError(
            "bad_return",
            "the shapes output '%s': %s %d has a vertex that is not a finite number"
            % (name, ring_name, number),
        )
    if len(array) > 1 and (array[0] == array[-1]).all():
        array = array[:-1]
    if len(np.unique(array, axis=0)) < 3:
        raise ToolError(
            "bad_return",
            "the shapes output '%s': %s %d has fewer than 3 distinct vertices" % (name, ring_name, number),
        )
    ring = [[float(x), float(y)] for y, x in array]
    return ring + [ring[0]]


def _check_geojson(name: str, collection: Any) -> None:
    """A GeoJSON FeatureCollection of Polygon / MultiPolygon features with finite coordinates; anything else is refused."""
    import math

    if (
        not isinstance(collection, dict)
        or collection.get("type") != "FeatureCollection"
        or not isinstance(collection.get("features"), list)
    ):
        raise ToolError(
            "bad_return",
            "the shapes output '%s': a GeoJSON dict must be a FeatureCollection with a list of features"
            % name,
        )

    def finite(node: Any) -> bool:
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            return math.isfinite(node)
        return isinstance(node, (list, tuple)) and all(finite(x) for x in node)

    for i, feature in enumerate(collection["features"]):
        geometry: Any = feature.get("geometry") if isinstance(feature, dict) else None
        kind = geometry.get("type") if isinstance(geometry, dict) else None
        if kind not in ("Polygon", "MultiPolygon"):
            raise ToolError(
                "bad_return",
                "the shapes output '%s': feature %d is a %s; only Polygon and MultiPolygon are supported"
                % (name, i, kind or "geometry-less feature"),
            )
        if not finite(geometry.get("coordinates")):
            raise ToolError(
                "bad_return",
                "the shapes output '%s': feature %d has a coordinate that is not a finite number" % (name, i),
            )


def _write_shapes(name: str, value: Any, job_dir: Path, display: dict[str, str]) -> Result:
    """Outlines as a GeoJSON FeatureCollection ([x, y], pixel centres at integers). Accepts a FeatureCollection, or a list of
    polygons: each an array of (y, x) vertices, or a dict with `polygon` (that array) and properties."""
    import json

    if isinstance(value, dict):
        _check_geojson(name, value)
        collection = value
    else:
        try:
            items = list(value)
        except TypeError:
            raise ToolError(
                "bad_return", "the shapes output '%s' must be a GeoJSON dict or a list of polygons" % name
            ) from None
        features = []
        for i, item in enumerate(items):
            properties = {}
            if isinstance(item, dict):
                properties = {str(k): _plain(v) for k, v in item.items() if k != "polygon"}
                item = item.get("polygon")
                if item is None:
                    raise ToolError(
                        "bad_return",
                        "the shapes output '%s': polygon %d is a dict without the key 'polygon'" % (name, i),
                    )
            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {"type": "Polygon", "coordinates": [_ring(name, i, item)]},
                }
            )
        collection = {"type": "FeatureCollection", "features": features}
    path = job_dir / (name + ".geojson")
    path.write_text(json.dumps(collection, allow_nan=False), encoding="utf-8")
    return {"type": "shapes", "name": name, "path": str(path), "n": len(collection["features"]), **display}


def _plain(value: Any) -> Any:
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


def _as_array(kind: str, name: str, value: Any) -> Any:
    """The tool's image/labels result as an ndarray; text, nothing, an object or a ragged list is `bad_return`."""
    import numpy as np

    if isinstance(value, (str, bytes, dict)) or value is None:
        raise _bad_return(kind, name, "an array of numbers", value)
    try:
        return np.asarray(value)
    except (TypeError, ValueError) as error:  # ragged nested lists
        raise ToolError(
            "bad_return", "the %s output '%s' must be an array of numbers (%s)" % (kind, name, error)
        ) from error


def _as_3x3(matrix: Any, name: str = "affine") -> list[list[float]]:
    """A 2x3 or 3x3 matrix of finite numbers as a 3x3 list; anything else is `bad_return` naming the output."""
    import numpy as np

    try:
        m = np.asarray(matrix, float)
    except (TypeError, ValueError) as error:
        raise ToolError(
            "bad_return", "the affine output '%s' must be a 3x3 matrix of numbers (%s)" % (name, error)
        ) from error
    if m.shape == (2, AFFINE_SIZE):
        m = np.vstack([m, [0, 0, 1]])
    if m.shape != (AFFINE_SIZE, AFFINE_SIZE):
        raise ToolError("bad_return", "affine must be 3x3 (got %s)" % (m.shape,))
    if not np.isfinite(m).all():
        raise ToolError(
            "bad_return",
            "the affine output '%s' has a value that is not a finite number (NaN or infinity): a host cannot apply it"
            % name,
        )
    return m.tolist()


_DTYPE_KIND_NAMES = {"c": "complex numbers", "O": "Python objects", "U": "text", "S": "bytes", "V": "records"}


def _float32_holds_exactly(widened: Any, original: Any) -> bool:
    """True when every integer of `original` equals its float32 `widened`. The back-conversion is only done for values inside
    the integer type's range: casting a float outside it is undefined (x86 gives 0, ARM saturates), which once let a uint64
    2**64-1 pass as float32 2**64."""
    import numpy as np

    info = np.iinfo(original.dtype)
    values = widened.astype(np.float64)  # exact: every float32 is a float64
    upper_exclusive = 2.0 ** (info.bits - (1 if info.min < 0 else 0))
    if not ((values >= float(info.min)) & (values < upper_exclusive)).all():
        return False
    return bool(np.array_equal(widened.astype(original.dtype), original))


def portable_dtype(array: Any, what: str = "image") -> Any:
    """Cast to a dtype every host can open (ImageJ's TIFF reader has no float64, int64, uint32/64, bool or int8).
    Integers are never changed in value: wide integers that fit 16 bits are narrowed, anything else must be exactly
    representable as float32 or the call fails. Floating point values lose precision (float64 -> float32, ~7 digits).
    """
    import numpy as np

    kind, size = array.dtype.kind, array.dtype.itemsize
    if array.size == 0:
        raise ToolError(
            "bad_return",
            "%s is empty (shape %s): an image needs at least one pixel in every dimension"
            % (what, tuple(array.shape)),
        )
    if kind not in IMAGE_DTYPE_KINDS:
        raise ToolError(
            "unsupported_dtype",
            "%s holds %s values (%s): hosts can only open numbers; return a numeric array (integers or floats)"
            % (what, array.dtype, _DTYPE_KIND_NAMES.get(kind, "not numbers")),
        )
    if kind == "b":
        return array.astype(np.uint8)
    if kind == "f":
        if array.dtype == np.float32:
            return array
        with np.errstate(over="ignore"):
            narrowed = array.astype(np.float32)
        if np.any(np.isinf(narrowed) & np.isfinite(array)):
            raise ToolError(
                "unsupported_dtype", "%s has values outside the float32 range that hosts can open" % what
            )
        return narrowed
    if kind in "ui":
        if (kind == "u" and size <= 2) or (kind == "i" and size == 2):
            return array
        if kind == "i" and size == 1:
            return array.astype(np.int16)
        low, high = int(array.min()), int(array.max())
        if low >= 0 and high <= UINT16_MAX:
            return array.astype(np.uint16)
        if low >= INT16_MIN and high <= INT16_MAX:
            return array.astype(np.int16)
        widened = array.astype(np.float32)
        if _float32_holds_exactly(widened, array):
            return widened
        raise ToolError(
            "unsupported_dtype",
            "%s has %s values from %d to %d that cannot be stored exactly in a TIFF that ImageJ, Napari and Fiji can open "
            "(16-bit integers or 32-bit floats); relabel or rescale them inside the tool"
            % (what, array.dtype, low, high),
        )
    return array
