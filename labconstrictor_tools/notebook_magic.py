"""Jupyter cell magic for tool authors.

    %load_ext labconstrictor_tools.notebook_magic

    %%lc_tool "Gaussian blur" --export lc_tools.py
    def blur(image: Image, sigma: Annotated[float, Min(0)] = 2.0) -> ImageOut:
        from skimage.filters import gaussian
        return gaussian(image, sigma)

The cell runs normally (the names `Image`, `Annotated`, `tool` ... are already available), is checked as a standalone
module, shown as the same form the Napari/Fiji hosts will generate, and - with --export - written to a module that
`labconstrictor-tools check` and `register` accept. From a terminal: `labconstrictor-tools export-notebook nb.ipynb`.
"""

from . import exporter


def load_ipython_extension(ip):
    ip.register_magic_function(lc_tool, magic_kind="cell", magic_name="lc_tool")
    exec(exporter.PRELUDE, ip.user_ns)  # noqa: S102 - makes the declaration names available without imports


def lc_tool(line, cell):
    from IPython import get_ipython

    ip = get_ipython()
    try:
        arguments = exporter.parse_magic_line(line)
        prepared = exporter.check(exporter.prepare(cell, arguments.label, arguments.function))
    except (exporter.CellError, SystemExit) as error:
        print("✖ %s" % (error or "bad %%lc_tool arguments"))
        return None
    for text in prepared.warnings:
        print("⚠ %s" % text)
    if prepared.problems:
        for text in prepared.problems:
            print("✖ %s: %s" % (prepared.name, text))
        print("(the cell was not run and nothing was exported)")
        return None
    ip.run_cell(prepared.code)
    function = ip.user_ns[prepared.name]
    if arguments.export:
        path = exporter.export(arguments.export, [prepared])
        print("✔ %s exported to %s" % (prepared.name, path))
    if not arguments.no_form:
        try:
            from IPython.display import display

            from .notebook import ToolForm

            display(ToolForm(function).widget)
        except ImportError as error:
            print("(no form: %s)" % error)
    return None
