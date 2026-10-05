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
| test_logging | failures are explained and logged; `support-bundle` |
| windows/test_windows.py | the same layer on Windows: `python tests/windows/test_windows.py` (also run under Wine via run_suite.sh) |

Real apps are tested in the apps' own repositories (`lc_tests/`), with `labconstrictor-tools test`.
