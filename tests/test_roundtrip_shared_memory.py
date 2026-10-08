"""Shared memory is host-owned: a worker that read an image from it must leave the block (and the host's stderr view) alone."""

import os
import time
import unittest
from multiprocessing import shared_memory

import _paths  # noqa: F401  (must come first)
import numpy as np
import roundtrip_harness as harness


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


def wait_for(condition, seconds=10.0):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.1)
    return bool(condition())


def shared_memory_problems():
    """Read an image from a host-owned block through a real worker, let the worker EXIT BY ITSELF (the host closes its end of the
    pipe), and look at what is left.

    The worker must end on its own, not through WorkerProcess.close(): close() kills the worker's whole process group after a
    moment, and that can kill Python's resource-tracker process (a child of the worker) before it has acted, which hides the
    defect in a race (seen on CI: the same check passed on a loaded machine and failed on an idle one)."""
    session = harness.Session()
    problems = []
    worker = None
    try:
        array = np.arange(12, dtype=np.uint16).reshape(3, 4)
        descriptor = session._share(array)
        worker = harness.start_worker()
        task = worker.task("echo_image", {"image": descriptor}).wait(60)
        if task.status != "COMPLETE":
            return ["the task did not complete: %s" % task.error]
        worker.proc.stdin.close()  # the host is done: the worker leaves by itself
        worker.proc.wait(60)
        name = descriptor["shm"]["name"]
        destroyed = wait_for_destruction(name, 15.0)
        if destroyed:
            problems.append("the host's shared-memory block was destroyed when the worker exited")
            if wait_for(lambda: "resource_tracker" in "".join(worker.stderr), 15.0):
                noise = "".join(worker.stderr)
                problems.append(
                    "the worker's stderr (shown to people in crash messages) holds: %s" % noise.strip()[:200]
                )
    finally:
        if worker is not None:
            worker.close()
        session.close()
    return problems


class SharedMemoryOwnership(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX shared memory is named, and tracked per process")
    def test_the_block_and_the_stderr_are_left_alone(self):
        self.assertEqual(shared_memory_problems(), [])


def tearDownModule():
    """Release what this module's tests left to the garbage collector now, so that a ResourceWarning for an unclosed pipe is
    raised here and not in whichever test happens to run next (some older tests count ResourceWarnings)."""
    import gc

    gc.collect()


if __name__ == "__main__":
    unittest.main()
