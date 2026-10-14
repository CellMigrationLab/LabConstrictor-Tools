# Results of the one-off test run

## CellTracksColab

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| sandbox | cli | 25 | 0 | 0 | 0 | 0 | NOT FINISHED |

## GuessTheCondition

| family | host | PASS | FAIL | NOT_RUN | HUMAN | NOTE | finished |
|---|---|---|---|---|---|---|---|
| nb | notebook | 46 | 0 | 0 | 0 | 6 | 2026-10-14T17:48:59 |
| sandbox | cli | 36 | 2 | 5 | 0 | 1 | 2026-10-14T17:47:48 |

### GuessTheCondition: FAIL (2)

* `4_cli_case_00_create_demo_experiment_COMPLETE` (sandbox/cli) status=FAILED code=already_exists
* `6_runs_complete` (sandbox/cli) run 0 of create_demo_experiment: n_create_demo_experiment/run.json", |   "error": "[already_exists] /home/user/apps/run_src/GuessTheCondition/lc_tests/fixtures/results/GuessTheCondition_demo already exists: choose another folder, or delete it.", |   "code": "already_exists", |   "log": "/home/user/apps/lc_home/logs/labconstrictor.log" | } |

### GuessTheCondition: NOT_RUN (5)

* `6a_markers_present` (sandbox/cli) expected, never executed
* `6b_results_keep_newest_20` (sandbox/cli) expected, never executed
* `6d_prune_dry_run_json` (sandbox/cli) expected, never executed
* `6e_foreign_folders_left_alone` (sandbox/cli) expected, never executed
* `6f_run_records_keep_50` (sandbox/cli) expected, never executed

