# Prompt: test the LabConstrictor tools bridge from the repositories

Copy everything below the line into a fresh Claude Code session (a new container) that has access to the six repositories.

---

You are testing a new feature of LabConstrictor from **source code in GitHub repositories**, in a clean container. The goal is a
verified, honest report of what works and what does not. Do not trust earlier claims: reproduce.

## What the feature is
LabConstrictor apps can expose typed Python functions ("tools") to **Napari** and **Fiji** through a generic, out-of-process runtime.
An app declares tools in a module `<package>_lc_tools`; at install time `post_install` installs `labconstrictor-tools` and registers
the app (`labconstrictor-tools register`). Napari and Fiji read the registry, generate forms from each tool's schema, and run the tool
in the app's own Python in a separate worker process. Image inputs can come from an open layer/window or a file.

## Repositories (GitHub org CellMigrationLab; all private or public, use the session's GitHub access)
| Repo | Branch | Role |
|---|---|---|
| `LabConstrictor-Tools` | `main` | runtime + CLI (`labconstrictor-tools`), example app `labconstrictor_tools.examples.synthetic`, docs, Python tests |
| `napari-labconstrictor` | `main` | Napari dock widget, tests under Xvfb |
| `LabConstrictor-Fiji` | `main` | Fiji command (Maven jar + Groovy script), GUI test harness |
| `LabConstrictor` | `bridge-test` | template: `app/bash_bat_scripts/post_install|pre_uninstall .sh/.bat` register/unregister hook, `.tools/docs/tools_bridge.md` |
| `NucleiSky` | `bridge-test` | app: `src/nucleisky_lc_tools`, hooks in its scripts, `lc_tests/` |
| `CellTracksColab` | `bridge-test` | app: `src/celltracks_lc_tools`, hooks in its scripts, `lc_tests/` |

Read each repo's README first. **Never push to `main` of LabConstrictor, NucleiSky or CellTracksColab.** Put fixes on a new branch
named `claude/<topic>` and report; do not open pull requests unless asked. For the three new repos, also use branches for fixes.

## Environment you must build (nothing is pre-installed)
* Python 3.11 and 3.12 (venvs), Linux. Java 21 and Maven (`mvn`). `xvfb-run` plus Qt/X libraries for Napari
  (`libegl1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0`).
* **Fiji** (download the Linux64 bundle from https://downloads.imagej.net/fiji/latest/fiji-latest-linux64-jdk.zip; if the network blocks it,
  say so, and test everything else). Fiji needs a display: tests run it under `xvfb-run`.
* The Tools repository may be private: install it from the **local clone** (`pip install ./LabConstrictor-Tools`) rather than `git+https`.
  The app installers use `LC_TOOLS_SPEC` for this (see step 4).
* Use a private registry for every test run: `export LC_HOME=$(mktemp -d)`.

## Steps (do them in order; stop and report on a blocker, do not improvise around it silently)
1. **Tools repo.** `pip install -e "./LabConstrictor-Tools[test]" black ruff`; run `black --check . && ruff check .`, then
   `cd tests && python -m unittest discover -v -p "test_*.py"` (about 2 minutes; expect 52 tests, 1 skipped). Also run
   `python tests/windows/test_windows.py` (it is Windows-oriented but should pass on Linux). Run the suite twice: report any flaky test.
2. **Napari repo.** Fresh venv (Python 3.11), `pip install "napari[pyqt5]" pandas scipy imageio tifffile`, then install the Tools clone and
   `pip install -e ./napari-labconstrictor`. Run `tests/test_units.py`, and with `xvfb-run -a` `tests/test_widget.py` and
   `tests/test_file_sources.py`. Open `evidence/widget_kitchen_sink.png` and describe what the UI looks like.
3. **Fiji repo.** `mvn -B package` (jar), then `export LC_FIJI_HOME=<Fiji.app>` and, in an env with the Tools clone + numpy pandas tifffile,
   `python tests/run_cases.py` (script mode) and `LC_FIJI_MODE=jar python tests/run_cases.py` (jar mode). Expect 10 cases each. Look at the
   screenshots under `evidence/` (dialogs). If a case hangs, the runner prints Fiji's output tail: report it.
