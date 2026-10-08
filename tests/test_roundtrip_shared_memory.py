"""Shared memory is host-owned: a worker that read an image from it must leave the block (and the host's stderr view) alone."""

import os
import time
import unittest
from multiprocessing import shared_memory

import _paths  # noqa: F401  (must come first)
import numpy as np
import roundtrip_harness as harness
from roundtrip_known_failures import is_known

KEY = "lifecycle:shared_memory_survives_the_worker"


def wait_for_destruction(name, seconds=10.0):
    """True when the block is gone within `seconds` (the worker's resource tracker acts a moment after the worker is gone)."""
    end = time.time() + seconds
    while time.time() < end:
        try:
            block = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            return True
        block.close()
        time.sleep(0.2)
    return False


def shared_memory_problems():
    """Read an image from a host-owned block through a real worker, close the worker, and look at what is left."""
    session = harness.Session()
    problems = []
    try:
        array = np.arange(12, dtype=np.uint16).reshape(3, 4)
        descriptor = session._share(array)
        worker = harness.start_worker()
        try:
            task = worker.task("echo_image", {"image": descriptor}).wait(60)
            if task.status != "COMPLETE":
                return ["the task did not complete: %s" % task.error]
        finally:
            worker.close()
        destroyed = wait_for_destruction(descriptor["shm"]["name"])
        if destroyed:
            problems.append("the host's shared-memory block was destroyed when the worker exited")
        noise = "".join(worker.stderr)
        if "resource_tracker" in noise:
            problems.append(
                "the worker's stderr (shown to people in crash messages) holds: %s" % noise.strip()[:200]
            )
    finally:
        session.close()
    return problems


class SharedMemoryOwnership(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX shared memory is named, and tracked per process")
    def test_the_block_and_the_stderr_are_left_alone(self):
        if is_known(KEY):
            self.skipTest("known failure F13, watched by test_roundtrip_known_failures")
        self.assertEqual(shared_memory_problems(), [])


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
