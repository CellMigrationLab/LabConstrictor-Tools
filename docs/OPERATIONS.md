# Operations: shared installs, security, troubleshooting

How a person installs an app and each plugin is in [Install an app](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/install/) and the [napari](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/napari/), [Fiji](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/fiji/) and [QuPath](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/qupath/) guides. What Tools needs from an installed app, and how to install it by hand, is in [INSTALL.md](INSTALL.md). In short: each app environment has its own `labconstrictor-tools`, installed by the app's installer from a tag, and the plugins need 0.3.0a1 or newer. Hosts never import an app's packages, so apps with conflicting dependencies can live side by side.

## When something goes wrong: logs

Every front-end (command line, napari, Fiji, QuPath, notebooks) appends to one file, `<LC_HOME>/logs/labconstrictor.log` (default `~/.labconstrictor/logs/`, rotated at 1 MB, five old files kept). It records the session start with versions and interpreter, every worker start (interpreter, module, `PYTHONPATH`), every task (inputs, outcome, timings), apps that were skipped and why, and for failures the tool's traceback and the worker's stderr. When a worker dies, the error shown to the person gives its exit code, a likely cause (a missing package, killed by the system for memory, a native crash) and its last output.

    labconstrictor-tools logs -n 100          # the end of the log
    labconstrictor-tools logs --path          # where the file is
    labconstrictor-tools doctor               # the state of the installation
    labconstrictor-tools support-bundle       # a zip of logs, registered apps, the last 10 run records and versions, to attach to a bug report

After a failure, napari and QuPath have a **Details** button with the error, the traceback, the worker's output and the end of the log; Fiji's error dialog shows the worker's last lines and where the log is.

Every run also writes a record, `<LC_HOME>/runs/<time>_<app>_<tool>/run.json`: the parameters (file paths and values, never pixel data), the status, the error and traceback, the interpreter and the worker's output. Attach it to bug reports.

## Troubleshooting

