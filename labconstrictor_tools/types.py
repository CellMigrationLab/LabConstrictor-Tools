"""Semantic types + metadata markers for tool declarations. Pure stdlib; no scientific imports."""

from collections.abc import Sequence
from typing import Any


# ---- semantic input types (what the tool function RECEIVES: Image->ndarray, Table->DataFrame, File->Path)
class Image:
    "image input (TIFF on the wire)"


class Labels:
    "label-image input"


class Table:
    "tabular input (CSV on the wire)"


class File:
    "arbitrary file input (path)"


class Folder:
    "folder input (a directory path; hosts show a folder chooser)"


# ---- semantic output types (what the tool function RETURNS)
class ImageOut:
    "ndarray -> image"


class LabelsOut:
    "ndarray -> label image"


class TableOut:
    "DataFrame / dict-of-lists / list-of-dicts -> table"


class FileOut:
    "pathlib.Path -> file"


class Scalars:
    "dict of JSON-able values"


class MessageOut:
    "str -> a message for the user (plain text; **bold** and lists are fine): instructions, a readout, a warning. Not a log: keep it short"


class PointsOut:
    """DataFrame / dict-of-lists / list-of-dicts with columns `y` and `x` (pixel coordinates, in the frame of the image named by
    ApplyTo, or of the first image input) -> points: a Napari points layer, Fiji point ROIs, QuPath point annotations. Any other
    column is kept as a property of each point (for example `label` or `score`)."""


class ShapesOut:
    """Outlines of objects (polygons, with holes allowed) in the pixel frame of the image named by ApplyTo, or of the first image
    input -> a Napari shapes layer, Fiji polygon ROIs, QuPath annotations. Return a GeoJSON FeatureCollection (dict), or a list of
    polygons: each an array of (y, x) vertices, or a dict with `polygon` (that array) plus properties. `labconstrictor_tools.shapes
    .labels_to_shapes(labels)` makes outlines from a label image. Coordinates are written as GeoJSON [x, y] with pixel centres at
    integers, like PointsOut."""


class Affine:
    "3x3 homogeneous matrix in (y,x) pixel coordinates mapping SOURCE pixels -> TARGET pixels"


INPUT_TYPES = {Image: "image", Labels: "labels", Table: "table", File: "file", Folder: "folder"}
OUTPUT_TYPES = {
    ImageOut: "image",
    LabelsOut: "labels",
    TableOut: "table",
    FileOut: "file",
    Scalars: "values",
    Affine: "affine",
    MessageOut: "message",
    PointsOut: "points",
    ShapesOut: "shapes",
}


# ---- metadata markers (use inside typing.Annotated[...])
class _Marker:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self.value)


class Min(_Marker):
    "inclusive minimum"


class Max(_Marker):
    "inclusive maximum"


class Unit(_Marker):
    "physical unit, e.g. 'um/px'"


class Description(_Marker):
    "one-line help text"


class Label(_Marker):
    "human-readable label"


class Group(_Marker):
    "heading the parameter is listed under in the form (parameters keep their order; a group is shown where it first appears)"


WIDGETS = ("slider", "radio")


class Widget(_Marker):
    "how a parameter is shown: Widget('slider') for a bounded number (needs Min and Max), Widget('radio') for 2 to 5 choices; hosts that do not know it show the plain field"

    def __init__(self, value: str) -> None:
        if value not in WIDGETS:
            raise ValueError("Widget(%r): use one of %s" % (value, ", ".join(repr(w) for w in WIDGETS)))
        super().__init__(value)


class RegionOf(_Marker):
    """On an optional Labels input: the host fills it from the current selection (Napari the selected Shapes layer, Fiji the ROI,
    QuPath the selected annotations) as a label image the size of the image named here (0 outside, 1..N for the selected objects),
    behind a "use the selection" box that is off by default. A tool must treat None as "the whole image"; see
    `labconstrictor_tools.region.bbox`. Without host support it is the plain optional Labels chooser."""

    def __init__(self, value: str) -> None:
        super().__init__(str(value))


class Advanced(_Marker):
    "listed under 'Advanced settings' (collapsed by default in hosts that can); use Advanced() without an argument"

    def __init__(self, value: bool = True) -> None:
        super().__init__(bool(value))


class EnabledWhen:
    """Only meaningful when another parameter has a value: EnabledWhen("fixed_seed") = that parameter is set / true;
    EnabledWhen("segmentation", "cellpose", "instanseg") = it equals one of these. Hosts grey the parameter out otherwise
    (Fiji cannot do that dynamically and shows it always); the tool must therefore still accept the parameter when it is not enabled.
    """

    def __init__(self, param: str, *equals: Any) -> None:
        self.param, self.equals = param, list(equals)

    def __repr__(self) -> str:
        return "EnabledWhen(%r%s)" % (self.param, "".join(", %r" % (e,) for e in self.equals))


class ChoicesFrom:
    """A string parameter whose options are only known at run time (for instance the conditions of a game that was just
    prepared). `tool` is another tool of the same app that returns Scalars with a list under `field`; `depends` names the
    parameters of THIS tool whose current values are passed to it (they must exist in the source tool too; every other
    parameter of the source tool must be optional). Hosts show a dropdown filled from that tool and fall back to a plain
    text field when it cannot be answered (not prepared yet, an error, an old host), so the tool must accept any string.
    """

    def __init__(self, tool: str, depends: Sequence[str] = (), field: str = "choices") -> None:
        self.tool, self.depends, self.field = tool, list(depends), field

    def __repr__(self) -> str:
        return "ChoicesFrom(%r, %r, %r)" % (self.tool, self.depends, self.field)


class ClearAfterRun(_Marker):
    "after a successful run, hosts that keep form values between runs (Napari) put this parameter back to its default (or unset)"

    def __init__(self, value: bool = True) -> None:
        super().__init__(bool(value))


class Collapsed(_Marker):
    "with Group: the group of this parameter starts folded (an accordion section); hosts that cannot fold show it open"

    def __init__(self, value: bool = True) -> None:
        super().__init__(bool(value))


class Replace(_Marker):
    "output hint (image, labels, table or affine): a new run replaces the result of the previous run of this output (same layer / window) instead of adding one"

    def __init__(self, value: bool = True) -> None:
        super().__init__(bool(value))


class PickChannel(_Marker):
    """On an Image input of a 2D tool: the person chooses the channel of a multi-channel image, and the host hands the tool only
    that channel (a 2D array). Without it a host passes the image as it is, and a 2D tool refuses a multi-channel one.
    Hosts that cannot list channels (Napari layers are usually one channel each) show a plain image chooser; the command line and
    notebooks pass the file as it is."""

    def __init__(self, value: bool = True) -> None:
        super().__init__(bool(value))


class Axes(_Marker):
    "axes string, e.g. 'YX'"


class Name(_Marker):
    "name of an output"


class PixelSizeOf(_Marker):
    "this float is the calibration (um/px) of the named image parameter; hosts prefill it"


class ApplyTo:
    """Output hint for Affine: apply this transform to image parameter `source` (optionally shown on top of `target`)."""

    def __init__(self, source: str, target: str | None = None) -> None:
        self.source, self.target = source, target

    def __repr__(self) -> str:
        return "ApplyTo(%r,%r)" % (self.source, self.target)


class ToolError(Exception):
    """Raise from a tool to return a structured, user-readable error: ToolError('no_match', 'message')."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code, self.message = code, message


class Cancelled(Exception):
    "raised by check_cancel() when the host cancelled the task"
