"""Typed shapes of the JSON documents that cross process boundaries: the schema hosts read, the registry entry hosts trust,
and what a worker sends back. They are plain dicts at run time (they come from JSON); the types document the contract
(docs/PROTOCOL.md) and let a type checker catch a misspelled key."""

from typing import Any, TypedDict


class RegistryEntry(TypedDict):
    """`<registry>/<name>.json`, written by `register`."""

    schema: int
    name: str
    display_name: str
    version: str
    prefix: str
    python: str
    module: str
    pythonpath: list[str]
    runtime_path: str
    schema_path: str


class _ParamRequired(TypedDict):
    name: str
    label: str
    type: str
    required: bool


class ParamSchema(_ParamRequired, total=False):
    """One input of a tool. `type` is one of: string integer float boolean choice image labels table file folder."""

    default: Any
    description: str
    choices: list[Any]
    minimum: float
    maximum: float
    unit: str
    axes: str
    pixel_size_of: str
    nullable: bool
    group: str
    advanced: bool
    enabled_when: dict[str, Any]
    group_collapsed: bool
    clear_after_run: bool
    choices_from: dict[str, Any]


class _OutputRequired(TypedDict):
    name: str
    type: str


class OutputSchema(_OutputRequired, total=False):
    """One output of a tool. `type` is one of: image labels table values affine file message points."""

    axes: str
    display: dict[str, str]
    replace: bool


class _ToolRequired(TypedDict):
    id: str
    label: str
    inputs: list[ParamSchema]
    outputs: list[OutputSchema]


class ToolSchema(_ToolRequired, total=False):
    description: str


class _AppRequired(TypedDict):
    protocol: int
    tools: list[ToolSchema]


class AppSchema(_AppRequired, total=False):
    """`<registry>/<name>.schema.json`: everything a host needs to build forms without starting Python."""

    application: str
    version: str


# a result as the worker reports it: {"type": ..., "name": ..., plus "path" / "values" / "matrix_yx" ...}
Result = dict[str, Any]


class _CaseRequired(TypedDict):
    tool: str


class CaseSpec(_CaseRequired, total=False):
    """One entry of a cases file (see testing.validate_case for the allowed keys)."""

    inputs: dict[str, Any]
    expect: dict[str, Any]
    skip: str | None
    cancel_after_s: float
    comment: str
    _dir: str


class _ReportRequired(TypedDict):
    tool: str
    problems: list[str]
    warnings: list[str]
    skipped: str | None
    seconds: float


class CaseReport(_ReportRequired, total=False):

    status: str
    traceback: str
    stderr_tail: list[str]
