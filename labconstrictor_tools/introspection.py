"""Python signature -> portable JSON schema (protocol 1). Never calls the tool."""

import enum
import inspect
import re
from typing import Annotated, Literal, Union, get_args, get_origin, get_type_hints

from . import types as T
from .decorators import tools_in

PROTOCOL = 1
SCALARS = {str: "string", int: "integer", float: "float", bool: "boolean"}


class DeclarationError(Exception):
    pass


def _docstring_args(doc):
    """Google-style 'Args:' section -> {name: text}."""
    out, sec, cur, base = {}, False, None, None
    for line in inspect.cleandoc(doc or "").splitlines():
        s = line.strip()
        ind = len(line) - len(line.lstrip())
        if s.lower() in ("args:", "arguments:", "parameters:"):
            sec, base = True, None
            continue
        if not sec or not s:
            continue
        if ind == 0:
            sec = False
            continue
        if base is None:
            base = ind
        m = re.match(r"^(\w+)\s*(\([^)]*\))?\s*:\s*(.*)$", s)
        if ind <= base and m:
            cur = m.group(1)
            out[cur] = m.group(3)
        elif cur:
            out[cur] += " " + s
    return out


def _unwrap(ann):
    """-> (base type, [metadata], optional?)"""
    meta, optional = [], False
    while True:
        o = get_origin(ann)
        if o is Annotated:
            args = get_args(ann)
            ann, meta = args[0], meta + list(args[1:])
            continue
        if o in (Union, getattr(__import__("types"), "UnionType", Union)):
            a = [x for x in get_args(ann) if x is not type(None)]
            if len(a) != len(get_args(ann)) and len(a) == 1:
                ann, optional = a[0], True
                continue
        return ann, meta, optional


def _m(meta, cls):
    for x in meta:
        if isinstance(x, cls):
            return x
    return None


def _param(name, p, hint, argdoc):
    base, meta, optional = _unwrap(hint)
    d = {
        "name": name,
        "label": (_m(meta, T.Label).value if _m(meta, T.Label) else name.replace("_", " ").capitalize()),
    }
    has_default = p.default is not inspect.Parameter.empty
    d["required"] = not (has_default or optional)
    if has_default and p.default is not None:
        d["default"] = p.default.value if isinstance(p.default, enum.Enum) else p.default
    if base in T.INPUT_TYPES:
        d["type"] = T.INPUT_TYPES[base]
        if _m(meta, T.Axes):
            d["axes"] = _m(meta, T.Axes).value
    elif get_origin(base) is Literal:
        ch = list(get_args(base))
        d["type"] = "choice"
        d["choices"] = ch
    elif isinstance(base, type) and issubclass(base, enum.Enum):
        d["type"] = "choice"
        d["choices"] = [e.value for e in base]
        if has_default and isinstance(p.default, enum.Enum):
            d["default"] = p.default.value
    elif base is bool:
        d["type"] = "boolean"
    elif base in SCALARS:
        d["type"] = SCALARS[base]
    elif base is __import__("pathlib").Path:
        d["type"] = "file"
    else:
        raise DeclarationError("parameter %r: unsupported annotation %r" % (name, hint))
    if d["type"] in ("integer", "float"):
        for key, cls in (("minimum", T.Min), ("maximum", T.Max)):
            if _m(meta, cls):
                d[key] = _m(meta, cls).value
        for k in ("minimum", "maximum"):
            if (
                k in d
                and "default" in d
                and ((k == "minimum" and d["default"] < d[k]) or (k == "maximum" and d["default"] > d[k]))
            ):
                raise DeclarationError(
                    "parameter %r: default %r violates %s %r" % (name, d["default"], k, d[k])
                )
        if _m(meta, T.Unit):
            d["unit"] = _m(meta, T.Unit).value
        if _m(meta, T.PixelSizeOf):
            d["pixel_size_of"] = _m(meta, T.PixelSizeOf).value
    desc = _m(meta, T.Description).value if _m(meta, T.Description) else argdoc.get(name)
    if desc:
        d["description"] = desc
    if _m(meta, T.Group):
        d["group"] = _m(meta, T.Group).value
    if _m(meta, T.Advanced) and _m(meta, T.Advanced).value:
        d["advanced"] = True
    when = _m(meta, T.EnabledWhen)
    if when:
        d["enabled_when"] = {"param": when.param, **({"equals": when.equals} if when.equals else {})}
    if not d["required"] and "default" not in d:
        # "unset" is a real value (default None / Optional[...]): hosts must be able to leave it unset and then omit it
        d["nullable"] = True
    if d["type"] == "choice" and "default" not in d and d["required"]:
        d["default"] = d["choices"][0]
    return d