4. **Install hook, template-level (shell block).** In `LabConstrictor` (branch `bridge-test`) read the added block in
   `app/bash_bat_scripts/post_install.sh`. In a scratch conda/venv env with a fake package `demo` that ships `demo_lc_tools.py` (use the example in
   `LabConstrictor-Tools/labconstrictor_tools/examples/synthetic.py` as a model) and a dummy `setup.py` + `construct.yaml` (`version: 1.2.3`),
   run the block with `LC_TOOLS_SPEC=<path to the Tools clone>`; verify `labconstrictor-tools list`, a `run`, `pre_uninstall` unregistering, and
   that a *failing* registration (e.g. broken `LC_TOOLS_SPEC`) does not stop the rest of `post_install`. The `.bat` variants cannot be run here:
   review them line by line for cmd.exe pitfalls (delayed expansion inside parenthesised blocks, quoting, `&&`, ERRORLEVEL after `IF`) and report concerns.
5. **Real apps from their own repos.**
   * `NucleiSky@bridge-test` and `CellTracksColab@bridge-test`: create each app's environment the way the installer would (read `environment.yaml`,
     `requirements.txt`, `setup.py`/`pyproject.toml`; Python 3.12; heavy packages such as torch may be skipped for the CellTracks app, and for NucleiSky
     only what `nucleisky_lc_tools` needs: numpy, scipy, scikit-image, numba, networkx, pandas, tifffile). `pip install --no-deps ./<app>`.
   * `labconstrictor-tools check --module <package>_lc_tools`, then `labconstrictor-tools test --module <package>_lc_tools --cases lc_tests/cases.json`
     (NucleiSky: first `python lc_tests/make_fixtures.py lc_tests/fixtures`; the first run compiles numba and is slow).
   * Register each app (`labconstrictor-tools register ...` exactly as `post_install` does) and verify in Napari (`test_widget`-style script or
     by hand under Xvfb with screenshots) and in Fiji (`python tests/run_cases.py --real-apps` with `LC_REAL_FIXTURES` pointing to a folder with `nucleisky/`
     `reference.tif`+`query.tif` and `celltracks/tracks.csv`, `LC_HOME` = the registry where both apps are registered).
   * **Optional, strongest test:** build the real installer on the app's `bridge-test` branch (`conda create -n ctor -c conda-forge python=3.11 constructor`,
     then `constructor . --output-dir out` as in `.tools/bash/build_installer_with_constructor.sh`), run it in batch mode (`bash installer.sh -b -p /opt/app`),
     set `LC_TOOLS_SPEC` to a wheel built from the Tools clone, and check the registry afterwards and the installer log
     (`menuinst_debug.log` in the prefix). Report honestly if the sandbox cannot do this.
6. **Failure diagnostics.** Break things on purpose and check that the error is *explained*, in Napari ("Details..."), in Fiji (error dialog) and in
   `$LC_HOME/logs/labconstrictor.log`: delete the app's python, remove a package from the app env, pass a corrupt TIFF, give a missing file, kill the
   worker (`kill -9`) mid-run, cancel a long NucleiSky run. Run `labconstrictor-tools doctor`, `logs`, `support-bundle` and check the zip contents.
7. **Review and adversarial pass.** Read `labconstrictor_tools/{worker,client,registry,convert,cli}.py`, the Fiji Groovy script, and the Napari widget
   looking for: path/command injection through registry entries or tool inputs, leftover processes or temp folders, behaviour with spaces/non-ASCII
   in paths, Windows-only pitfalls, UI states that can get stuck. Try to break them with a test; do not just opine.

## Known gaps (verify, do not assume)
Windows and macOS were never tested natively (Windows only under Wine earlier). The `.bat` hooks have never run. CI workflows in the repos have
not run. The Fiji jar is a packaging shell around a Groovy script (no Java port, no update site). Tables are file-only inputs. Large images are read
whole by the worker. `labconstrictor-tools` is not on PyPI, so installers that run `pip install labconstrictor-tools` fail until it is published or
`LC_TOOLS_SPEC` is set; the registration step then logs a warning and the app itself still installs.

## Deliverable
A report (Markdown, committed nowhere unless asked; print it and save under your scratchpad) with: environment details; per step PASS/FAIL/BLOCKED
with the exact commands and the relevant output lines; every bug found with a minimal reproduction; screenshots described; a list of fixes you
pushed on `claude/*` branches (commit ids); and a final section "What I could not test". Distinguish **demonstrated** from **inferred**. If you
disagree with a design decision, say so with evidence.
