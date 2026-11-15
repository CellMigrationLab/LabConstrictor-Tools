# Audit tooling (`tests/audit/`)

Tools for a local audit of released apps on Linux (Xvfb): install an app, drive it through the hosts, its notebooks and the CLI, and write
one result matrix per family, host and app. None of it runs in CI and none of it is collected as a test (no `test_*.py` here); it is linted,
formatted and type-checked like the rest of `tests/`. The parts that need no installed app and no network are covered by `tests/test_audit_*.py`,
which CI does run.

| Path | What it is |
|---|---|
| `matrix.py` | the result matrix: one JSON file per family, host and app, rewritten atomically after every row; expected ids that never ran become `NOT_RUN` |
| `collect_results.py` | aggregator: `RESULTS.md` for matrices outside any round folder, one generated `alphaN/MATRICES.md` per round; rounds are never mixed |
| `run_sandbox_family.py`, `run_multi_family.py` | families `sandbox` (release-sandbox checks against one installed app, optionally in a private `LC_HOME`) and `multi` (several apps in one registry, CLI level) |
| `notebooks/` | family `nb`: runs every notebook an installed app packages with simulated clicks (`scripts/<app>/<notebook>.py`); see [notebooks/README.md](notebooks/README.md) |
| `synthetic/` | generators of input data with ground truth for the apps, and their checkers; see [synthetic/README.md](synthetic/README.md) |
| `run_fiji_audit.sh`, `run_napari_audit.sh`, `run_qupath_audit.sh`, `syn_napari.sh` | launchers of the host repositories' UI audits (under Xvfb) |
| `register_app.sh` | registers an installed app into a fresh private registry, as the installer's post-install does |
| `syn_to_matrix.py` | turns the synthetic checker's output into matrix rows |

Statuses of a matrix row: `PASS`, `FAIL`, `NOT_RUN` (expected, not executed: red), `HUMAN` (cannot be automated: listed for a person, never
green), `NOTE` (information, never green).

## Running a round

Every machine-specific path is an environment variable; a missing one is an error, never a guess. Keep each round's results in its own folder
`RESULTS_DIR/alphaN/`.

1. Install the app under test into its own prefix, and register it in a fresh registry:
   `register_app.sh NAME PREFIX SRC_CHECKOUT PRIVATE_LC_HOME`.
2. Run the families you need:
    * `python run_sandbox_family.py --app NAME --prefix PREFIX --src APP_SRC --tag TAG --results DIR --lc-home LC_HOME [--sections basic,hosts,cases,retention]`
    * `python run_multi_family.py --apps NAME:PREFIX:SRC [...] --results DIR --private-home EMPTY_DIR`
    * `python notebooks/nb_runner.py --app NAME --prefix PREFIX --src SRC --tag TAG --results DIR --lc-home LC_HOME`
      (timeouts `LC_NB_TOTAL_TIMEOUT`, `LC_NB_CELL_TIMEOUT`, `LC_NB_DOWNLOAD_CAP_MB`)
    * host UI audits, each `APP LC_HOME TESTS OUTDIR`:

      | Launcher | Required environment | Optional |
      |---|---|---|
      | `run_napari_audit.sh` | `LC_NAPARI_CHECKOUT`, `LC_AUDIT_PYTHON` | `LC_EXPECT_NAPARI` (`listed` or `hidden`) |
      | `run_fiji_audit.sh` (extra argument `script` or `jar`) | `LC_FIJI_CHECKOUT`, `LC_FIJI_HOME`, `LC_HOST_VERSION`, `LC_AUDIT_PYTHON`; `LC_FIJI_PLUGIN_DIR` (script mode) or `LC_FIJI_JAR` (jar mode) | `LC_EXPECT_FIJI` |
      | `run_qupath_audit.sh` | `LC_QUPATH_CHECKOUT`, `QUPATH`, `LC_RELEASE_DIR`, `LC_AUDIT_PYTHON` | `LC_EXPECT_QUPATH` |
      | `syn_napari.sh APP SYNDIR LC_HOME OUTDIR [file\|layer]` | `LC_NAPARI_CHECKOUT`, `LC_AUDIT_PYTHON` | `LC_EXPECT_NAPARI` |

    * synthetic data: the commands in [synthetic/README.md](synthetic/README.md), then `python syn_to_matrix.py APP HOST CHECK_OUTPUT_TXT OUTDIR [REPORTS_DIR]`.
3. `python collect_results.py RESULTS_DIR` writes the summary tables.
