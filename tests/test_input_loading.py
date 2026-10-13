"""How the worker reads an image input: the memory order of a shared-memory block, and the memory-mapped read of big TIFF files.

* `order` of a shared-memory descriptor (docs/PROTOCOL.md): C and F are read correctly (a non-symmetric array, so that a transpose
  is noticed), anything else is refused with `unreadable_image` and never read transposed.
* An uncompressed, contiguous, single-series TIFF over `convert.MEMMAP_MIN_BYTES` is mapped copy-on-write instead of read: the tool
  gets the same shape, dtype and values as from `tifffile.imread`, a tool that writes to its input changes nothing on disk, and the
  mapping is released when the task ends. Compressed, tiled, multi-series, non-contiguous, OME, non-native byte order, small and
  cut-short files are read the plain way.
"""

import hashlib
import logging
import mmap
import os
import tempfile
import unittest
from multiprocessing import shared_memory
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import _paths  # noqa: F401  (must come first)
import numpy as np
import tifffile

from labconstrictor_tools import convert
from labconstrictor_tools.client import WorkerProcess
from labconstrictor_tools.types import ToolError

if TYPE_CHECKING:
    from typing import Any

    from labconstrictor_tools.client import Task

INPUT_APP = Path(__file__).resolve().parent / "input_app"
IMAGE_PARAM = {"name": "n", "label": "N", "type": "image", "required": True}


def is_mapped(array: object) -> bool:
    base = array
    while base is not None:
        if isinstance(base, mmap.mmap):
            return True
        base = getattr(base, "base", None)
    return False


def digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_with_a_gap(path: str | Path, stack: np.ndarray) -> None:
    """A classic TIFF stack in one series whose second page's pixels were moved to the end of the file: the pages are no longer
    one block of bytes. (tifffile never writes this itself, so the offset of the page is patched in the file.)
    """
    import struct

    tifffile.imwrite(path, stack, photometric="minisblack", rowsperstrip=stack.shape[1])
    with tifffile.TiffFile(path) as tif:
        second = tif.pages[1]
        assert len(second.dataoffsets) == 1 and tif.byteorder == "<"
        entry = second.tags["StripOffsets"]
        slot, start, size = entry.valueoffset, second.dataoffsets[0], second.databytecounts[0]
    data = Path(path).read_bytes()
    moved = data + b"\0" * 777 + data[start : start + size]
    moved = moved[:slot] + struct.pack("<I", len(data) + 777) + moved[slot + 4 :]
    Path(path).write_bytes(moved)


def non_symmetric(shape: tuple[int, ...], dtype: str = "uint16") -> np.ndarray:
    return (np.arange(int(np.prod(shape))).reshape(shape) * 3 % 251).astype(dtype)


