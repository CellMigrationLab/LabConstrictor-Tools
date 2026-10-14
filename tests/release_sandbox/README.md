# Release sandbox: which hosts must list which app

The workflow `.github/workflows/release_sandbox.yml` (dispatch only) installs a RELEASED app and checks it. Since the per-host
discovery rule ([PROTOCOL.md, "App hosts"](../../docs/PROTOCOL.md#app-hosts-which-host-lists-an-app)) it also asserts, for every app and
for each of Napari, Fiji and QuPath, that the host **lists** the app or **does not list** it, as the matrix says.

## The shared expectation: `expected_hosts.json`
One row per app (key = `name:` of its `construct.yaml`): `hosts` (what its `labconstrictor-app.yaml` must declare), `repo`, and
`tools_module` (`required`, or `optional` for an app that may ship no tools). A host in `hosts` must list the app, every other
host must not. `expected_hosts.py env --app-name NAME --repo OWNER/NAME [--override a,b]` turns the row into `EXPECT_HOSTS`,
`EXPECT_NAPARI`, `EXPECT_FIJI`, `EXPECT_QUPATH` (`listed` | `not_listed`) and `TOOLS_MODULE`; the workflow puts them in `$GITHUB_ENV`.
An app with no row (and no `expected_hosts` input) stops the run: the sandbox never assumes "listed everywhere". A new app
needs a row in the same PR that adds it to the matrix.

| App (construct.yaml name) | hosts | Napari | Fiji | QuPath | tools module |
|---|---|---|---|---|---|
| LabConstrictorPlayground, NucleiSky, GuessTheCondition | notebook, napari, fiji, qupath | listed | listed | listed | required |
| VLab4Mic | notebook, napari, fiji | listed | listed | **not listed** | required |
| CellTracksColab | notebook | **not listed** | **not listed** | **not listed** | optional |

`tests/test_release_sandbox_hosts.py` keeps this file equal to the matrix, to the reference function and to the vectors of
`conformance.json`.

## Inputs (added or changed)
| Input | Meaning |
|---|---|
| `expected_hosts` | optional override of the row, e.g. `notebook,fiji` (for an app that has no row yet) |
| `hosts_napari`, `hosts_fiji`, `hosts_qupath` | `auto` (default): run the host check and assert listed or not_listed from the expectation; `skip`: do not run it. They replace the old boolean `hosts_napari` (default true, always "listed") and `hosts_qupath` (only with `playground_extras`) |
| `playground_extras` | unchanged in meaning, but only the Playground's own tool runs and failure paths and its Fiji and QuPath tool cases: the listing checks of Fiji and QuPath now run for every app |

## Checks (every line is `CHECK <id> PASS|FAIL <detail>`; `NOTE` lines say what does not apply and why)
| Id | Who | Meaning |
|---|---|---|
| `hosts_1_registry_entry_declares_the_hosts` | `hosts_check.py` | the registry entry written by the installer has exactly the expected `hosts`. Red when the installer passes none (an older installer: the entry has no `hosts`, so every host would list the app) |
| `hosts_2_reference_function_matches_the_matrix` | `hosts_check.py` | `app_hosts.listed_for(entry, host)` gives the expected answer for napari, fiji and qupath |
| `hosts_3_list_shows_the_declaration` | `hosts_check.py` | `labconstrictor-tools list` prints `hosts: ...` for the app |
| `napari_lists_the_app` / `napari_does_not_list_the_app` | `napari_check.py` | the Napari app dropdown contains (or lacks) the app |
| `napari_logs_why_it_skipped_the_app` | `napari_check.py` | for a registered, not listed app: the exact skip sentence is in `<LC_HOME>/logs/labconstrictor.log` |
| `fiji_*`, `qupath_*` | the host drivers below | see the contract |
| `tools_module_absent_as_declared` | workflow | the app has no `*_lc_tools` module and its row says `optional`: stated, and the tool, cases and retention checks do not run (`HAS_TOOLS=false`); `1b_app_without_tools_registered_nothing` and `hosts_1_app_without_tools_registers_nothing` then assert that nothing was registered |

An app without a tools module whose row says `required` stops the run. CellTracksColab is "no tools: hidden everywhere, notebook
run only": if its installer registers a module, the registry entry must say `hosts: [notebook]` (hidden in all three hosts) and
the command-line cases still run, because `run` is never filtered; if it registers nothing, the sandbox checks that nothing is
listed anywhere.

## Driver contract for the host repositories (Fiji and QuPath have their drivers on `main`; Napari is `napari_check.py`)
The workflow clones the host repository at `fiji_ref` / `qupath_ref` (Linux, Xvfb), installs the Tools tag `tools_pin`, and runs a
driver with these environment variables, in a registry (`LC_HOME`) that holds the installed app:

| Variable | Value |
|---|---|
| `LC_HOME` | the scratch registry with the installed app's entry (none for an app that ships no tools) |
| `LC_EXPECT_APP` | the registry name of the app |
| `LC_EXPECT_LISTED` | `listed` or `not_listed`: what this host must do |
| `LC_EXPECT_SENTENCE` | the exact sentence from `hosts_check.py sentence` (`app_hosts.listed_for`): non-empty when the app is registered and not listed; the host must have written it to the Tools log (`<LC_HOME>/logs/labconstrictor.log`) |

| Host | Driver (path in the host repository) | Started as |
|---|---|---|
| Fiji | `tests/sandbox_listing.py` | `python tests/sandbox_listing.py` under Xvfb with `LC_FIJI_HOME` set, in the venv that has the pinned Tools |
| QuPath | `tests/gui_test_listing_body.groovy` | `tests/run_gui_ci.sh gui_test_listing_body.groovy`; the script must pass the four variables on to QuPath |

The driver prints exactly one line per run and exits non-zero on FAIL:
* `CHECK fiji_lists_the_app PASS|FAIL <detail>` (Fiji) / `CHECK qupath_lists_the_app ...` (QuPath) when `LC_EXPECT_LISTED=listed`: the app is offered with every tool of its schema.
* `CHECK fiji_does_not_list_the_app ...` / `CHECK qupath_does_not_list_the_app ...` when `not_listed`: the app is NOT offered, and for a registered app the skip sentence is in the Tools log; for an app with no registry entry the driver prints `NOTE <host>_no_registry_entry` as well.

For a ref of a host repository that lacks its driver the workflow prints `CHECK fiji_listing_driver_present FAIL` / `CHECK qupath_listing_body_present FAIL`
(never a silent skip). The Playground's own Fiji cases (`fiji_cases/`) and QuPath bodies still run with `playground_extras`.
