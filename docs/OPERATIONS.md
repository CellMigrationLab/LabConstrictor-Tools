# Operations: install, shared/network installs, security, troubleshooting

## Install
* Each app environment needs `labconstrictor-tools` (standard library only, no dependencies).
* Napari (nothing is on PyPI yet): `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip https://github.com/CellMigrationLab/napari-labconstrictor/archive/refs/heads/main.zip` in the napari environment (source archives: no `git` program needed; `git+https://github.com/...` works too if you have git). Plugins > LabConstrictor tools.
* Fiji (no release or update site yet): either copy `LabConstrictor_Tools.groovy` (keep the underscore: Fiji lists a script in its menus only when its name contains one) from the Fiji repository (`src/main/resources/org/cellmigrationlab/labconstrictor/`) to `Fiji.app/scripts/Plugins/LabConstrictor/` (no build), or build the jar with `mvn package` and copy `target/labconstrictor-fiji-<version>.jar` to `Fiji.app/plugins/`, then restart: Plugins > LabConstrictor > LabConstrictor Tools... (jar) or Plugins > LabConstrictor > LabConstrictor Tools (script). The macro recorder needs the jar.
* Fiji and Napari never import an app's packages, so apps with conflicting dependencies can coexist.

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
* `labconstrictor-tools run` without `--out` writes its results to `<LC_HOME>/results/<time>_<app>_<tool>` (the newest 20 are kept; Napari and Fiji use their own temporary folders and remove them).
* Every run writes `<LC_HOME>/runs/<time>_<app>_<tool>/run.json` (parameters as file paths and values, never pixel data; status,
  error, traceback, interpreter, worker output). Napari's *Details...* button shows it; attach it to bug reports. The newest 50 are kept.
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
