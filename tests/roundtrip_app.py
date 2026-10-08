"""The declarations of an example app, read from the PRODUCTION registry, robust against other test modules clearing it.

`unittest discover` runs every test file in one process, and some of the older ones empty the global tool registry
(`decorators.clear()`); importing a module again does nothing (it is cached), so the declarations would be gone. Reloading
the module registers its tools again.
"""

import importlib

from labconstrictor_tools.decorators import tools_in
from labconstrictor_tools.introspection import describe_tools


def declared(module_name):
    """-> {tool id: (schema, function)} of the tools declared by `module_name`."""
    module = importlib.import_module(module_name)
    if not tools_in(module_name):
        module = importlib.reload(module)
    schemas = {t["id"]: t for t in describe_tools(module_name)["tools"]}
    return {t.id: (schemas[t.id], t.fn) for t in tools_in(module_name)}


def schemas(module_name):
    return {tool_id: schema for tool_id, (schema, _) in declared(module_name).items()}
