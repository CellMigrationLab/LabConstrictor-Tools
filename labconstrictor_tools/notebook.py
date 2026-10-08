"""Render a declared tool as an ipywidgets form inside a Jupyter notebook (LabConstrictor apps are notebooks).

    from labconstrictor_tools.notebook import form
    form(my_tool_function)        # shows the form; the tool runs in THIS kernel (no worker process needed)

The form is generated from the same schema as the Napari and Fiji GUIs, and goes through the same input validation and
result conversion, so a tool behaves identically in all four front-ends (notebook, Napari, Fiji, command line).
"""

import logging
import tempfile
from collections.abc import Callable
from typing import Any

from . import convert, runtime
from . import types as T
from .introspection import describe_tool
from .structures import ParamSchema, Result


class ToolForm:
    """The form of one tool. ipywidgets is imported inside, so importing this module works without it installed."""

    def __init__(self, function: Callable[..., Any]) -> None:
        try:
            import ipywidgets as widgets
        except ImportError as error:
            raise ImportError(
                "labconstrictor_tools.notebook needs ipywidgets (pip install ipywidgets)"
            ) from error
        if not hasattr(function, "__lc_tool__"):
            raise ValueError("%r is not a declared tool (missing @tool)" % function)
        self._w = widgets
        self.function = function
        self.schema = describe_tool(function.__lc_tool__)
        self.controls = {p["name"]: self._control(p) for p in self.schema["inputs"]}
        self.run_button = widgets.Button(description="Run", button_style="primary")
        self.progress = widgets.FloatProgress(
            min=0, max=1, layout=widgets.Layout(width="100%", visibility="hidden")
        )
        self.status = widgets.HTML()
        self.output = widgets.Output()
        self.run_button.on_click(lambda _button: self.run())
        title = widgets.HTML(
            "<b>%s</b><br><i>%s</i>" % (self.schema["label"], self.schema.get("description", ""))
        )
        self.widget = widgets.VBox(
            [title, *self.controls.values(), self.run_button, self.progress, self.status, self.output]
        )
        self.results: list[Result] | None = None

    # ---- controls (same type mapping as the other hosts)
    def _control(self, param: ParamSchema) -> Any:
        w, kind = self._w, param["type"]
        common = {
            "description": param["label"],
            "style": {"description_width": "initial"},
            "layout": w.Layout(width="auto"),
        }
        tooltip = param.get("description", "")
        default = param.get("default")
        if kind in ("image", "labels", "table", "file", "folder", "string"):
            hint = {
                "image": "path to a TIFF image",
                "labels": "path to a TIFF label image",
                "table": "path to a CSV file",
            }.get(kind, "")
            control = w.Text(value="" if default is None else str(default), placeholder=hint, **common)
        elif kind == "integer":
            control = w.BoundedIntText(
                value=int(default or 0),
                min=param.get("minimum", -(10**9)),
                max=param.get("maximum", 10**9),
                **common,
            )
        elif kind == "float":
            control = w.BoundedFloatText(
                value=float(default or 0),
                min=param.get("minimum", -1e9),
                max=param.get("maximum", 1e9),
                step=1e-4,
                **common,
            )
        elif kind == "boolean":
            control = w.Checkbox(value=bool(default), **{**common, "layout": w.Layout()})
        elif kind == "choice":
            control = w.Dropdown(
                options=param["choices"],
                value=default if default in param["choices"] else param["choices"][0],
                **common,
            )
        else:
            raise ValueError("unsupported parameter type %r" % kind)
        control.tooltip = tooltip
        return control

    def values(self) -> dict[str, Any]:
        """Control values -> the inputs the worker would receive (empty optional paths are left out)."""
        inputs: dict[str, Any] = {}
        for param in self.schema["inputs"]:
            value = self.controls[param["name"]].value
            if param["type"] in ("image", "labels", "table", "file", "folder") and not str(value).strip():
                continue
            inputs[param["name"]] = value
        return inputs

    # ---- run (in this kernel)
    def run(self) -> list[Result] | None:
        """Run the tool with the current control values. Returns the list of typed results, or None if it failed."""
        self.output.clear_output()
        self.progress.layout.visibility = "visible"
        self.run_button.disabled = True
        runtime.install(progress=self._on_progress, cancelled=lambda: False)
        self.results = None
        try:
            kwargs = convert.load_inputs(self.schema, self.values(), self.function)
            returned = self.function(**kwargs)
            self.results = convert.build_results(self.schema, returned, tempfile.mkdtemp(prefix="lcnb_"))
            self.status.value = "✔ done"
            self._show(self.results)
        except T.ToolError as error:
            self.status.value = "✖ <b>%s</b>: %s" % (error.code, error.message)
        except (
            Exception
        ) as error:  # noqa: BLE001 - UI boundary: any tool failure is shown in the form, and logged with its traceback
            logging.getLogger("labconstrictor.notebook").error(
                "tool run failed in the notebook form", exc_info=True
            )
            self.status.value = "✖ <b>%s</b>: %s" % (type(error).__name__, error)
        finally:
            runtime.install()
            self.progress.layout.visibility = "hidden"
            self.run_button.disabled = False
        return self.results

    def _on_progress(self, fraction: float | None, message: str) -> None:
        if fraction is not None:
            self.progress.value = fraction
        self.status.value = str(message)

    def _show(self, results: list[Result]) -> None:
        with self.output:
            for result in results:
                kind = result["type"]
                if kind in ("image", "labels"):
                    self._show_image(result)
                elif kind == "table":
                    import pandas as pd
                    from IPython.display import display

                    display(pd.read_csv(result["path"]))
                elif kind == "values":
                    print(result["name"], result["values"])
                elif kind == "message":
                    print(result["text"])
                elif kind == "points":
                    import pandas as pd
                    from IPython.display import display

                    display(pd.read_csv(result["path"]))
                elif kind == "shapes":
                    print(result["name"], "%d outline(s):" % result["n"], result["path"])
                elif kind == "affine":
                    print(
                        result["name"],
                        "(%s -> %s):" % (result.get("apply_to"), result.get("relative_to", "reference")),
                    )
                    for row in result["matrix_yx"]:
                        print("  ", [round(x, 4) for x in row])
                else:
                    print(result["name"], result.get("path", ""))

    @staticmethod
    def _show_image(result: Result) -> None:
        import matplotlib.pyplot as plt
        import tifffile

        array = tifffile.imread(result["path"])
        while array.ndim > 2:
            array = array[0]
        plt.figure(figsize=(5, 5))
        plt.imshow(array, cmap="gray")
        plt.title(result["name"])
        plt.axis("off")
        plt.show()


def form(function: Callable[..., Any]) -> ToolForm:
    """Show (and return) the form for a declared tool."""
    from IPython.display import display

    tool_form = ToolForm(function)
    display(tool_form.widget)
    return tool_form