class SharedMemoryOrder(unittest.TestCase):
    def descriptor(
        self, block: shared_memory.SharedMemory, array: np.ndarray, **changes: "Any"
    ) -> "dict[str, Any]":
        return {
            "appose_type": "ndarray",
            "shm": {"name": block.name},
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            **changes,
        }

    def block_with(self, array: np.ndarray, order: str) -> shared_memory.SharedMemory:
        block = shared_memory.SharedMemory(create=True, size=array.nbytes)
        self.addCleanup(block.unlink)
        self.addCleanup(block.close)
        np.ndarray(array.shape, dtype=array.dtype, buffer=block.buf, order=order)[...] = array
        return block

    def test_f_order_is_read_with_the_right_strides_not_transposed(self) -> None:
        for shape in ((3, 5), (4, 2, 6)):
            array = non_symmetric(shape)
            block = self.block_with(array, "F")
            for spelling in ("F", "F_ORDER"):
                with self.subTest(shape=shape, order=spelling):
                    got = convert._load_one(IMAGE_PARAM, self.descriptor(block, array, order=spelling))
                    self.assertEqual(got.shape, array.shape)
                    np.testing.assert_array_equal(got, array)
                    self.assertTrue(got.flags.c_contiguous)  # the tool always gets a C-ordered array

    def test_c_order_and_no_order_are_the_same_row_major_read(self) -> None:
        array = non_symmetric((3, 5))
        block = self.block_with(array, "C")
        for changes in ({}, {"order": "C"}, {"order": "C_ORDER"}):
            with self.subTest(changes):
                got = convert._load_one(IMAGE_PARAM, self.descriptor(block, array, **changes))
                np.testing.assert_array_equal(got, array)

    def test_any_other_order_is_refused_with_a_message(self) -> None:
        array = non_symmetric((3, 5))
        block = self.block_with(array, "C")
        for bad in ("A", "f", "c", "", "K", "FORTRAN", None, 1, ["F"], {"F": 1}):
            with self.subTest(order=bad):
                with self.assertRaises(ToolError) as caught:
                    convert._load_one(IMAGE_PARAM, self.descriptor(block, array, order=bad))
                self.assertEqual(caught.exception.code, "unreadable_image")
                self.assertIn("order", caught.exception.message)
                self.assertIn("'C' or 'F'", caught.exception.message)

    def test_through_a_real_worker(self) -> None:
        array = non_symmetric((3, 5))
        f_block = self.block_with(array, "F")
        worker = WorkerProcess(
            module="labconstrictor_tools.examples.roundtrip", pythonpath=[str(_paths.ROOT)]
        )
        try:
            ok = worker.task("echo_image", {"image": self.descriptor(f_block, array, order="F")}).wait(60)
            self.assertEqual(ok.status, "COMPLETE", ok.error)
            received = ok.outputs["results"][1]["values"]
            self.assertEqual(received["shape"], [3, 5])
            self.assertEqual(
                received["digest"], hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
            )
            refused = worker.task("echo_image", {"image": self.descriptor(f_block, array, order="Z")}).wait(
                60
            )
            self.assertEqual(refused.status, "FAILED")
            self.assertEqual(refused.code, "unreadable_image")
        finally:
            worker.close()