* **Something is wrong with an app.** `labconstrictor-tools doctor` checks every registered app (interpreter, schema, protocol, staleness) and says what to fix.
* **The tool list is out of date after an app update.** Run `labconstrictor-tools register ...` again; the app's installer normally does this.
* **Where results go, and cleanup.** `labconstrictor-tools run` without `--out` writes to a new folder under `<LC_HOME>/results/`. `labconstrictor-tools prune` keeps the newest 20 finished result folders and the newest 50 run records; hosts start it after each run. It removes only folders that carry LabConstrictor's marker files (`.lc-owner.json` and `.lc-done.json`): a folder you made, or one from an older version, is never touched. Look first with `labconstrictor-tools prune --dry-run`. The rules are in [PROTOCOL.md](PROTOCOL.md#result-folders-and-run-records-retention).
* **Writing run records from a Python host.** Use `runs.build_record`, `runs.record_json` and `runs.done_status` (Tools 0.3.0a1 and later), then start `prune`; a host never deletes folders itself ([PROTOCOL.md](PROTOCOL.md#result-folders-and-run-records-retention)). There is no feature id for them: require Tools 0.3.0a1.
* **A file stays locked on Windows.** Tools memory-maps uncompressed, contiguous TIFF files of 8 MiB or more. A tool that keeps a reference to its input (a global, a stored exception, a thread that outlives the run) keeps the file locked until the worker ends, and the host cannot delete or overwrite it meanwhile. Set `LC_TIFF_MEMMAP=0` to read files the plain way. Linux and macOS are not affected.
* **A copied terminal line does not start on Windows.** Windows limits a command line to about 32,000 characters. Run such a long text parameter from the plugin's form or the copied Python snippet.
* **The first run is slow.** Imports dominate; a repeat run in a kept worker is about 10 times faster. napari keeps an idle worker for 10 minutes.
* **A tool hangs on Windows.** Please report it with the run record.

## Many apps, many users, network shares

* Any number of apps can be registered, and hosts list them all. When the same name is registered twice, the higher-priority directory wins (a per-user entry overrides a shared one). Two versions of one app side by side are not supported.
* An administrator can publish apps for everybody with `labconstrictor-tools register --dir <shared folder> ...`; users add the folder to `LC_APPS_PATH`, or the administrator uses the system directory ([PROTOCOL.md](PROTOCOL.md#registry)). An entry whose interpreter does not exist on a user's machine is reported as "not available on this machine" instead of disappearing (roaming profiles).
* An app on a network share works if its Python can be started from that path. Temporary files stay local, and the runtime never writes to the app folder. A read-only install at a different path from where it was created is tested. UNC paths, slow networks (the first import of torch or scipy over a network can take minutes), antivirus or AppLocker rules and many users on one share are not tested. The installers do not offer per-machine ("all users") installs, although `register --dir` and `LC_APPS_PATH` support them.
* Running the app on another computer than the host is not supported: the design assumes a local process and shared files.

## Security model

* The worker never runs code sent by a host: it starts only tools declared by the app's own module.
* Tools are ordinary Python and can read and write any file the user can. **Installing an app means trusting it**, exactly as running its notebook does. There is no sandbox.
* A registry entry makes hosts start a program. Entries must live in a directory only the user can write, the interpreter must be inside the entry's install prefix, and system-wide directories must be controlled by an administrator. These checks (owner, group- or world-writable files, interpreter inside the prefix, world-writable folders on the way) run **on Linux and macOS only**. On Windows a registry entry is trusted as found, because ownership and permission bits do not map to its access-control lists. Treat write access to these directories like write access to the user's startup items.
* `labconstrictor-tools` is the only code every app shares: installers pin it to a tag (below).

## Known limits

* The worker reads image files whole; there is no tile-by-tile reading. TIFF is always read; other formats only when the app has `imageio`.
* A protocol change is a new major version; hosts say so when an app speaks a newer protocol than they do.
* A tool must stop the threads it starts before it returns: a leftover thread that calls `progress()` while the next task runs is reported on that task.
* The log is one shared rotating file; napari, Fiji and the command line do not lock it while writing.
* A worker starts with `PYTHONSAFEPATH=1` (Python 3.11 and later), so the folder the host was started from is not on the tool's import path. On older Pythons a stray `pandas.py` there could shadow the real package.

## Deliberate fallbacks

In these places the code carries on with a substitute instead of failing. Each writes one line to the log when it happens; none hides a failure the person could act on.

| Where | What happens | What the person sees |
|---|---|---|
| `log.version()` (session start, `doctor`, support bundle) | `labconstrictor-tools` runs from a source checkout, not an installed package | `unknown (checkout)` instead of a version; an info line in the log |
| `diagnostics.probe_worker()` | the same situation | `running from a source folder` in the "Check this installation" table |
| `diagnostics.probe_worker()` (numpy, pandas, scipy, tifffile, matplotlib) | a library that is not installed is left out | its row is absent; a debug line in the log |
| `diagnostics._ram_gb()` | `os.sysconf` has no memory value (Windows): the Windows memory API is used; if that also fails, the row is omitted | the memory row, or none and a warning in the log |
| `support-bundle` environment report | an app's interpreter cannot run `-VV`: its line says `cannot run: ...` and the bundle is still written | that line in the bundle; a warning in the log |
| `convert._memmap_tiff` (a TIFF of 8 MiB or more) | the file cannot be memory-mapped (compressed, tiled, multi-series, OME or another special layout, big-endian, truncated, not contiguous, `LC_TIFF_MEMMAP=0`, or the mapping failed): it is read with `tifffile.imread`, same pixels, more memory and time | one warning line with the file name and the reason, in the log and on the worker's stderr |
| `Worker._orphan_exit` | the host is gone and a temporary folder could not be removed completely: the worker exits anyway | one warning line in the log file |
| `log.tail()` (`logs`, Details windows) | the log file does not exist or cannot be read | an empty tail; a debug line explaining why |

## Releases and tags

The version is written once, in `labconstrictor_tools/_version.py` (`__version__`); `pyproject.toml` and `labconstrictor_tools.__version__` read it. `describe`, the registry and `doctor` report it as `tools_version` ([PROTOCOL.md](PROTOCOL.md#tools-version-and-features)).

* **Tag names.** `vX.Y.Z` for a release (`v0.2.0`); `vX.Y.Z-rc.N`, `vX.Y.Z-alpha.N` or `vX.Y.Z-beta.N` for a pre-release; always on a commit of `main`. Tags are lightweight, as GitHub creates them from the Releases page. The Python version has no `v` and uses PEP 440 spelling: `-rc.N` is `rcN`, `-alpha.N` is `aN`, `-beta.N` is `bN`. So tag `v0.2.0-rc.1` is `__version__ = "0.2.0rc1"` and tag `v0.3.0-alpha.1` is `"0.3.0a1"`. Order: `0.2.0rc1 < 0.3.0a1 < 0.3.0`.
* **One number, one code.** A code change a host can observe gets a new version number in the same pull request, so that hosts can tell versions apart. Pre-releases count up towards the number they lead to (`v0.3.0-alpha.1`, `v0.3.0-alpha.2`, ...).
* **Who tags.** Only the maintainer. Claude and CI never create tags or GitHub releases; a pull request that wants a release says so, and the maintainer tags after merging.
* **Procedure.**
  1. CI is green on `main` on all three systems, and so is the nightly run of the same commit.
  2. A pull request sets `_version.py` to the new number and moves the "unreleased" notes of the regression ledger; merge it.
  3. On GitHub, create the release with the new tag name, targeting the merge commit on `main`. GitHub creates the tag. Tick "pre-release" for `-rc.N` and `-alpha.N`. The release notes go in the GitHub release.
  4. In a clean environment, check `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/<tag>.zip` and `labconstrictor-tools --help`.

  Commits on `main` after the tag keep reporting the tag's version until the next bump.
* **Fixed-name archive.** When a release is published, the workflow `release-archive` (`.github/workflows/release_archive.yml`) archives the tag, installs it in a clean environment, checks that its version matches the tag, and attaches it to the release as `labconstrictor-tools.zip`. `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/releases/latest/download/labconstrictor-tools.zip` installs the newest release that is not a pre-release; a pre-release has the file at `.../releases/download/<tag>/labconstrictor-tools.zip`. The file is only added, never replaced. For an older release the maintainer can run the workflow from Actions with the tag.
* **Never move or recreate a tag.** Installers pin tags, so a moved tag would change what a pinned installer installs. A broken release is fixed with the next number.
* **The CI `compat` job** installs the newest tag and reads schemas across versions ([TESTING.md](TESTING.md)).

### Pinning Tools in app installers

An app installer installs a **tagged** Tools, never `main`: `main` moves, so two installs of the same app a week apart would run different workers, and a breaking change would reach installed apps without a release.

* The installer installs `LC_TOOLS_SPEC` with one `pip install` ([LABCONSTRICTOR_INTEGRATION.md](LABCONSTRICTOR_INTEGRATION.md)). Its default is `https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/<tag>.zip`, built from the pinned tag. Never `refs/heads/main.zip`, a branch or a commit that is not a tag.
* `LC_TOOLS_SPEC` stays the override: a local wheel for tests, a mirror, a branch for a developer.
* The pin is the line `LC_TOOLS_PIN` of the template's `app/bash_bat_scripts/post_install.sh` and `post_install.bat`; the [template's files](https://github.com/CellMigrationLab/LabConstrictor/tree/main/app/bash_bat_scripts) show the current tag. Apps get it by the template sync, and users get it with the app's next release.
* A pin may name a pre-release tag (`-rc.N`, `-alpha.N`) while no final release exists; it is replaced by the final release when there is one.
* A pin change is a one-line pull request to the template, merged only after the maintainer has created the tag. An installer that pins a missing tag fails at `pip install`; the installer reports it and finishes the rest of the install.
