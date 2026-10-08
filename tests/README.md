# Tests

Each `test_*.py` is a plain script/unittest: `cd tests && python test_introspection.py`. They use a private temporary registry
(`LC_HOME`), never `~/.labconstrictor`, and register the example app `labconstrictor_tools.examples.synthetic` against the
interpreter that runs them (needs `pip install -e ".[test]"`).

| Suite | What it proves |
|---|---|
| test_introspection | type hints -> schema, declaration errors, determinism |
| test_generic_integration | worker protocol end to end: all types, progress, cancel, kill, cleanup, shared memory |
| test_cli_and_registry | CLI, registry search path, trust checks, run records, doctor |
| test_environments | concurrency, duplicate/broken/future-protocol apps, orphaned workers (optional read-only prefix: `LC_TEST_RO_PREFIX`) |
| test_notebook_form | the ipywidgets form |
| test_author_tools | `%%lc_tool`, `export-notebook`, `labconstrictor-tools test` |
| test_regressions_run2 | worker pipes closed, `--pythonpath` precedence, damaged TIFF, nullable/folder/group/advanced/enabled_when in the schema, host cwd not on the worker's path, root prefix refused, CLI results folder pruned |
| test_hardening | NaN/inf rejected, strict-JSON results, registry priority and trust, unsafe app names, skipped-app explanations, message after a forced kill on Cancel |
| test_cli_hardening | support bundle never follows symlinks, doctor survives broken apps, unique results folders, duplicate arguments |
| test_convert_hardening | dtype narrowing never changes values, invalid defaults refused, strict booleans/choices, enums restored, empty images refused |
| test_worker_protocol | the worker fed raw hostile requests: bad ids/inputs, duplicates, sys.exit, unserialisable results, oversized lines |
| test_client_hardening | host client: callback errors, cancel escalation, task cleanup, shutdown, concurrent sends, record pruning |
| test_testing_hardening | the author test harness: unknown expectation keys refused, 3x3 matrices, directories are not files, text inputs never become paths, describe output stays JSON, cancel check verdict |
| test_logging | failures are explained and logged; `support-bundle` |
| test_roundtrip_* | the generated round-trip matrix, properties, geometry, hints, failure injection, known failures, sabotage: see [../docs/TESTING.md](../docs/TESTING.md) |
| windows/test_windows.py | the same layer on Windows: `python tests/windows/test_windows.py` (also run under Wine via run_suite.sh) |

Run everything: `cd tests && python -m unittest discover -p "test_*.py"` (about 80 s; 78 tests, 2 skipped: the read-only-prefix test needs `LC_TEST_RO_PREFIX`, the foreign-owned-entry test needs root).

Real apps are tested in the apps' own repositories (`lc_tests/`), with `labconstrictor-tools test`. A checklist for people testing on a real computer: [../docs/HUMAN_TEST_PROTOCOL.md](../docs/HUMAN_TEST_PROTOCOL.md).