class MappedTiff(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="lcmap_"))
        patch = mock.patch.object(convert, "MEMMAP_MIN_BYTES", 0)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.cleanup)

    def cleanup(self) -> None:
        import gc
        import shutil

        gc.collect()  # a mapping would keep the files locked on Windows
        shutil.rmtree(self.folder, ignore_errors=True)

    def write(self, name: str, data: np.ndarray, **options: "Any") -> Path:
        path = self.folder / name
        tifffile.imwrite(path, data, **options)
        return path

    def read(self, path: str | Path) -> np.ndarray:
        return convert._read_image(str(path), "N")

    def assertSameAsImread(self, path: str | Path, mapped: bool) -> np.ndarray:
        got = self.read(path)
        expected = tifffile.imread(path)
        self.assertEqual(is_mapped(got), mapped, "mapped" if not mapped else "not mapped")
        self.assertEqual(got.shape, expected.shape)
        self.assertEqual(got.dtype, expected.dtype)
        np.testing.assert_array_equal(got, expected)
        self.assertIs(type(got), np.ndarray)
        return got

    def test_the_simple_cases_are_mapped_and_equal_to_imread(self) -> None:
        cases = {
            "u8": (non_symmetric((7, 9), "uint8"), {}),
            "u16": (non_symmetric((7, 9)), {}),
            "i16": (non_symmetric((7, 9), "int16") - 100, {}),
            "u32": (non_symmetric((7, 9), "uint32") * 70000, {}),
            "f32": (non_symmetric((7, 9), "float32") / 7, {}),
            "f64": (non_symmetric((7, 9), "float64") / 7, {}),
            "stack": (non_symmetric((4, 7, 9)), {"photometric": "minisblack"}),
            "rgb": (non_symmetric((7, 9, 3), "uint8"), {"photometric": "rgb"}),
            "imagej": (non_symmetric((2, 3, 7, 9)), {"imagej": True, "metadata": {"axes": "TZYX"}}),
            "bigtiff": (non_symmetric((7, 9)), {"bigtiff": True}),
            "many strips": (non_symmetric((16, 9)), {"rowsperstrip": 4}),
        }
        for name, (data, options) in cases.items():
            with self.subTest(name):
                self.assertSameAsImread(self.write(name + ".tif", data, **options), mapped=True)

    def test_everything_else_is_read_the_plain_way_with_the_same_result(self) -> None:
        data = non_symmetric((16, 32))
        stack = non_symmetric((3, 16, 32))
        multi = self.folder / "multi.tif"
        with tifffile.TiffWriter(multi) as writer:
            writer.write(data, contiguous=False)
            writer.write(data[::-1].copy(), contiguous=False)
        gap = self.folder / "gap.tif"
        write_with_a_gap(gap, stack)
        with tifffile.TiffFile(gap) as tif:
            self.assertEqual(len(tif.series), 1)  # one series, so only the gap keeps it from being mapped
        np.testing.assert_array_equal(tifffile.imread(gap), stack)  # and the patched file is a valid one
        pyramid = self.folder / "pyr.tif"
        with tifffile.TiffWriter(pyramid) as writer:
            writer.write(data, subifds=1)
            writer.write(data[::2, ::2].copy(), subfiletype=1)
        cases = {
            "compressed": self.write("zlib.tif", data, compression="zlib"),
            "tiled": self.write("tiled.tif", data, tile=(16, 16)),
            "predictor": self.write("pred.tif", data, compression="zlib", predictor=True),
            "non-contiguous": gap,
            "two series": multi,
            "ome": self.write("o.ome.tif", data, ome=True),
            "big-endian": self.write("be.tif", data, byteorder=">" if np.little_endian else "<"),
            "pyramid": pyramid,
        }
        for name, path in cases.items():
            with self.subTest(name):
                self.assertSameAsImread(path, mapped=False)

    def test_a_small_file_is_not_mapped(self) -> None:
        path = self.write("small.tif", non_symmetric((7, 9)))
        with mock.patch.object(convert, "MEMMAP_MIN_BYTES", 1 << 20):
            self.assertFalse(is_mapped(self.read(path)))
        with mock.patch.object(convert, "MEMMAP_MIN_BYTES", 0):
            self.assertTrue(is_mapped(self.read(path)))

    def test_the_environment_switch_turns_it_off(self) -> None:
        path = self.write("a.tif", non_symmetric((7, 9)))
        with mock.patch.dict(os.environ, {convert.MEMMAP_ENV: "0"}):
            self.assertFalse(is_mapped(self.read(path)))

    def test_a_file_cut_short_is_not_mapped_and_gives_what_the_plain_reader_gives(self) -> None:
        path = self.write("cut.tif", non_symmetric((64, 64)))
        data = path.read_bytes()
        path.write_bytes(data[: len(data) - 4000])
        self.assertIsNone(convert._memmap_tiff(path))
        with self.assertRaises(ValueError):
            tifffile.imread(path)  # the reference: the plain reader refuses a cut file
        with self.assertLogs("labconstrictor.convert", "ERROR"), self.assertRaises(ToolError) as caught:
            self.read(path)
        self.assertEqual(caught.exception.code, "unreadable_image")

    def told(self, path: Path) -> "tuple[Any, list[str], str]":
        """What `_memmap_tiff` says about `path`: the log records of the worker's logger and the text on stderr."""
        import io
        from contextlib import redirect_stderr

        with mock.patch.dict(os.environ, {"LC_HOME": str(self.folder / "home")}):
            stderr = io.StringIO()
            with self.assertLogs("labconstrictor", "DEBUG") as logged, redirect_stderr(stderr):
                logging.getLogger("labconstrictor").debug("marker")  # assertLogs fails on no record at all
                mapped = convert._memmap_tiff(path)
        lines = [r.getMessage() for r in logged.records if r.levelno >= logging.WARNING]
        return mapped, lines, stderr.getvalue()

    def test_a_file_that_could_not_be_mapped_says_why_in_the_log_and_on_stderr(self) -> None:
        data = non_symmetric((16, 32))
        multi = self.folder / "multi.tif"
        with tifffile.TiffWriter(multi) as writer:
            writer.write(data, contiguous=False)
            writer.write(data[::-1].copy(), contiguous=False)
        gap = self.folder / "gap.tif"
        write_with_a_gap(gap, non_symmetric((3, 16, 32)))
        cut = self.write("cut.tif", non_symmetric((64, 64)))
        cut.write_bytes(cut.read_bytes()[:-4000])
        cases = {
            "compressed": self.write("zlib.tif", data, compression="zlib"),
            "tiled": self.write("tiled.tif", data, tile=(16, 16)),
            "multi-series": multi,
            "big-endian": self.write("be.tif", data, byteorder=">" if np.little_endian else "<"),
            "not contiguous": gap,
            "truncated": cut,
        }
        for reason, path in cases.items():
            with self.subTest(reason):
                mapped, lines, stderr = self.told(path)
                self.assertIsNone(mapped)
                self.assertEqual(len(lines), 1, lines)
                self.assertIn(path.name, lines[0])
                self.assertIn(reason, lines[0])
                self.assertIn(lines[0].split("convert: ")[-1], stderr)
                self.assertTrue(stderr.startswith("LabConstrictor worker: "), stderr)

    def test_the_environment_switch_is_told_for_a_big_file(self) -> None:
        path = self.write("a.tif", non_symmetric((7, 9)))
        with mock.patch.dict(os.environ, {convert.MEMMAP_ENV: "0"}):
            mapped, lines, _ = self.told(path)
        self.assertIsNone(mapped)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn(convert.MEMMAP_ENV, lines[0])

    def test_nothing_is_said_for_a_small_file_or_a_mapped_one(self) -> None:
        small = self.write("small.tif", non_symmetric((7, 9)))
        small_compressed = self.write("smallz.tif", non_symmetric((16, 32)), compression="zlib")
        with mock.patch.object(convert, "MEMMAP_MIN_BYTES", 1 << 20):
            for path in (small, small_compressed):
                mapped, lines, stderr = self.told(path)
                self.assertIsNone(mapped)
                self.assertEqual((lines, stderr), ([], ""))
        mapped, lines, stderr = self.told(small)  # threshold 0 again: mapped, so nothing to tell either
        self.assertIsNotNone(mapped)
        self.assertEqual((lines, stderr), ([], ""))
        del mapped

    def test_writing_to_the_input_works_and_never_reaches_the_file(self) -> None:
        path = self.write("mine.tif", non_symmetric((64, 64)))
        before, mtime = digest(path), path.stat().st_mtime_ns
        original = tifffile.imread(path)
        got = self.read(path)
        self.assertTrue(is_mapped(got))
        self.assertTrue(
            got.flags.writeable
        )  # same as an array from imread: tools written for arrays in memory keep working
        got[...] = 0
        got[3, 4] = 9
        self.assertEqual(int(got.sum()), 9)
        del got
        import gc

        gc.collect()
        self.assertEqual(digest(path), before)
        self.assertEqual(path.stat().st_mtime_ns, mtime)
        np.testing.assert_array_equal(tifffile.imread(path), original)

    def test_results_of_arithmetic_are_plain_arrays(self) -> None:
        got = self.read(self.write("a.tif", non_symmetric((7, 9))))
        self.assertIs(type(got + 1), np.ndarray)
        self.assertIs(type(got.max(axis=0)), np.ndarray)


