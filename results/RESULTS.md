# Results of the one-off test run

## CellTracksColab

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 31 | 0 | 0 | 0 | 0 | 2026-10-14T17:57:48 |

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 5 | 3 | 21 | 0 | 3 | 2026-10-14T18:15:50 |
| sandbox | cli | 37 | 2 | 5 | 0 | 1 | 2026-10-14T17:58:52 |

### GuessTheCondition: FAIL (5)

* `nb_GuessTheCondition_Welcome_worker` (nb/notebook) the worker crashed with exit 1: nel_run.py", line 163 |     emit.row("net_%d" % number, "NOTE", "%s %s -> %s (size %s bytes)" % (event["method"], event["url"], event.get("status", "FAILED: " + str(event.get("error"))), event.get("size", "n/a"))) |     ^^^^ | IndentationError: expected an indented block after 'for' statement on line 162 | 
* `nb_GuessTheCondition_GuessTheCondition_worker` (nb/notebook) the worker crashed with exit 1: nel_run.py", line 163 |     emit.row("net_%d" % number, "NOTE", "%s %s -> %s (size %s bytes)" % (event["method"], event["url"], event.get("status", "FAILED: " + str(event.get("error"))), event.get("size", "n/a"))) |     ^^^^ | IndentationError: expected an indented block after 'for' statement on line 162 | 
* `nb_GuessTheCondition_GuessTheCondition_API_Example_worker` (nb/notebook) the worker crashed with exit 1: nel_run.py", line 163 |     emit.row("net_%d" % number, "NOTE", "%s %s -> %s (size %s bytes)" % (event["method"], event["url"], event.get("status", "FAILED: " + str(event.get("error"))), event.get("size", "n/a"))) |     ^^^^ | IndentationError: expected an indented block after 'for' statement on line 162 | 
* `4_cli_case_00_create_demo_experiment_COMPLETE` (sandbox/cli) status=FAILED code=already_exists
* `6_runs_complete` (sandbox/cli) run 0 of create_demo_experiment: eriment/run.json", |   "error": "[already_exists] /home/user/apps/run_src/GuessTheCondition/lc_tests/fixtures/results/GuessTheCondition_demo already exists: choose another folder, or delete it.", |   "code": "already_exists", |   "log": "/home/user/apps/lc_sbx_GuessTheCondition/logs/labconstrictor.log" | } |

### GuessTheCondition: NOT_RUN (26)

* `nb_GuessTheCondition_Welcome_packaged` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_valid` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_imports` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_kernel` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_runs` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_oracle` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_Welcome_sideeffects` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_packaged` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_valid` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_imports` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_kernel` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_runs` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_oracle` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_sideeffects` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_packaged` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_valid` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_imports` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_kernel` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_runs` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_oracle` (nb/notebook) expected, never executed
* `nb_GuessTheCondition_GuessTheCondition_API_Example_sideeffects` (nb/notebook) expected, never executed
* `6a_markers_present` (sandbox/cli) expected, never executed
* `6b_results_keep_newest_20` (sandbox/cli) expected, never executed
* `6d_prune_dry_run_json` (sandbox/cli) expected, never executed
* `6e_foreign_folders_left_alone` (sandbox/cli) expected, never executed
* `6f_run_records_keep_50` (sandbox/cli) expected, never executed

## all

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| multi | cli | 11 | 0 | 0 | 0 | 0 | 2026-10-14T17:59:43 |

