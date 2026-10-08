"""The installation checks: each probe is isolated, advice is attached to every failure, and no heavy library is imported to find it missing."""

import importlib.machinery
import json
import sys
import types
import unittest
from unittest import mock

import _paths  # noqa: F401  (must come first)

from labconstrictor_tools import diagnostics as d


def fake_torch(*, cuda=False, cuda_build="12.4", mps=False, hip=None, devices=1):
    """A stand-in for PyTorch: just enough of the surface the probes touch."""
    torch = types.ModuleType("torch")
    torch.__spec__ = importlib.machinery.ModuleSpec("torch", None)
    torch.__version__ = "2.9.0"
    torch.version = types.SimpleNamespace(cuda=cuda_build, hip=hip)
    props = types.SimpleNamespace(name="Fake GPU", total_memory=8 * 1024**3)
    torch.cuda = types.SimpleNamespace(
        is_available=lambda: cuda,
        device_count=lambda: devices,
        get_device_properties=lambda i: props,
        synchronize=lambda: None,
    )
    torch.backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: mps, is_built=lambda: True)
    )
    return torch


NVIDIA_PRESENT = [d.Check("gpu tools", "NVIDIA GPU 0", d.OK, "Fake GPU")]


class ParsingAndShape(unittest.TestCase):
    def test_nvidia_smi_lines_are_parsed(self):
        text = "NVIDIA RTX A4000, 535.104.05, 16376\nNVIDIA RTX A4000, 535.104.05, 16376\n"
        gpus = d.parse_nvidia_smi(text)
        self.assertEqual([g["name"] for g in gpus], ["NVIDIA RTX A4000"] * 2)
        self.assertEqual(gpus[0]["memory_mb"], 16376.0)

    def test_garbage_from_nvidia_smi_gives_no_gpus(self):
        self.assertEqual(d.parse_nvidia_smi("Failed to initialize NVML: Driver/library version mismatch"), [])

    def test_default_run_is_json_serialisable_and_has_every_layer(self):
        checks = d.run_checks(benchmark=False)
        layers = {c.layer for c in checks}
        self.assertTrue({"machine", "worker", "gpu tools", "gpu libraries"} <= layers)
        parsed = json.loads(d.as_json(checks))
        self.assertEqual(len(parsed["checks"]), len(checks))

    def test_importing_the_module_stays_light(self):
        import subprocess

        code = "import sys, labconstrictor_tools.diagnostics\nheavy=[m for m in ('torch','numpy','pandas','tensorflow') if m in sys.modules]\nassert not heavy, heavy"
        done = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env={**__import__("os").environ, "PYTHONPATH": str(_paths.ROOT)},
        )
        self.assertEqual(done.returncode, 0, done.stderr)


class IsolationAndSummary(unittest.TestCase):
    def test_a_probe_that_raises_becomes_one_failed_check_and_the_others_run(self):
        def broken():
            raise RuntimeError("boom")

        checks = d.run_checks(benchmark=False, extra=[broken])
        failed = [c for c in checks if c.layer == "probe"]
        self.assertEqual(len(failed), 1)
        self.assertIn("boom", failed[0].detail)
        self.assertTrue(any(c.layer == "machine" for c in checks))

    def test_summary_lists_the_fix_beside_every_failure(self):
        text = d.summary(
            [
                d.Check("gpu", "CUDA", d.FAIL, "cannot be used", "update the driver"),
                d.Check("machine", "memory", d.OK, "16 GB"),
            ]
        )
        self.assertIn("1 failure", text)
        self.assertIn("Fix: update the driver", text)
        self.assertIn("✖ **gpu**", text)
        self.assertIn("✔ **machine**", text)

    def test_what_was_found_is_listed_under_the_tick(self):
        text = d.summary(
            [
                d.Check("machine", "cpu", d.INFO, "8 logical cores"),
                d.Check("machine", "memory", d.OK, "16.0 GB"),
            ]
        )
        self.assertIn("- cpu: 8 logical cores", text)
        self.assertIn("- memory: 16.0 GB", text)

    def test_a_layer_with_a_warning_is_marked_as_one(self):
        text = d.summary(
            [d.Check("machine", "disk", d.WARN, "low", "free space"), d.Check("machine", "cpu", d.OK, "8")]
        )
        self.assertIn("⚠ **machine**", text)


