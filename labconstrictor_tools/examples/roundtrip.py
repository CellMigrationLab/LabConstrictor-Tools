"""Round-trip app: one tool per declared type that sends back what it received, plus transforms with known results.

    labconstrictor-tools check --module labconstrictor_tools.examples.roundtrip

It exists so that a host (or the test matrix in tests/) can prove that every type and value crosses the bridge unchanged:
each `echo_*` tool returns its input as the matching output AND reports what it received (type, exact bits, digest) in a
`received` Scalars result, so both directions can be compared with a value computed independently by the caller.
The `transform` tools (image + 1, a column sum, a label count, a region box, outlines of labels) have results that a caller
can work out with plain numpy. numpy, pandas and tifffile are only imported inside the functions.
"""

import enum
import hashlib
import json
from typing import Annotated, Literal

from labconstrictor_tools import (
    Affine,
    ApplyTo,
    Description,
    File,
    FileOut,
    Folder,
    Image,
    ImageOut,
    Labels,
    LabelsOut,
    Max,
    MessageOut,
    Min,
    Name,
    PointsOut,
    RegionOf,
    Scalars,
    ShapesOut,
    Table,
    TableOut,
    ToolError,
    Widget,
    tool,
)


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


# ---------------------------------------------------------------- what a tool reports about what it received
def _scalar_report(value: object) -> dict[str, object]:
    """Type and exact content of a received scalar (`hex` keeps the sign of -0.0 and every bit of a float)."""
    report: dict[str, object] = {"value": value, "type": type(value).__name__, "repr": repr(value)}
    if isinstance(value, float):
        report["hex"] = value.hex()
    if isinstance(value, str):
        report["codepoints"] = [ord(c) for c in value]
    return report


def _array_report(array: "object") -> dict[str, object]:
    import numpy as np

    a = np.asarray(array)
    report: dict[str, object] = {
        "dtype": str(a.dtype),
        "shape": list(a.shape),
        "digest": hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest(),
    }
    if a.dtype.kind == "f":
        report["n_nan"] = int(np.isnan(a).sum())
        report["n_inf"] = int(np.isinf(a).sum())
    if a.size <= 64 and a.dtype.kind in "biu":
        report["flat"] = a.ravel().tolist()
    return report


# ---------------------------------------------------------------- echo: files and arrays
@tool("Echo image")
def echo_image(
    image: Image,
) -> tuple[Annotated[ImageOut, Name("image")], Annotated[Scalars, Name("received")]]:
    """Returns the image it received and a report of it."""
    return image, _array_report(image)


@tool("Echo labels")
def echo_labels(
    labels: Labels,
) -> tuple[Annotated[LabelsOut, Name("labels")], Annotated[Scalars, Name("received")]]:
    """Returns the label image it received and a report of it."""
    return labels, _array_report(labels)


@tool("Echo table")
def echo_table(
    table: Table,
) -> tuple[Annotated[TableOut, Name("table")], Annotated[Scalars, Name("received")]]:
    """Returns the table it received and its column names, row count and the kind of each column."""
    report = {
        "columns": [str(c) for c in table.columns],
        "n_rows": int(len(table)),
        "kinds": [t.kind for t in table.dtypes],  # b, i, u, f or O (text): stable across pandas versions
    }
    return table, report


@tool("Echo file")
def echo_file(
    file: File,
) -> tuple[Annotated[FileOut, Name("file")], Annotated[Scalars, Name("received")]]:
    """Returns the path it received and what the worker sees at that path."""
    exists = file.is_file()
    report = {
        "name": file.name,
        "str": str(file),
        "exists": exists,
        "size": file.stat().st_size if exists else None,
        "digest": hashlib.sha256(file.read_bytes()).hexdigest() if exists else None,
        "type": type(file).__name__,
    }
    return file, report


@tool("Echo folder")
def echo_folder(
    folder: Folder,
) -> tuple[Annotated[FileOut, Name("folder")], Annotated[Scalars, Name("received")]]:
    """Returns the folder path it received and the sorted names inside it."""
    report = {"name": folder.name, "str": str(folder), "entries": sorted(p.name for p in folder.iterdir())}
    return folder, report


# ---------------------------------------------------------------- echo: scalars
@tool("Echo int")
def echo_int(value: int) -> Scalars:
    return _scalar_report(value)


