"""Semantic types + metadata markers for tool declarations. Pure stdlib; no scientific imports."""

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
