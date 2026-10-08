"""Names that vulture reports at --min-confidence 80 although nothing is dead. One name per line, each with its reason (a line
without a reason is refused by tests/test_roundtrip_unused_code.py, and so is a name vulture no longer reports).

    vulture labconstrictor_tools tests/vulture_whitelist.py --min-confidence 80
"""

exc  # WorkerProcess.__exit__(self, *exc): the context-manager protocol hands over the exception triple; it is deliberately not used
