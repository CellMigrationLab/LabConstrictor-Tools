# Operations: install, shared/network installs, security, troubleshooting

## Install
* Each app environment needs `labconstrictor-tools` (standard library only, no dependencies).
* Napari (nothing is on PyPI yet): `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip https://github.com/CellMigrationLab/LabConstrictor-napari/archive/refs/heads/main.zip` in the napari environment (source archives: no `git` program needed; `git+https://github.com/...` works too if you have git). Plugins > LabConstrictor tools.
* Fiji (no release or update site yet): either copy `LabConstrictor_Tools.groovy` (keep the underscore: Fiji lists a script in its menus only when its name contains one) from the Fiji repository (`src/main/resources/org/cellmigrationlab/labconstrictor/`) to `Fiji.app/scripts/Plugins/LabConstrictor/` (no build), or build the jar with `mvn package` and copy `target/labconstrictor-fiji-<version>.jar` to `Fiji.app/plugins/`, then restart: Plugins > LabConstrictor > LabConstrictor Tools... (jar) or Plugins > LabConstrictor > LabConstrictor Tools (script). The macro recorder needs the jar.
* Fiji and Napari never import an app's packages, so apps with conflicting dependencies can coexist.

## Releases and tags
The version lives in one place, `labconstrictor_tools/_version.py` (`__version__`); `pyproject.toml` and `labconstrictor_tools.__version__` both read it. `describe`, the registry and `doctor` report it as `tools_version` ([PROTOCOL.md](PROTOCOL.md#tools-version-and-features)).
* **Tag names:** `vX.Y.Z` for a release (`v0.2.0`), `vX.Y.Z-rc.N` for a pre-release (`v0.2.0-rc.1`), always on a commit of `main`. The tag has a leading `v`; the Python version in `_version.py` has not, and spells the pre-release PEP 440 style: tag `v0.2.0-rc.1` <-> `__version__ = "0.2.0rc1"`. Beta or alpha work uses `-beta.N` / `-alpha.N` (`0.2.0b1`, `0.2.0a1`) and is never pinned by an app.
* **Who tags:** the maintainer tags. Claude and CI never create tags or GitHub releases; a pull request that wants a release says so in its description and the maintainer tags after merging.
* **Procedure:** (1) CI is green on `main` on all three systems (and the nightly of the same commit); (2) a pull request sets `_version.py` to the new number and moves the "unreleased" notes of the ledger; merge it; (3) `git tag -a v0.2.0-rc.1 -m "Tools 0.2.0 release candidate 1" <merge commit>` and `git push origin v0.2.0-rc.1`; (4) on GitHub create the release from the tag (tick "pre-release" for `-rc.N`); (5) check `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.2.0-rc.1.zip` in a clean environment and `labconstrictor-tools --help`; (6) a new `main` commit after the tag keeps the tag's version until the next bump PR (so `main` between releases reports the last number: `doctor` shows what is installed, not where it came from).
* **Moving a tag is forbidden.** A broken release is fixed with the next number (`-rc.2`, `0.2.1`); installers pin tags, and a moved tag would change what a pinned installer installs.
* **The CI `compat` job** installs the newest tag (if one exists) and reads schemas across versions, see [TESTING.md](TESTING.md).

### Pinning Tools in app installers
An app installer must install a **tagged** Tools, never `main`: `main` moves, so two installs of the same app a week apart would run different workers, and a breaking change (for example issue #51) would reach installed apps without any release. The installer already reads the source from `LC_TOOLS_SPEC` and installs it with one `pip install` ([LABCONSTRICTOR_INTEGRATION.md](LABCONSTRICTOR_INTEGRATION.md)); pinning only changes the default:
* Default value: `https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.2.0.zip` (a release) or `.../refs/tags/v0.2.0-rc.1.zip` while only a release candidate exists. Never `refs/heads/main.zip`, never a bare branch or a commit that is not a tag. An app moves to a newer Tools by a pull request that changes this one string (and runs its `lc_tests`), not by anybody tagging.
* `LC_TOOLS_SPEC` stays the override (a local wheel for tests, a mirror, a branch for a developer).
* After installing, the hook may record the version by running `labconstrictor-tools doctor`, which shows `Tools <version>`; a test of the installer checks that the version equals the pinned tag.
* A tag is only pinned after the maintainer created it ([Releases and tags](#releases-and-tags)); an installer that pins a tag that does not exist fails at `pip install`, which the hook already reports without stopping the rest of the install.

Files that must change in the apps (the template-repository change is a later task; the lists come from a search for `refs/heads/main.zip` and `LC_TOOLS_SPEC`; search again before editing, other branches may carry more):

| Repository | File and line (at the time of writing) | Change |
|---|---|---|
| `labconstrictor-vlab4mic` | `app/bash_bat_scripts/post_install.sh` (the `pip install "${LC_TOOLS_SPEC:-...refs/heads/main.zip}"` line, about 88) | the default URL, to the tag |
| `labconstrictor-vlab4mic` | `app/bash_bat_scripts/post_install.bat` (`IF NOT DEFINED LC_TOOLS_SPEC SET "LC_TOOLS_SPEC=..."`, about 111) | the same URL |
| `guessthecondition` | `app/bash_bat_scripts/post_install.sh` (about 88) and `post_install.bat` (about 111) | the same |
| `labconstrictor-playground` | `app/bash_bat_scripts/post_install.sh` (about 98) and `post_install.bat` (about 120) | the same |
| `labconstrictor-playground` | `notebooks/LabConstrictorPlayground/LabConstrictorPlayground.ipynb` (the `!pip install -q ...main.zip` cell) | the same URL |
| `NucleiSky`, `CellTracksColab` | `app/bash_bat_scripts/post_install.sh` and `.bat` once their bridge PRs are merged (not present on `main` of the local clones when this was written) | the same |
| `LabConstrictor` (template) | `app/bash_bat_scripts/post_install.sh` and `.bat` of the template, so new apps start pinned | the same (later task) |
| docs and READMEs that tell people to `pip install` Tools | `LabConstrictor-Tools/README.md` (about line 35), `LabConstrictor-napari/README.md` (about 13), `labconstrictor-vlab4mic/README.md` (about 56), `docs/OPERATIONS.md` Install, above | say `refs/tags/<tag>.zip` (or keep `main` and label it "development version") |

## Many apps, many users, network shares
* Any number of apps can be registered; hosts list them all. Same name registered twice: the higher-priority directory wins
  (the per-user entry overrides a shared one); two versions of one app side by side are not supported.
* An administrator can publish apps for everybody: `labconstrictor-tools register --dir <shared folder> ...` and users add the folder to
  `LC_APPS_PATH` (or use the system directory). Entries whose interpreter does not exist on a user's machine are reported as
  "not available on this machine" instead of disappearing silently (roaming profiles).
* An app on a network share works if its Python can be started locally from that path; temporary files stay local; the app folder is
  never written to by the runtime. Tested: a read-only install at a different path than where it was created. **Not tested:**
  UNC paths, latency (first imports of torch/scipy over a network can take minutes), antivirus/AppLocker, many users on one share.
* Remote execution (app on a server, host elsewhere) is not supported: the design assumes local process launch and shared files.

## Security model
* The worker never runs host-supplied code: only tools declared by the app's own module can be started.
* Tools themselves are ordinary Python and can read/write any file the user can: **installing an app means trusting it**, exactly as
  running its notebook does. There is no sandbox.
* A registry entry makes hosts start a program. Entries must live in a directory only the user can write (checked on POSIX), the
  interpreter must be inside the entry's install prefix, and system-wide directories must be admin-controlled. Treat write access to
  these directories like write access to the user's startup items.
* Pin `labconstrictor-tools` in app requirements (with hashes if you can); it is the only code every app shares.

## Troubleshooting
* `labconstrictor-tools doctor` checks every entry (interpreter, schema, protocol, staleness) and prints what to fix.
* Stale tool list after an app update: run `labconstrictor-tools register ...` again (the installer does this).
* `labconstrictor-tools run` without `--out` writes its results to `<LC_HOME>/results/<time>_<app>_<tool>` (the newest 20 finished ones are kept by `labconstrictor-tools prune`, which the hosts start after a run; Napari and Fiji use their own temporary folders and remove them). `prune` removes only folders that carry LabConstrictor's own marker files (`.lc-owner.json` and `.lc-done.json`): a folder you made yourself, or one from an older version without markers, is never touched. Look first with `labconstrictor-tools prune --dry-run`; the rules are in [PROTOCOL.md](PROTOCOL.md#result-folders-and-run-records-retention).
* Every run writes `<LC_HOME>/runs/<time>_<app>_<tool>/run.json` (parameters as file paths and values, never pixel data; status,
  error, traceback, interpreter, worker output). Napari's *Details...* button shows it; attach it to bug reports. The newest 50 finished records are kept (`prune`, same rules).
* First run slow? Imports dominate (a repeat run in a kept worker is ~10x faster). Napari keeps the worker for 10 minutes by default.
* Tool hangs on Windows? Please report with the run record; two such hangs (numpy/scipy imports vs a pending stdin read) were found
  and fixed during development.


## When something goes wrong: logs
Every front-end (command line, Napari, Fiji, notebooks) appends to ONE file, `<LC_HOME>/logs/labconstrictor.log`
(default `~/.labconstrictor/logs/`, rotated at 1 MB, five files kept). It records: session start with versions and interpreter,
every worker start (exact interpreter, module, PYTHONPATH), every task (inputs, outcome, timings), apps that were skipped and why,
and for failures the tool's traceback and the worker's own stderr. A worker that dies reports its exit code with a likely cause
(missing package, killed by the OS for memory, native crash) and its last output, in the error shown to the user.

    labconstrictor-tools logs -n 100          # the tail
    labconstrictor-tools logs --path          # where the file is
    labconstrictor-tools doctor               # state of the installation
    labconstrictor-tools support-bundle       # zip: logs, registered apps, last 10 run records, versions -> attach to the bug report

Napari: after a failure the status line says so and **Details...** shows the error, traceback, worker output and the log tail.
Fiji: the error dialog shows the worker's last lines and the log location; unexpected script errors are logged with their stack trace.
Each run also has `<LC_HOME>/runs/<time>_<app>_<tool>/run.json`.

## Fallbacks (intended)
Places where the code deliberately carries on with a substitute instead of failing. Each one writes one line to the log when it happens
(see "When something goes wrong: logs"); none of them hides a failure the person could act on.

| Where | What happens | What the person sees |
|---|---|---|
| `log.version()` (session start line, `doctor`, support bundle) | `labconstrictor-tools` is not installed as a package (a source checkout): the version is reported as `unknown (checkout)` | That text instead of a number; one info line in the log |
| `diagnostics.probe_worker()` | Same situation: the package row says `running from a source folder` | That text in the "Check this installation" table; one info line in the log |
| `diagnostics.probe_worker()` (numpy, pandas, scipy, tifffile, matplotlib) | A library that is not installed is left out of the table | Its row is absent; a debug line in the log |
| `diagnostics._ram_gb()` | `os.sysconf` has no memory value (Windows): the Windows memory API is used instead; if that also fails the memory row is omitted | The memory row, or no memory row plus a warning in the log |
| `cli` environment report (`support-bundle`) | An app's interpreter cannot be run for `-VV`: its line says `cannot run: ...` and the bundle is still written | That line in the bundle; a warning in the log |
| `log.tail()` (`logs`, Details windows) | The log file does not exist or cannot be read: an empty tail | Nothing to show; a debug line explaining why |

## Known limits (testing phase)
* Verified on Linux with real NucleiSky and CellTracksColab installers, in Napari and Fiji (an earlier VLab4Mic check is not repeated here).
  Windows only under Wine (real Windows installer, host and worker both Windows processes); the `.bat` install hooks have never run on real
  Windows; macOS, UNC/NFS shares and multi-user "all users" installs are untested. People can help with these: docs/HUMAN_TEST_PROTOCOL.md.
* The worker reads image files whole (no lazy/chunked reading); TIFF always, other formats only when the app has `imageio`.
* No sandbox: a tool runs with the user's rights, like any app code. The worker only executes tools declared by the registered module.
* A protocol change is a major version; hosts say so in the UI when an app speaks a newer protocol than they do.
* A tool must stop the threads it starts before it returns: a leftover thread that calls `progress()` while the NEXT task runs is reported on that next task (after its own task ends the hooks do nothing).
* Logs are one shared rotating file; concurrent writers (Napari, Fiji, CLI) do not lock it.
* A worker is started with `PYTHONSAFEPATH=1` (Python 3.11+) so that the directory the host was started from is not on the tool's import path; on older Pythons a stray `pandas.py` there could shadow a real package.