@tool("Echo float")
def echo_float(value: float) -> Scalars:
    return _scalar_report(value)


@tool("Echo string")
def echo_string(value: str) -> Scalars:
    return _scalar_report(value)


@tool("Echo bool")
def echo_bool(value: bool) -> Scalars:
    return _scalar_report(value)


@tool("Echo choice (text)")
def echo_choice(value: Literal["alpha", "beta", "gamma", "with space", "ünï", ""]) -> Scalars:
    return _scalar_report(value)


@tool("Echo choice (numbers)")
def echo_number_choice(value: Literal[1, 2, 3]) -> Scalars:
    return _scalar_report(value)


@tool("Echo enum")
def echo_enum(value: Color = Color.GREEN) -> Scalars:
    return {**_scalar_report(value.value), "is_member": isinstance(value, Color), "member": value.name}


@tool("Echo with defaults")
def echo_defaults(
    number: int = 7, ratio: float = 0.25, text: str = "dflt", flag: bool = True, mode: Literal["a", "b"] = "b"
) -> Scalars:
    """Every parameter has a default: an empty request must give exactly these values."""
    return {
        "number": _scalar_report(number),
        "ratio": _scalar_report(ratio),
        "text": _scalar_report(text),
        "flag": _scalar_report(flag),
        "mode": _scalar_report(mode),
    }


@tool("Echo optional int")
def echo_optional_int(value: int | None = None) -> Scalars:
    return {**_scalar_report(value), "is_none": value is None}


@tool("Echo optional float")
def echo_optional_float(value: float | None = None) -> Scalars:
    return {**_scalar_report(value), "is_none": value is None}


@tool("Echo optional string")
def echo_optional_string(value: str | None = None) -> Scalars:
    return {**_scalar_report(value), "is_none": value is None}


@tool("Echo optional bool")
def echo_optional_bool(value: bool | None = None) -> Scalars:
    return {**_scalar_report(value), "is_none": value is None}


@tool("Echo optional choice")
def echo_optional_choice(value: Literal["x", "y"] | None = None) -> Scalars:
    return {**_scalar_report(value), "is_none": value is None}


@tool("Echo optional image")
def echo_optional_image(image: Image | None = None) -> Scalars:
    return {"is_none": image is None, **({} if image is None else _array_report(image))}


@tool("Echo bounded int")
def echo_bounded_int(value: Annotated[int, Min(-5), Max(10)]) -> Scalars:
    return _scalar_report(value)


@tool("Echo bounded float")
def echo_bounded_float(value: Annotated[float, Min(-0.5), Max(1.5)]) -> Scalars:
    return _scalar_report(value)


@tool("Echo min only")
def echo_min_only(value: Annotated[float, Min(0)]) -> Scalars:
    return _scalar_report(value)


@tool("Echo max only")
def echo_max_only(value: Annotated[int, Max(100)]) -> Scalars:
    return _scalar_report(value)


@tool("Echo slider int")
def echo_slider_int(value: Annotated[int, Min(0), Max(255), Widget("slider")] = 128) -> Scalars:
    return _scalar_report(value)


@tool("Echo slider float")
def echo_slider_float(value: Annotated[float, Min(0), Max(1), Widget("slider")] = 0.5) -> Scalars:
    return _scalar_report(value)


@tool("Echo radio")
def echo_radio(value: Annotated[Literal["one", "two", "three"], Widget("radio")] = "two") -> Scalars:
    return _scalar_report(value)


@tool("Echo radio (enum)")
def echo_radio_enum(value: Annotated[Color, Widget("radio")] = Color.RED) -> Scalars:
    return {**_scalar_report(value.value), "is_member": isinstance(value, Color)}


# ---------------------------------------------------------------- echo: other outputs
@tool("Echo message")
def echo_message(text: str) -> MessageOut:
    """The message output (plain text; the host shows it stripped of surrounding whitespace)."""
    return text


@tool("Echo points")
def echo_points(points: Table) -> PointsOut:
    """Returns a table with the columns y and x (any other column becomes a property of each point)."""
    return points


