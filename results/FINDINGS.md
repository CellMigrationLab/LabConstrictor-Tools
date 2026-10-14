# Findings of the one-off run (classified; nothing fixed until the owner reviews)

Classes: app bug, host bug, Tools bug, sandbox/runner bug, environment. Status: open until the owner decides.

## F-001 (Tools sandbox bug) `sandbox_checks.py cases` is not idempotent for apps whose COMPLETE case writes into the fixtures
* Where: tests/release_sandbox/sandbox_checks.py, function `cases`. It first runs `labconstrictor-tools test --cases cases.json` (the whole suite, which executes every case, including GuessTheCondition case 00 `create_demo_experiment` into `lc_tests/fixtures/results`), then runs each COMPLETE case again through the CLI.
* Evidence (GuessTheCondition 0.0.1, fresh fixtures, private copy of the checkout, no other process): `4_cases_suite PASS reports=22`, then `4_cli_case_00_create_demo_experiment_COMPLETE FAIL status=FAILED code=already_exists`. Run alone in a fresh copy, the same CLI call completes (COMPLETE, demo created).
* Effect: a correct app reports a failing case 00 and `6_runs_complete` FAIL. Would also fail in the GitHub release sandbox for this app.
* Needs: owner decision (regenerate the fixtures between the suite and the CLI phase, or give each phase its own copy).

## F-002 (Tools sandbox bug) the retention step repeats the first case 60 times, so it needs a repeatable first case
* Evidence: `6_runs_complete FAIL run 0 of create_demo_experiment ... already_exists`; the other retention ids (6a, 6b, 6d, 6e, 6f) were never produced and are NOT_RUN. GuessTheCondition's first case creates a folder that must not exist, so it cannot be repeated.
* Effect: the retention contract (markers, newest 20 results, 50 run records, prune) is unverified for Guess the Condition by the sandbox. It must be exercised through a repeatable tool (e.g. prepare_game) instead.
* Needs: owner decision (select the first repeatable COMPLETE case; add a `retention_case` hint to the case format, or exempt with a reason).

## Environment notes
* The user-level Jupyter kernelspec in this container (/root/.local/share/jupyter/kernels/python3) points to a stale interpreter; each installed app has its own kernelspec under <prefix>/share/jupyter. Notebook runs must pin the app's kernel.
* The first real installer run (Guess the Condition 0.0.1, Linux): 4.5 min, 1.2 GB; post-install passed `--app-manifest` to Tools; registered with hosts notebook, napari, fiji, qupath; `doctor` clean.

## F-003 (environment, not an app bug) retention check needs an exclusive LC_HOME
* `6b_results_keep_newest_20` asserts that the kept results are exactly the names of THIS run's last 20 results. In a shared registry (the one-off run installs several apps and runs agents in parallel) other tool runs interleave, so `kept=20` still reports FAIL (16 CellTracksColab results + 4 Guess the Condition results).
* Action taken in the runner: each sandbox family run registers the app into its own empty private LC_HOME (as a clean user would). Result of the rerun is in RESULTS.md.
* Note for the Tools sandbox: the check is only valid in an exclusive registry; that is true in CI (one app per runner), so no change is proposed.
* F-003 result: rerun of CellTracksColab 1.1.2 in a private LC_HOME: 31 PASS, 0 FAIL (registry hosts `notebook` as required, tool cases, retention 6a to 6f all pass). Confirms F-003 was the shared registry, not the app.
