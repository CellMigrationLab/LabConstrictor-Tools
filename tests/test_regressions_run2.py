"""Regression tests for problems found in the second source test run: a damaged TIFF that tifffile reads as an empty array,
worker pipes that were never closed, and --pythonpath being shadowed by the host interpreter's site-packages.
"""

import gc
import tempfile
import unittest
import warnings
from pathlib import Path

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import client, convert
from labconstrictor_tools.types import ToolError


class Run2(unittest.TestCase):
    def test_tiff_with_bad_first_page_offset_is_an_error_not_an_empty_image(self):
        path = Path(tempfile.mkdtemp()) / "damaged.tif"
        path.write_bytes(b"II*\x00garbage not a tiff")
        with self.assertRaises(ToolError) as caught:
            convert._read_image(str(path))
        self.assertEqual(caught.exception.code, "unreadable_image")

    def test_worker_pipes_are_closed_when_the_worker_ends(self):
        from _paths import SYNTHETIC_MODULE

        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always", ResourceWarning)
            with client.WorkerProcess(module=SYNTHETIC_MODULE) as worker:
                proc = worker.proc
                task = worker.task("scalar_echo", {"a": 1, "b": 2})
                task.wait(60)
            worker._stderr_thread.join(5)
            for _ in range(50):  # the reader threads close the pipes when they see EOF
                if proc.stdout.closed and proc.stderr.closed:
                    break
                import time

                time.sleep(0.1)
            del worker, task
            gc.collect()
        self.assertTrue(proc.stdout.closed and proc.stderr.closed)
        self.assertEqual([str(w.message) for w in seen if issubclass(w.category, ResourceWarning)], [])

    def test_pythonpath_comes_before_the_runtime_path(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "shadow_lc_tools.py").write_text(
            "from labconstrictor_tools import Scalars, tool\n"
            "@tool('Where')\n"
            "def where() -> Scalars:\n"
            "    import os\n"
            "    return {'pythonpath': os.environ['PYTHONPATH'].split(os.pathsep)[0]}\n"
        )
        with client.WorkerProcess(module="shadow_lc_tools", pythonpath=[str(folder)]) as worker:
            task = worker.task("where", {})
            task.wait(60)
        self.assertEqual(task.status, "COMPLETE", task.error)
        first = task.outputs["results"][0]["values"]["pythonpath"]
        self.assertEqual(Path(first).resolve(), folder.resolve())


class Schema(unittest.TestCase):
    def test_nullable_and_folder_in_the_manifest(self):
        from pathlib import Path as P
        from typing import Annotated, Optional

        from labconstrictor_tools import Folder, Min, Scalars
        from labconstrictor_tools.decorators import tool
        from labconstrictor_tools.introspection import describe_tool

        @tool("T", id="nullable_probe")
        def t(
            a: Optional[int] = None,
            b: Annotated[float, Min(0)] = 1.0,
            c: Optional[str] = None,
            d: Optional[Folder] = None,
            e: Optional[P] = None,
        ) -> Scalars:
            return {}

        by = {p["name"]: p for p in describe_tool(t.__lc_tool__)["inputs"]}
        self.assertTrue(
            by["a"]["nullable"] and by["c"]["nullable"] and by["d"]["nullable"] and by["e"]["nullable"]
        )
        self.assertNotIn("nullable", by["b"])
        self.assertEqual((by["d"]["type"], by["e"]["type"]), ("folder", "file"))

    def test_folder_input_must_be_a_directory(self):
        param = {"name": "f", "label": "F", "type": "folder", "required": True}
        self.assertEqual(convert._load_one(param, tempfile.gettempdir()), Path(tempfile.gettempdir()))
        with self.assertRaises(ToolError) as caught:
            convert._load_one(param, "/definitely/not/here")
        self.assertEqual(caught.exception.code, "folder_not_found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