def _outputs(ret, tool_id):
    if ret in (inspect.Signature.empty, None, type(None)):
        return []
    base, meta, _ = _unwrap(ret)
    items = [ret] if get_origin(base) is not tuple else list(get_args(base))
    outs = []
    for i, it in enumerate(items):
        b, m, _ = _unwrap(it)
        if b not in T.OUTPUT_TYPES:
            raise DeclarationError("tool %r output %d: unsupported return annotation %r" % (tool_id, i, it))
        o = {"name": _m(m, T.Name).value if _m(m, T.Name) else T.OUTPUT_TYPES[b], "type": T.OUTPUT_TYPES[b]}
        if _m(m, T.Axes):
            o["axes"] = _m(m, T.Axes).value
        a = _m(m, T.ApplyTo)
        if a:
            o["display"] = {"apply_to": a.source, **({"relative_to": a.target} if a.target else {})}
        outs.append(o)
    seen = {}
    for o in outs:  # unnamed outputs of the same type get a numeric suffix
        seen[o["name"]] = seen.get(o["name"], 0) + 1
        if seen[o["name"]] > 1:
            o["name"] += str(seen[o["name"]])
    names = [o["name"] for o in outs]
    if len(set(names)) != len(names):
        raise DeclarationError("tool %r: duplicate output names %s" % (tool_id, names))
    return outs


def describe_tool(t):
    fn = t.fn
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception as e:
        raise DeclarationError("tool %r: cannot resolve annotations (%s)" % (t.id, e)) from e
    argdoc = _docstring_args(fn.__doc__)
    ins = []
    for name, p in sig.parameters.items():
        if name not in hints:
            raise DeclarationError("tool %r: parameter %r has no type annotation" % (t.id, name))
        ins.append(_param(name, p, hints[name], argdoc))
    names = {i["name"] for i in ins}
    for i in ins:
        if "pixel_size_of" in i and i["pixel_size_of"] not in names:
            raise DeclarationError("tool %r: PixelSizeOf(%r) names no parameter" % (t.id, i["pixel_size_of"]))
    for i in ins:
        rule = i.get("enabled_when")
        if rule and rule["param"] not in names:
            raise DeclarationError(
                "tool %r: EnabledWhen(%r) on %r names no parameter" % (t.id, rule["param"], i["name"])
            )
        if rule and rule["param"] == i["name"]:
            raise DeclarationError("tool %r: parameter %r cannot be enabled by itself" % (t.id, i["name"]))
    outs = _outputs(hints.get("return", inspect.Signature.empty), t.id)
    for o in outs:
        for k in ("apply_to", "relative_to"):
            if k in o.get("display", {}) and o["display"][k] not in names:
                raise DeclarationError(
                    "tool %r: output %r refers to unknown parameter %r" % (t.id, o["name"], o["display"][k])
                )
    desc = (inspect.getdoc(fn) or "").split("\n\n")[0].replace("\n", " ").strip()
    return {
        "id": t.id,
        "label": t.label,
        **({"description": desc} if desc else {}),
        "inputs": ins,
        "outputs": outs,
    }


def describe_tools(module_name=None, application=None, version=None):
    """Deterministic JSON-compatible schema for all tools declared by `module_name`."""
    ts = sorted(tools_in(module_name), key=lambda t: t.id)
    out = {"protocol": PROTOCOL, "tools": [describe_tool(t) for t in ts]}
    if application:
        out["application"] = application
    if version:
        out["version"] = version
    return out
