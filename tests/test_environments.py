"""Multi-app / odd-environment behaviour: concurrency, read-only (network-like) install, registry robustness, orphaned workers."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import EVIDENCE as EV
from _paths import FIXTURES as FX
from _paths import GENERIC_PREFIX, SYNTHETIC_MODULE, V3

from labconstrictor_tools import client, registry

REPORT = {}
RO_PREFIX = (
    Path(os.environ["LC_TEST_RO_PREFIX"]) if os.environ.get("LC_TEST_RO_PREFIX") else None
)  # read-only mount of an environment with numpy+pandas (optional)


def alive(pid):
    return Path("/proc/%d" % pid).exists() and "Z" not in Path("/proc/%d/stat" % pid).read_text().split()[2]


class Environments(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        (EV / "environments.json").write_text(json.dumps(REPORT, indent=2, default=str))
        for name in ("ro_app", "dup", "broken_schema", "future_protocol", "copy_a", "copy_b", "copy_c"):
            registry.unregister(name)

    def test_1_several_apps_run_concurrently(self):
        names = (
            "copy_a",
            "copy_b",
            "copy_c",
        )  # three registered apps (real installs in the field), each busy for ~3 s
        for name in names:
            registry.register(name, GENERIC_PREFIX, SYNTHETIC_MODULE, "1")
        results, started = {}, time.time()

        def go(app):
            t0 = time.time()
            task = client.run_once(app, "slow", {"seconds": 3.0, "steps": 6}, timeout=120)
            results[app] = (task.status, round(time.time() - t0, 1))

        threads = [threading.Thread(target=go, args=(a,)) for a in names]
        [t.start() for t in threads]
        [t.join() for t in threads]
        wall = round(time.time() - started, 1)
        REPORT["concurrent"] = {
            "results": results,
            "wall_s": wall,
            "sum_of_individual_s": round(sum(v[1] for v in results.values()), 1),
        }
        self.assertTrue(all(status == "COMPLETE" for status, _ in results.values()), results)
        self.assertLess(wall, 0.8 * sum(v[1] for v in results.values()), "apps did not run in parallel")

    def test_2_read_only_install_prefix(self):
        if RO_PREFIX is None or not RO_PREFIX.exists():
            self.skipTest(
                "set LC_TEST_RO_PREFIX to a read-only mounted environment (numpy + pandas) to run this"
            )
        registry.register("ro_app", RO_PREFIX, SYNTHETIC_MODULE, "1", [], "Read-only")
        task = client.run_once("ro_app", "table_sum", {"tab": str(FX / "celltracks/tracks.csv")}, timeout=120)
        REPORT["read_only_prefix"] = {
            "status": task.status,
            "interpreter": (task.outputs.get("diagnostics") or {}).get("sys.prefix"),
            "error": task.error,
        }
        self.assertEqual(task.status, "COMPLETE", task.error)

    def test_3_duplicate_app_names_collide(self):
        registry.register("dup", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", [], "App v1")
        registry.register("dup", GENERIC_PREFIX, SYNTHETIC_MODULE, "2", [], "App v2")
        entry = registry.load_all()["dup"]
        REPORT["duplicate_names"] = {
            "entries_visible": 1,
            "survivor_version": entry["version"],
            "survivor_prefix": entry["prefix"],
        }
        self.assertEqual(
            entry["version"], "2"
        )  # documents the behaviour: the later install silently replaces the earlier one

    def test_4_one_broken_app_must_not_hide_the_others(self):
        registry.register("broken_schema", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", [], "Broken")
        Path(registry.load_all()["broken_schema"]["schema_path"]).write_text("{ not json")
        schemas, problems = registry.load_schemas()
        REPORT["broken_schema"] = {"apps_still_listed": sorted(schemas), "problems": problems}
        self.assertIn("synthetic", schemas)
        self.assertNotIn("broken_schema", schemas)
        self.assertTrue(any(name == "broken_schema" for name, _ in problems))

    def test_5_unsupported_protocol_is_skipped_with_a_reason(self):
        registry.register("future_protocol", GENERIC_PREFIX, SYNTHETIC_MODULE, "1", [], "Future")
        path = Path(registry.load_all()["future_protocol"]["schema_path"])
        schema = json.loads(path.read_text())
        schema["protocol"] = 99
        path.write_text(json.dumps(schema))
        schemas, problems = registry.load_schemas()
        self.assertNotIn("future_protocol", schemas)
        self.assertTrue(
            any(name == "future_protocol" and "protocol" in why for name, why in problems), problems
        )

    @unittest.skipUnless(Path("/proc/self").exists(), "needs /proc (Linux)")
    def test_6_worker_dies_when_the_host_dies(self):
        code = (
            "import sys, time; sys.path.insert(0, %r); import os; os.environ['LC_HOME'] = %r\n"
            "from labconstrictor_tools import client\n"
            "w = client.WorkerProcess('synthetic'); t = w.task('stubborn', {'seconds': 120})\n"
            "print(w.proc.pid, flush=True); time.sleep(600)\n" % (str(V3), os.environ["LC_HOME"])
        )
        host = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        worker_pid = int(host.stdout.readline())
        time.sleep(2)
        self.assertTrue(alive(worker_pid))
        host.send_signal(signal.SIGKILL)  # the host crashes mid-run
        host.wait()
        t0, gone = time.time(), False
        while time.time() - t0 < 20:
            if not alive(worker_pid):
                gone = True
                break
            time.sleep(0.5)
        REPORT["orphan_worker"] = {
            "worker_gone_after_host_crash": gone,
            "seconds_waited": round(time.time() - t0, 1),
        }
        if not gone:
            os.kill(worker_pid, signal.SIGKILL)
        self.assertTrue(gone, "worker kept running a 120 s tool after its host died")


if __name__ == "__main__":
    unittest.main(verbosity=2)
