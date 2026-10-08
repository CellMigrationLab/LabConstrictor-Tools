"""The generated round-trip matrix through every transport (worker protocol, command line, copied snippet, copied terminal
line, notebook form). Values that a transport cannot carry are not sent on it; the cases in roundtrip_known_failures.py are
skipped here and watched by test_roundtrip_known_failures.py."""

import os
import traceback
import unittest
from concurrent.futures import ThreadPoolExecutor

import _paths  # noqa: F401  (must come first)
import roundtrip_cases as rc
import roundtrip_harness as harness
from roundtrip_known_failures import is_known

PARALLEL = 4  # subprocess transports run this many cases at a time


def key(transport, case):
    return "%s:%s" % (transport, case.id)


class Matrix(unittest.TestCase):
    session = None

    @classmethod
    def setUpClass(cls):
        cls.session = harness.Session()

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def attempt(self, transport, case):
        try:
            return harness.run_case(self.session, transport, case)
        except (
            Exception
        ):  # noqa: BLE001 - a harness or transport error is a failure of that case, reported with its traceback
            return ["the run itself raised:\n" + traceback.format_exc()[-1500:]]

    def walk(self, transport, parallel=1):
        todo = [c for c in rc.selected(transport) if not is_known(key(transport, c))]
        self.assertGreater(
            len(todo), 0 if os.environ.get("LC_ROUNDTRIP_FILTER") else 10
        )  # a slice must not be empty
        if parallel > 1:
            with ThreadPoolExecutor(max_workers=parallel) as pool:
                outcomes = list(pool.map(lambda c: self.attempt(transport, c), todo))
        else:
            outcomes = [self.attempt(transport, c) for c in todo]
        for case, problems in zip(todo, outcomes):
            with self.subTest(key(transport, case)):
                self.assertEqual(problems, [])

    def test_worker_protocol(self):
        self.walk("worker")

    def test_command_line(self):
        self.walk("cli", PARALLEL)

    def test_copied_python_snippet(self):
        self.walk("snippet", PARALLEL)

    def test_copied_terminal_line(self):
        self.walk("terminal", PARALLEL)

    def test_notebook_form(self):
        self.walk("notebook")


if __name__ == "__main__":
    unittest.main()
