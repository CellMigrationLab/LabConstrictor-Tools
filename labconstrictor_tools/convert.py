"""Wire values <-> Python objects, driven by the generated schema.

Inputs : image/labels -> ndarray (TIFF path or shared-memory ndarray), table -> DataFrame (CSV path),
         file -> Path, scalars coerced and range-checked.
Outputs: ndarray -> TIFF, DataFrame/dict/list -> CSV, matrices -> JSON, dict -> JSON.
numpy/pandas/tifffile are imported lazily, only when a tool actually uses those types.
"""

import logging
import math
import os
import sys
from pathlib import Path
from typing import Any

from .structures import OutputSchema, ParamSchema, Result, ToolSchema
from .types import ToolError

UINT16_MAX = (
    65535  # integer images within the 16-bit ranges are narrowed to uint16 / int16, which every host opens
)
INT16_MIN, INT16_MAX = -32768, 32767
SHARED_MEMORY_TRACK_PARAMETER_FROM = (3, 13)  # SharedMemory(track=False) exists from this Python version on
DEFAULT_AXES = {2: "YX", 3: "ZYX", 4: "CZYX"}


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
        array = _read_image(value)
        if array.size == 0:  # a file is checked while reading; shared memory is checked here
            raise ToolError(
                "empty_image", "'%s' contains no image data (shape %s)" % (param["label"], tuple(array.shape))
            )
        return _check_dimensions(param, array)
    if kind == "table":
        return _read_table(param, value)
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
        if isinstance(value, bool):
            raise ToolError("invalid_parameter", "'%s' must be a number, not true/false" % param["label"])
        number = float(value)
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


# Texts pandas reads as "missing" by default. In a table input they stay text, except in a column whose other cells are numbers
# (there they are missing numbers); an empty cell is always missing. Documented in docs/PROTOCOL.md ("Table inputs").
PANDAS_NA_WORDS = [
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "N/A",
    "NA",
    "NULL",
    "NaN",
    "None",
    "n/a",
    "nan",
    "null",
]
EMPTY_CELL = ""


def _read_table(param: ParamSchema, value: Any) -> Any:
    """Read a CSV file into a DataFrame exactly as the host wrote it: floats with all their digits (`round_trip`), column names
    as written (duplicates and empty names included: columns are read by position and named afterwards), empty cells missing,
    texts like "NA" kept as text unless the column is numeric. A missing or unreadable file is a ToolError, not a pandas error.
    """
    import pandas as pd

    path = Path(value)
    label = param["label"]
    if not path.is_file():
        raise ToolError("file_not_found", "'%s': table file not found: %s" % (label, path))
    try:
        header = pd.read_csv(path, header=None, nrows=1, dtype=str, keep_default_na=False)
        names = [str(name) for name in header.iloc[0]]
        columns = list(range(len(names)))
        options: dict[str, Any] = {"header": 0, "names": columns, "float_precision": "round_trip"}
        frame = pd.read_csv(path, keep_default_na=False, na_values=[EMPTY_CELL], **options)
        words = [
            column
            for column in columns
            if pd.api.types.is_string_dtype(frame[column]) and frame[column].isin(PANDAS_NA_WORDS).any()
        ]
        if words:  # a column of numbers with some "NA" cells is numeric, with those cells missing
            numeric = pd.read_csv(
                path,
                usecols=words,
                keep_default_na=False,
                na_values=PANDAS_NA_WORDS + [EMPTY_CELL],
                **options,
            )
            for column in words:
                if (
                    pd.api.types.is_numeric_dtype(numeric[column]) and numeric[column].notna().any()
                ):  # all words: text
                    frame[column] = numeric[column]
        frame.columns = names
        return frame
    except (
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeDecodeError,
        ValueError,
        OSError,
    ) as error:
        logging.getLogger("labconstrictor.convert").error("cannot read table %s", path, exc_info=True)
        raise ToolError(
            "unreadable_table",
            "cannot read %s as a CSV table: %s; save the table as a UTF-8 CSV file with a header row"
            % (path.name, error),
        ) from error


def _read_image(value: Any) -> Any:
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


def _attach_shared_memory(name: str) -> Any:
    """Map a block the HOST created, without taking over its life: the worker only reads it, the host unlinks it.

    Python's resource tracker unlinks every block a process registered when that process exits. Attaching registers the block
    before Python 3.13 (3.13 has `track=False`), so a worker leaving would destroy a block the host still owns (and print a
    "leaked shared_memory" warning into crash messages). Tracking is a POSIX mechanism: Windows has none to avoid.
    """
    from multiprocessing import resource_tracker, shared_memory

    if sys.version_info >= SHARED_MEMORY_TRACK_PARAMETER_FROM:
        return shared_memory.SharedMemory(name=name, track=False)  # type: ignore[call-arg,unused-ignore]  # older stubs lack `track`
    if os.name != "posix":
        return shared_memory.SharedMemory(name=name)
    # Before 3.13 the constructor registers every attach: skip that one call (unregistering afterwards would also cancel the
    # registration of a creator living in THIS process, e.g. a test or a notebook that calls the converter directly)
    register = resource_tracker.register
    resource_tracker.register = lambda *_args, **_kwargs: None
    try:
        return shared_memory.SharedMemory(name=name)
    finally:
        resource_tracker.register = register


def _ndarray_from_shared_memory(descriptor: dict[str, Any]) -> Any:
    import numpy as np

    shm = _attach_shared_memory(descriptor["shm"]["name"])
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


def _write_one(out: OutputSchema, value: Any, job_dir: Path) -> Result:
    kind, name = out["type"], out["name"]
    if kind in ("image", "labels"):
        import numpy as np
        import tifffile

        array = portable_dtype(np.asarray(value), name)
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
    if kind == "message":
        text = str(value).strip()
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

    frame = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
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


def _as_3x3(matrix: Any) -> list[list[float]]:
    import numpy as np

    m = np.asarray(matrix, float)
    if m.shape == (2, 3):
        m = np.vstack([m, [0, 0, 1]])
    if m.shape != (3, 3):
        raise ToolError("bad_return", "affine must be 3x3 (got %s)" % (m.shape,))
    return m.tolist()


def portable_dtype(array: Any, what: str = "image") -> Any:
    """Cast to a dtype every host can open (ImageJ's TIFF reader has no float64, int64, uint32/64, bool or int8).
    Integers are never changed in value: wide integers that fit 16 bits are narrowed, anything else must be exactly
    representable as float32 or the call fails. Floating point values lose precision (float64 -> float32, ~7 digits).
    """
    import numpy as np

    kind, size = array.dtype.kind, array.dtype.itemsize
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
        if array.size == 0:
            return array.astype(np.uint16)
        low, high = int(array.min()), int(array.max())
        if low >= 0 and high <= UINT16_MAX:
            return array.astype(np.uint16)
        if low >= INT16_MIN and high <= INT16_MAX:
            return array.astype(np.int16)
        widened = array.astype(np.float32)
        if np.array_equal(widened.astype(array.dtype), array):
            return widened
        raise ToolError(
            "unsupported_dtype",
            "%s has %s values from %d to %d that cannot be stored exactly in a TIFF that ImageJ, Napari and Fiji can open "
            "(16-bit integers or 32-bit floats); relabel or rescale them inside the tool"
            % (what, array.dtype, low, high),
        )
    return array
