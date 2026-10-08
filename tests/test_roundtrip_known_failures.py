"""The list of known failures cannot rot: every listed id must still fail, every finding must have entries, every entry
must name a test that exists. When a fix PR makes an entry pass, this file fails until the entry is deleted.
"""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor

import _paths  # noqa: F401  (must come first)
import roundtrip_cases as rc
import roundtrip_harness as harness
from roundtrip_known_failures import FINDINGS, KNOWN, is_known


def matrix_keys():
    return sorted(k for k in KNOWN if k.split(":")[0] in harness.TRANSPORTS and is_known(k))


class KnownFailuresDoNotRot(unittest.TestCase):
    def test_findings_are_complete_and_used(self):
        for name, finding in FINDINGS.items():
            with self.subTest(name):
                for field in ("title", "repro", "expected", "observed"):
                    self.assertTrue(getattr(finding, field).strip(), field)
                self.assertTrue(
                    [k for k, f in KNOWN.items() if f == name], "a finding without entries: delete it"
                )
        self.assertEqual(sorted(set(KNOWN.values()) - set(FINDINGS)), [])

    def test_matrix_entries_name_cases_that_exist(self):
        by_id = {c.id: c for c in rc.all_cases()}
        for key in KNOWN:
            transport, _, case_id = key.partition(":")
            if transport not in harness.TRANSPORTS:
                continue
            with self.subTest(key):
                self.assertIn(case_id, by_id)
                carried_by = "cli" if transport == "terminal" else transport
                self.assertIn(carried_by, by_id[case_id].paths)

    def test_matrix_entries_still_fail(self):
        session = harness.Session()
        try:
            by_id = {c.id: c for c in rc.all_cases()}
            keys = [k for k in matrix_keys() if k.split(":", 1)[1] in by_id]

            def attempt(key):
                transport, _, case_id = key.partition(":")
                try:
                    return harness.run_case(session, transport, by_id[case_id])
                except Exception as error:  # noqa: BLE001 - a run that raises is still a failure of that case
                    return ["raised %r" % error]

            slow = [k for k in keys if not k.startswith(("worker:", "notebook:"))]
            fast = [k for k in keys if k.startswith(("worker:", "notebook:"))]
            with ThreadPoolExecutor(max_workers=4) as pool:
                outcomes = dict(zip(slow, pool.map(attempt, slow)))
            outcomes.update({k: attempt(k) for k in fast})
        finally:
            session.close()
        for key, problems in outcomes.items():
            with self.subTest(key):
                self.assertTrue(
                    problems,
                    "%s now PASSES: delete it from roundtrip_known_failures.py (%s)" % (key, KNOWN[key]),
                )

    def test_property_entries_still_fail(self):
        names = [k.split(":", 1)[1] for k in KNOWN if k.startswith("property:") and is_known(k)]
        if not names:
            return
        import test_roundtrip_properties as properties

        for name in names:
            with self.subTest(name):
                self.assertIn(name, properties.PROPERTIES)
                try:
                    properties.PROPERTIES[name]()
                except (
                    Exception
                ):  # noqa: BLE001 - any failure of the property is the defect we are waiting to see fixed
                    continue
                self.fail("property %s now PASSES: delete it from roundtrip_known_failures.py" % name)

    def test_hint_entries_are_still_accepted(self):
        import test_roundtrip_hints as hints

        by_id = {c.id: c for c in hints.invalid_cells()}
        for key in KNOWN:
            if key.startswith("hint:") and is_known(key):
                with self.subTest(key):
                    self.assertIn(key.split(":", 1)[1], by_id)
                    self.assertIsNone(
                        hints.refused(by_id[key.split(":", 1)[1]]), "now REFUSED: delete the entry"
                    )

    def test_unit_test_entries_still_fail(self):
        import io

        import roundtrip_known_failures as module

        module.META = True
        try:
            for key in KNOWN:
                if key.startswith("test:") and is_known(key):
                    with self.subTest(key):
                        suite = unittest.defaultTestLoader.loadTestsFromName(key.split(":", 1)[1])
                        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
                        self.assertEqual(result.testsRun, 1)
                        self.assertFalse(
                            result.wasSuccessful(),
                            "%s now PASSES: delete it from roundtrip_known_failures.py" % key,
                        )
        finally:
            module.META = False

    def test_lifecycle_entries_still_fail(self):
        import test_roundtrip_failures as failures
        from test_roundtrip_shared_memory import shared_memory_problems

        checks = {
            "shared_memory_survives_the_worker": shared_memory_problems,
            "task_on_a_dead_worker": failures.task_on_dead_worker_problems,
            "children_die_when_the_host_goes_away": failures.children_problems,
            "progress_percent_is_rounded": failures.progress_problems,
        }
        listed = {k.split(":", 1)[1] for k in KNOWN if k.startswith("lifecycle:")}
        self.assertEqual(sorted(listed - set(checks)), [], "an entry without a check")
        for name, check in checks.items():
            if is_known("lifecycle:" + name):
                with self.subTest(name):
                    self.assertTrue(check(), "%s now PASSES: delete the entry" % name)

    def test_failure_entries_still_fail(self):
        import test_roundtrip_failures as failures

        for key in KNOWN:
            if key.startswith("failure:") and is_known(key):
                with self.subTest(key):
                    self.assertTrue(
                        failures.toolerror_problems(key.split(":", 1)[1]), "now PASSES: delete the entry"
                    )

    def test_windows_quoting_entries_still_fail(self):
        from test_roundtrip_command import TEXTS, parse_windows_command_line

        from labconstrictor_tools import command

        for key in KNOWN:
            if key.startswith("winquote:") and is_known(key):
                label = key.split(":", 1)[1]
                with self.subTest(key):
                    self.assertIn(label, TEXTS)
                    line = "prog " + command.quote(TEXTS[label], windows=True)
                    self.assertNotEqual(
                        parse_windows_command_line(line),
                        ["prog", TEXTS[label]],
                        "now passes: delete the entry",
                    )

    @unittest.skipUnless(os.name == "nt", "the real Windows process start")
    def test_windows_process_entries_still_fail(self):
        from test_roundtrip_command import TEXTS, windows_process_problems

        for key in KNOWN:
            if key.startswith("winproc:") and is_known(key):
                label = key.split(":", 1)[1]
                with self.subTest(key):
                    self.assertTrue(windows_process_problems(TEXTS[label]), "now passes: delete the entry")

    def test_the_skip_is_exactly_the_list(self):
        self.assertFalse(is_known("worker:echo_int/ok/0"))
        self.assertTrue(is_known("worker:echo_int/word"))
        if os.name in ("posix", "nt"):
            self.assertTrue(is_known("cli:echo_table/missing-file"))


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
