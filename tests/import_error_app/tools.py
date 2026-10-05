import a_package_that_is_not_installed  # noqa: F401  (deliberate: the worker must explain this)

from labconstrictor_tools import Scalars, tool


@tool("Never reached")
def never(a: float = 1.0) -> Scalars:
    return {}