@tool("Grid of points")
def grid_points(
    rows: Annotated[int, Min(0), Max(1000)] = 2,
    columns: Annotated[int, Min(0), Max(1000)] = 3,
    spacing: Annotated[float, Min(0)] = 1.5,
) -> PointsOut:
    """A rows x columns grid of points at y = row * spacing, x = column * spacing, labelled 1..N row by row."""
    ys, xs = [], []
    for r in range(rows):
        for c in range(columns):
            ys.append(r * spacing)
            xs.append(c * spacing)
    return {"y": ys, "x": xs, "label": list(range(1, len(ys) + 1))}


@tool("Echo shapes (GeoJSON)")
def echo_geojson(geojson: File) -> ShapesOut:
    """Returns the FeatureCollection stored in a JSON file."""
    return json.loads(geojson.read_text(encoding="utf-8"))


@tool("Echo shapes (polygons)")
def echo_polygons(polygons: File) -> ShapesOut:
    """Returns the list of polygons stored in a JSON file: each [[y, x], ...] or {"polygon": [[y, x], ...], ...properties}."""
    return json.loads(polygons.read_text(encoding="utf-8"))


@tool("Echo affine")
def echo_affine(matrix_json: str) -> Affine:
    """Returns the matrix given as JSON text (3x3, or 2x3 which is completed)."""
    return json.loads(matrix_json)


@tool("Echo affine (applied)")
def echo_affine_applied(
    matrix_json: str, source: Image | None = None, reference: Image | None = None
) -> Annotated[Affine, ApplyTo("source", "reference")]:
    """The same, with the images it belongs to named in the result."""
    return json.loads(matrix_json)


@tool("Typed scalars")
def typed_scalars(kind: Literal["numpy", "nan", "nested"] = "numpy") -> Scalars:
    """Values a tool may put in Scalars: numpy scalars, NaN/infinity (sent as null), nested lists and dicts."""
    import numpy as np

    if kind == "numpy":
        return {
            "i64": np.int64(2**40),
            "u8": np.uint8(200),
            "f32": np.float32(0.1),
            "f64": np.float64(0.1),
            "bool": np.bool_(True),
            "zero_d": np.array(3),
        }
    if kind == "nan":
        return {
            "nan": float("nan"),
            "inf": float("inf"),
            "ninf": float("-inf"),
            "ok": 1.5,
            "np_nan": np.float32("nan"),
        }
    return {"list": [1, float("nan"), [2, float("inf")]], "dict": {"a": float("-inf"), "b": (1, 2)}}


# ---------------------------------------------------------------- transforms with results that plain numpy can predict
@tool("Image plus one")
def image_plus_one(image: Image) -> ImageOut:
    """image + 1, computed in float32 (so uint8 255 becomes 256.0, not 0)."""
    import numpy as np

    return image.astype(np.float32) + np.float32(1)


@tool("Column sum")
def table_column_sum(table: Table, column: str) -> Scalars:
    """The sum of one column and the number of rows."""
    if column not in table.columns:
        raise ToolError(
            "no_column", "the table has no column %r (columns: %s)" % (column, list(table.columns))
        )
    return {"sum": float(table[column].sum()), "n_rows": int(len(table))}


@tool("Count labels")
def count_labels(labels: Labels) -> Scalars:
    """How many distinct non-zero labels there are, and the pixel count of each."""
    import numpy as np

    values, counts = np.unique(labels[labels != 0], return_counts=True)
    return {"count": int(len(values)), "areas": {str(int(v)): int(c) for v, c in zip(values, counts)}}


@tool("Region box")
def region_box(
    image: Image,
    region: Annotated[
        Labels | None, RegionOf("image"), Description("rows and columns that enclose the region")
    ] = None,
) -> Scalars:
    """Rows and columns that enclose the region (the whole image when there is none), through region.bbox."""
    from labconstrictor_tools.region import bbox

    box = (
        bbox(region, image) if region is not None else (slice(0, image.shape[-2]), slice(0, image.shape[-1]))
    )
    return {"rows": [box[0].start, box[0].stop], "columns": [box[1].start, box[1].stop]}


@tool("Outline labels")
def outline_labels(
    labels: Labels, simplify: Annotated[float, Min(0)] = 0.0, min_area: Annotated[int, Min(1)] = 1
) -> Annotated[ShapesOut, ApplyTo("labels")]:
    """Outlines of the labels (labels_to_shapes); simplify 0 keeps every pixel corner."""
    from labconstrictor_tools.shapes import labels_to_shapes

    return labels_to_shapes(labels, simplify=simplify, min_area=min_area)
