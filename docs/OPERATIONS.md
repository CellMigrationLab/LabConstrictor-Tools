# Operations: install, shared/network installs, security, troubleshooting

## Install
How a person installs an app and the three hosts is one page: [INSTALL.md](INSTALL.md). In short:
* Each app environment needs `labconstrictor-tools` (standard library only, no dependencies); the app installer installs it from a **tag** (`LC_TOOLS_PIN`, below), and the hosts need Tools **0.3.0a1 or newer** in the app.
* **Install rules** (they come from the sandbox findings of 13 Oct): no space anywhere in the install path (the installers refuse it); macOS and Windows update by uninstalling first; Linux `installer.sh -u` updates in place only after a *finished* install (otherwise delete `<prefix>/pkgs` or uninstall first); testers install only tagged versions and only the latest.
* Napari (nothing is on PyPI yet; **Python 3.11 or newer, Qt6 backend**): `pip install "napari[pyqt6]" https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip https://github.com/CellMigrationLab/LabConstrictor-napari/archive/refs/tags/<NAPARI_TAG>.zip` in the napari environment. The plugin has no tag yet (14 Oct 2026), so `<NAPARI_TAG>` is a placeholder that does not resolve; its README and user guide now give the same tag lines (Napari PR #60, merged) and no longer use `refs/heads/main.zip`. Source archives: no `git` program needed. Plugins > LabConstrictor tools.
* Fiji (jar from the release, `labconstrictor-fiji-<tag>.jar`): copy it to `Fiji.app/plugins/`, restart: Plugins > LabConstrictor > LabConstrictor Tools... The release also carries `labconstrictor-fiji-script-<tag>.zip` (the script **and its `lib` folder**, to unzip into `Fiji.app/scripts/Plugins/LabConstrictor/`; entry without the dots; macro calls need the jar) and `SHA256SUMS` (Fiji README at f9277af; no Fiji release existed when this was written).
* QuPath 0.7.0 (jar from the release, `labconstrictor-qupath-<tag>.jar`): drag it onto the QuPath window and restart: Extensions > LabConstrictor tools... The Script Editor alternative is the **single file** `LabConstrictorTools-all.groovy` of the release; the repository's script is split into part files that only the jar and the build join (QuPath README at 9e64c6d; no QuPath release existed when this was written).
* **State today:** the Napari, Fiji and QuPath hosts are tagged `v0.1.0-alpha.4`. **For each test round, update the record sheet** (section 0.1) of [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md), the table in [TESTER_START_HERE.md](TESTER_START_HERE.md) and the cells of [TEST_MATRIX.md](TEST_MATRIX.md).
* Fiji, Napari and QuPath never import an app's packages, so apps with conflicting dependencies can coexist.

## Releases and tags
The version lives in one place, `labconstrictor_tools/_version.py` (`__version__`); `pyproject.toml` and `labconstrictor_tools.__version__` both read it. `describe`, the registry and `doctor` report it as `tools_version` ([PROTOCOL.md](PROTOCOL.md#tools-version-and-features)).
* **Tag names:** `vX.Y.Z` for a release (`v0.2.0`), `vX.Y.Z-rc.N` or `vX.Y.Z-alpha.N` (`-beta.N`) for a pre-release, always on a commit of `main`. The tag is a **lightweight** tag, the one GitHub creates when the release is made from the Releases page (step 4 below); it is the standard here, an annotated tag is not required. The tag has a leading `v`; the Python version in `_version.py` has not, and spells the pre-release PEP 440 style: `-rc.N` <-> `rcN`, `-alpha.N` <-> `aN`, `-beta.N` <-> `bN`. So tag `v0.2.0-rc.1` <-> `__version__ = "0.2.0rc1"` and tag `v0.3.0-alpha.1` <-> `"0.3.0a1"`. Order: `0.2.0rc1 < 0.3.0a1 < 0.3.0`.
* **Pinning a pre-release.** An app pins a tagged release; it may also pin a pre-release tag (`-rc.N`, `-alpha.N`) when a human-test round needs exactly that Tools (for example `v0.3.0-alpha.1` for the first human tests). An app never pins a branch or an untagged commit, and a pre-release pin is replaced by the final release when it exists.
* **One number, one code.** A tag and the version it reports must tell the code apart: a code change that a host can observe gets a new number in the same pull request. History: `v0.2.0-rc.1` and `v0.2.0-rc.2` (and `main` after it) all reported `0.2.0rc1` because `rc.2` did not bump the version string, so hosts could not tell them apart; `0.3.0a1` (tag `v0.3.0-alpha.1`) is the first number that does. There will be no `rc.3`: the next pre-release is `v0.3.0-alpha.1`, then `-alpha.N` / `-rc.N` of the number it leads to.
* **Who tags:** the maintainer tags. Claude and CI never create tags or GitHub releases; a pull request that wants a release says so in its description and the maintainer tags after merging.
* **Procedure:** (1) CI is green on `main` on all three systems (and the nightly of the same commit); (2) a pull request sets `_version.py` to the new number and moves the "unreleased" notes of the ledger; merge it; (3) and (4) in one step: on GitHub create the release with the new tag name, targeting the merge commit on `main` (GitHub creates the lightweight tag; tick "pre-release" for `-rc.N` and `-alpha.N`; the notes go in the body of the GitHub release, not in this repository); (5) check `pip install https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/v0.3.0-alpha.1.zip` in a clean environment and `labconstrictor-tools --help`; (6) a new `main` commit after the tag keeps the tag's version until the next bump PR (so `main` between releases reports the last number: `doctor` shows what is installed, not where it came from).
* **Never move or recreate a tag.** A broken release is fixed with the next number (`-alpha.2`, `0.3.1`); installers pin tags, and a moved or recreated tag would change what a pinned installer installs.
* **The CI `compat` job** installs the newest tag (if one exists) and reads schemas across versions, see [TESTING.md](TESTING.md).

### Pinning Tools in app installers
An app installer must install a **tagged** Tools, never `main`: `main` moves, so two installs of the same app a week apart would run different workers, and a breaking change (for example issue #51) would reach installed apps without any release. The installer already reads the source from `LC_TOOLS_SPEC` and installs it with one `pip install` ([LABCONSTRICTOR_INTEGRATION.md](LABCONSTRICTOR_INTEGRATION.md)); pinning only changes the default:
* Default value: `https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/<tag>.zip` (for example `v0.2.0` once it exists) or `.../refs/tags/v0.3.0-alpha.1.zip` while only a pre-release exists (a human-test round pins it, see above). Never `refs/heads/main.zip`, never a bare branch or a commit that is not a tag. An app moves to a newer Tools by a pull request that changes this one string (and runs its `lc_tests`), not by anybody tagging.
* `LC_TOOLS_SPEC` stays the override (a local wheel for tests, a mirror, a branch for a developer).
* After installing, the hook may record the version by running `labconstrictor-tools doctor`, which shows `Tools <version>`; a test of the installer checks that the version equals the pinned tag.
* A tag is only pinned after the maintainer created it ([Releases and tags](#releases-and-tags)); an installer that pins a tag that does not exist fails at `pip install`, which the hook already reports without stopping the rest of the install.

State at 14 Oct 2026 (read from the `main` branches of the repositories; search again before editing, other branches may carry more). Every installed app pins **`v0.2.0-rc.1`** today (`LC_TOOLS_PIN`); the pin moves to `v0.3.0-alpha.1` by one-string pull requests that are merged only after the maintainer created the tag, and reaches users only with a new app release:

| Repository | Pin today (file and line) | Pin pull request (draft, do not merge before the tag) | New app release after it | Still open outside the hooks |
|---|---|---|---|---|
| `labconstrictor-playground` | `app/bash_bat_scripts/post_install.sh:83` and `post_install.bat:232` | #27 | 0.0.4, decided (latest 0.0.3) | `notebooks/LabConstrictorPlayground/LabConstrictorPlayground.ipynb` line 48 (`!pip install -q ...refs/heads/main.zip`); `.github/workflows/ci.yml` installs Tools `@main` on purpose (development CI) |
| `NucleiSky` | `post_install.sh:73` and `post_install.bat:223`: the bridge is **merged** (`nucleisky_lc_tools` is on `main`) | #38 | 0.1.4, decided (latest 0.1.3) | none found |
| `labconstrictor-vlab4mic` | `post_install.sh:73` and `post_install.bat:223` | #17 | 0.1.6, decided (latest 0.1.5) | `README.md` lines 56-57 tell users to `pip install` Tools and the Napari plugin from `refs/heads/main.zip` |
| `guessthecondition` | `post_install.sh:73` and `post_install.bat:223` | #14 | 0.0.1, decided (latest 0.0.0) | none found |
| `CellTracksColab` | **no Tools step on `main`** (no tools registered); the held branch `bridge-test` has an unpinned `refs/heads/main.zip` line | none | 1.1.2 is held until the bridge decision (latest 1.1.1) | the bridge must be pinned to a tag before it is merged |
| `LabConstrictor` (template) | `post_install.sh:73` and `post_install.bat:223` | #33 (template 0.1.18: pin, pinned actions, template CI, install rules) | template release after #33 (tag: <fill in>) | apps get the pin and the install page by the template sync after it is released |
| Docs that tell people to `pip install` Tools | `LabConstrictor-napari/README.md` (line 77) and `docs/user-guide.md` (line 20) already say `refs/tags/<tag>.zip` with the placeholder `<NAPARI_TAG>` (Napari PR #60, merged); this repository's README and docs name the tag | | | replace `<NAPARI_TAG>` by the real tag once Napari has one |

The tests of this repository keep the strings `LC_TOOLS_SPEC`, `refs/tags/`, `refs/heads/main.zip`, `post_install.sh` and `post_install.bat` in the pinning section above.

## Playground rule
Every feature or limit needs a Playground tool or case, a generated matrix case and a host GUI check; how it is checked is written in [TESTING.md](TESTING.md#the-playground-rule).

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
* A registry entry makes hosts start a program. Entries must live in a directory only the user can write, the
  interpreter must be inside the entry's install prefix, and system-wide directories must be admin-controlled. These checks (owner, group/other-writable, interpreter inside the prefix, world-writable folders on the way) run on **POSIX only**. **Windows is unchecked**: file ownership and permission bits do not map to its access-control lists, and no equivalent check has been written, so on Windows a registry entry is trusted as found. Treat write access to
  these directories like write access to the user's startup items.
* Pin `labconstrictor-tools` in app requirements (with hashes if you can); it is the only code every app shares.

## Troubleshooting
* `labconstrictor-tools doctor` checks every entry (interpreter, schema, protocol, staleness) and prints what to fix.
* Stale tool list after an app update: run `labconstrictor-tools register ...` again (the installer does this).
* `labconstrictor-tools run` without `--out` writes its results to `<LC_HOME>/results/<time>_<app>_<tool>` (the newest 20 finished ones are kept by `labconstrictor-tools prune`, which the hosts start after a run: hosts never prune themselves, they write the markers and call the Tools CLI; a host that works in its own temporary folder writes the markers there and starts `prune`). `prune` removes only folders that carry LabConstrictor's own marker files (`.lc-owner.json` and `.lc-done.json`): a folder you made yourself, or one from an older version without markers, is never touched. Look first with `labconstrictor-tools prune --dry-run`; the rules are in [PROTOCOL.md](PROTOCOL.md#result-folders-and-run-records-retention).
* Every run writes `<LC_HOME>/runs/<time>_<app>_<tool>/run.json` (parameters as file paths and values, never pixel data; status,
  error, traceback, interpreter, worker output). Napari's *Details...* button shows it; attach it to bug reports. The newest 50 finished records are kept (`prune`, same rules).
  A Python host that makes its own record folder (Napari) builds the content with `labconstrictor_tools.runs.build_record`, writes it with `runs.record_json` and picks the done status with `runs.done_status` (a crash after Cancel is `cancelled`); none of them prunes, the host starts `labconstrictor-tools prune` itself ([PROTOCOL.md](PROTOCOL.md#result-folders-and-run-records-retention)). They exist from 0.3.0a1 (they are in the code of `v0.2.0-rc.2` too, which still reports `0.2.0rc1`, so a host requires `min_tools_version` 0.3.0a1 or checks `hasattr`). There is no feature id for them.
* A file that a tool still holds is locked on Windows. From 0.3.0a1 Tools opens TIFF files of 8 MiB or more that are uncompressed and contiguous as a copy-on-write memory map (set `LC_TIFF_MEMMAP=0` to read them the plain way). On Windows a tool that keeps a reference to its input (a global, a stored exception, a thread that outlives the run) keeps the file mapped and therefore locked until the worker ends; the host cannot delete or overwrite that file meanwhile. Linux and macOS are not affected.
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
| `convert._memmap_tiff` (a TIFF input of 8 MiB or more) | The file could not be memory-mapped (compressed, tiled, multi-series, OME or other special layout, big-endian, truncated, not contiguous, `LC_TIFF_MEMMAP=0`, or the mapping failed): it is read the plain way with `tifffile.imread`, same pixels, more memory and time. Files under 8 MiB are the normal plain path and say nothing | One warning line with the file name and the reason, in the log and on the worker's stderr |
| `Worker._orphan_exit` | The host is gone and a temporary folder of the worker could not be removed completely: the worker leaves anyway | One warning line in the log file only (stderr has no reader any more) |
| `log.tail()` (`logs`, Details windows) | The log file does not exist or cannot be read: an empty tail | Nothing to show; a debug line explaining why |

## Known limits (testing phase)
* Verified on Linux with real NucleiSky and CellTracksColab installers (the CellTracksColab one with the bridge branch, which is not on its `main`), in Napari and Fiji, in October 2026 and earlier (an earlier VLab4Mic check is not repeated here); the release sandbox runs released apps on fresh Linux, macOS and Windows runners ([TESTING.md](TESTING.md#release-sandbox-a-released-app-on-fresh-runners)). QuPath: GUI tests on Linux in its own CI; nobody has used it by hand on any system.
  Windows by a person: not done; the `.bat` install hooks run in the sandbox on a Windows runner only; macOS by a person, UNC/NFS shares and multi-user "all users" installs are untested. People can help with these: [HUMAN_TEST_PROTOCOL.md](HUMAN_TEST_PROTOCOL.md).
* The worker reads image files whole (no lazy/chunked reading); TIFF always, other formats only when the app has `imageio`.
* No sandbox: a tool runs with the user's rights, like any app code. The worker only executes tools declared by the registered module.
* A protocol change is a major version; hosts say so in the UI when an app speaks a newer protocol than they do.
* A tool must stop the threads it starts before it returns: a leftover thread that calls `progress()` while the NEXT task runs is reported on that next task (after its own task ends the hooks do nothing).
* Logs are one shared rotating file; concurrent writers (Napari, Fiji, CLI) do not lock it.
* A worker is started with `PYTHONSAFEPATH=1` (Python 3.11+) so that the directory the host was started from is not on the tool's import path; on older Pythons a stray `pandas.py` there could shadow a real package.
