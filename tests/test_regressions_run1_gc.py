"""Runs just before test_regressions_run2 (test files run in name order) and collects the garbage that earlier tests left behind.

test_regressions_run2 counts ResourceWarnings between creating a worker and its own gc.collect(), so it also sees unclosed pipes
of OTHER tests that happen to be collected inside that window. When that happens depends on the garbage collector's counters, which
move with every import (the round-trip tests import numpy, pandas and hypothesis at discovery). Collecting here, outside the window,
makes the older test independent of that timing. The one thing it can say about the garbage is that nothing was left uncollectable (`gc.garbage` stays empty).
"""

import gc
import unittest
import warnings


class CollectBeforeTheWorkerPipeTest(unittest.TestCase):
    def test_collect_what_earlier_tests_left_behind(self):
        with warnings.catch_warnings():
            warnings.simplefilter(
                "ignore", ResourceWarning
            )  # not this test's business; the owners of the garbage are named elsewhere
            for _ in range(3):
                gc.collect()
        self.assertEqual(
            gc.garbage, []
        )  # objects the collector found but could not free would be a leak of some test


if __name__ == "__main__":
    unittest.main()