class TorchProbes(unittest.TestCase):
    def run_probe(self, torch, gpu_tools=()):
        with (
            mock.patch.dict(sys.modules, {"torch": torch}),
            mock.patch.object(d, "probe_gpu_tools", return_value=list(gpu_tools)),
        ):
            return d.probe_torch()

    def status(self, checks, name):
        return next(c for c in checks if c.name == name).status

    def test_not_installed_is_information_not_a_failure(self):
        with (
            mock.patch.dict(sys.modules, {"torch": None}),
            mock.patch("importlib.util.find_spec", return_value=None),
        ):
            checks = d.probe_torch()
        self.assertEqual([(c.name, c.status) for c in checks], [("PyTorch", d.INFO)])

    def test_cpu_build_with_an_nvidia_gpu_says_to_reinstall_the_cuda_build(self):
        checks = self.run_probe(fake_torch(cuda=False, cuda_build=None), NVIDIA_PRESENT)
        cuda = next(c for c in checks if c.name == "CUDA")
        self.assertEqual(cuda.status, d.FAIL)
        self.assertIn("built without CUDA", cuda.detail)
        self.assertIn("CUDA build", cuda.fix)

    def test_cuda_build_that_cannot_use_the_gpu_points_at_the_driver(self):
        checks = self.run_probe(fake_torch(cuda=False, cuda_build="12.4"), NVIDIA_PRESENT)
        cuda = next(c for c in checks if c.name == "CUDA")
        self.assertEqual(cuda.status, d.FAIL)
        self.assertIn("driver", cuda.fix)

    def test_working_cuda_lists_each_device(self):
        checks = self.run_probe(fake_torch(cuda=True, devices=2), NVIDIA_PRESENT)
        self.assertEqual(
            [c.name for c in checks if c.name.startswith("CUDA device")], ["CUDA device 0", "CUDA device 1"]
        )

    def test_no_nvidia_and_no_cuda_is_just_information(self):
        checks = self.run_probe(fake_torch(cuda=False))
        self.assertEqual(self.status(checks, "CUDA"), d.INFO)

    def test_mps_available_is_ok(self):
        checks = self.run_probe(fake_torch(mps=True))
        self.assertEqual(self.status(checks, "MPS (Apple Metal)"), d.OK)

    def test_a_broken_import_is_a_finding_with_advice(self):
        def explode(name, *a, **k):
            raise ImportError("DLL load failed")

        with mock.patch.object(d, "_torch_module", side_effect=ImportError("DLL load failed")):
            checks = d.probe_torch()
        self.assertEqual(checks[0].status, d.FAIL)
        self.assertIn("Reinstall", checks[0].fix)

    def test_devices_list_always_starts_with_the_cpu(self):
        with mock.patch.dict(sys.modules, {"torch": fake_torch(cuda=True, devices=2, mps=True)}):
            self.assertEqual(d.torch_devices(), ["cpu", "cuda:0", "cuda:1", "mps"])
        with mock.patch.object(d, "_torch_module", return_value=None):
            self.assertEqual(d.torch_devices(), [])


class Benchmark(unittest.TestCase):
    def test_timings_are_extracted_for_a_figure(self):
        checks = [
            d.Check("benchmark", "cpu", d.OK, "12.5 ms per run (conv + matmul, 512x512)"),
            d.Check("benchmark", "cuda:0", d.FAIL, "boom"),
        ]
        self.assertEqual(d.benchmark_timings(checks), {"cpu": 12.5})

    def test_without_pytorch_the_benchmark_is_empty(self):
        with mock.patch.object(d, "_torch_module", return_value=None):
            self.assertEqual(d.probe_benchmark(), [])

    def test_real_pytorch_when_installed(self):
        try:
            import torch  # noqa: F401
        except ImportError:
            self.skipTest("PyTorch is not installed here")
        checks = d.probe_benchmark(size=64, repeats=1)
        self.assertTrue(
            checks and all(c.status == d.OK for c in checks), [c for c in checks if c.status != d.OK]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