class MappedTiffThroughAWorker(unittest.TestCase):
    """Files above the real threshold, through a real worker: what the tool sees, what stays on disk, what is released."""

    SIDE = 2400  # 11 MiB as uint16, over MEMMAP_MIN_BYTES

    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = Path(tempfile.mkdtemp(prefix="lcmapw_"))
        cls.array = non_symmetric((cls.SIDE, cls.SIDE))
        cls.path = cls.folder / "big.tif"
        tifffile.imwrite(cls.path, cls.array)
        assert cls.array.nbytes > convert.MEMMAP_MIN_BYTES
        cls.sha = hashlib.sha256(cls.array.tobytes()).hexdigest()

    @classmethod
    def tearDownClass(cls) -> None:
        import shutil

        shutil.rmtree(cls.folder, ignore_errors=True)

    def run_tool(self, tool_id: str, path: str | Path, env: dict[str, str] | None = None) -> "Task":
        old = {key: os.environ.get(key) for key in (env or {})}
        os.environ.update(env or {})
        try:
            worker = WorkerProcess(module="input_tools", pythonpath=[str(INPUT_APP)])
            try:
                return worker.task(tool_id, {"image": str(path)}).wait(120)
            finally:
                worker.close()
        finally:
            for key, value in old.items():
                os.environ.pop(key, None) if value is None else os.environ.__setitem__(key, value)

    def test_the_tool_gets_the_same_array_mapped(self) -> None:
        task = self.run_tool("report", self.path)
        self.assertEqual(task.status, "COMPLETE", task.error)
        values = task.outputs["results"][0]["values"]
        self.assertTrue(values["mapped"])
        self.assertEqual(
            (values["dtype"], values["shape"], values["sha256"]), ("uint16", [self.SIDE] * 2, self.sha)
        )
        self.assertTrue(values["writeable"])
        self.assertTrue(values["plain_ndarray"])

    def test_the_switch_reaches_the_worker(self) -> None:
        values = self.run_tool("report", self.path, {convert.MEMMAP_ENV: "0"}).outputs["results"][0]["values"]
        self.assertFalse(values["mapped"])
        self.assertEqual(values["sha256"], self.sha)

    def test_a_tool_that_writes_to_its_input_cannot_change_the_file(self) -> None:
        copy = self.folder / "to_scribble.tif"
        copy.write_bytes(self.path.read_bytes())
        task = self.run_tool("scribble", copy)
        self.assertEqual(task.status, "COMPLETE", task.error)
        values = task.outputs["results"][0]["values"]
        self.assertTrue(values["mapped"])
        self.assertNotEqual(values["sha256"], self.sha)  # the tool really changed its array
        self.assertEqual(digest(copy), digest(self.path))  # and the file did not change
        os.remove(copy)  # nothing keeps it open (a mapping would block this on Windows)

    def test_the_file_is_free_when_the_task_has_ended_even_after_a_failure(self) -> None:
        for tool_id, status in (("report", "COMPLETE"), ("fail_holding", "FAILED")):
            with self.subTest(tool_id):
                copy = self.folder / ("free_%s.tif" % tool_id)
                copy.write_bytes(self.path.read_bytes())
                worker = WorkerProcess(module="input_tools", pythonpath=[str(INPUT_APP)])
                try:
                    task = worker.task(tool_id, {"image": str(copy)}).wait(120)
                    self.assertEqual(task.status, status, task.error)
                    if os.path.exists(
                        "/proc/self/maps"
                    ):  # Linux does not lock a mapped file: look at the worker's mappings
                        again = worker.task("mappings_of", {"path": str(copy)}).wait(60)
                        self.assertEqual(again.outputs["results"][0]["values"]["mappings"], 0)
                    os.remove(
                        copy
                    )  # the worker is still alive and has let go of the file (Windows would refuse otherwise)
                    self.assertFalse(copy.exists())
                finally:
                    worker.close()


if __name__ == "__main__":
    unittest.main()
