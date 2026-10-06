# How the LabConstrictor template registers an app's tools (as built)

**Status.** Implemented on the `bridge-test` branches of `LabConstrictor` (the template), `NucleiSky` and `CellTracksColab`.
The Linux (`.sh`) hooks were run inside real installers built with `constructor`. The Windows (`.bat`) hooks have **never been run on Windows**
(see HUMAN_TEST_PROTOCOL.md). An earlier draft of this page proposed a different design (`lc_tools.py`, `APP_NAME` variables): that is not what was built.

## What an app must contain
* A Python package `<package>` listed in `construct.yaml` (`extra_files`, with its `setup.py`), as for any app with external code.
* A module **`<package>_lc_tools`** next to it (for NucleiSky `src/nucleisky_lc_tools/__init__.py`), also listed under `extra_files`.
  Apps without such a module are unaffected: the hook does nothing.

## `post_install.sh` / `post_install.bat` (after the app's own `pip install`)
1. Looks for `<package>_lc_tools` in the app's Python (`importlib.util.find_spec`); the `.sh` also requires the bundled `setup.py`.
2. Reads the app version from the top-level `version:` line of the bundled `construct.yaml` (quotes removed; `0` if missing).
3. Installs `labconstrictor-tools`: `pip install "${LC_TOOLS_SPEC:-https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/heads/main.zip}"`. The default is the GitHub source archive of the package
   (a plain zip: the user's computer needs internet access at that moment but no `git`), because the package is not on PyPI yet; once it is,
   the default becomes `labconstrictor-tools`. `LC_TOOLS_SPEC` overrides it: a wheel, a git URL (for example
   `git+https://github.com/CellMigrationLab/LabConstrictor-Tools@main`), a mirror. If this step fails (no internet, unreachable source) the
   installation still finishes, registration is skipped and `menuinst_debug.log` says `WARNING: tool registration failed`.
4. Runs `python -m labconstrictor_tools register --name <App> --prefix <prefix> --module <package>_lc_tools --version <version> --display-name <App>`.
   (No `--pythonpath`: the module is installed in the app's environment.)
5. Writes to `menuinst_debug.log`: `Found <package>_lc_tools: registering ...`; then on success (`.sh`) `Tools registered (labconstrictor-tools list shows them).`
   (the `.bat` prints the register output instead); on failure `WARNING: tool registration failed - see the pip and register output above ...`.
   **A failure here never fails the installation.**

## `pre_uninstall.sh` / `.bat`
`python -m labconstrictor_tools unregister --name <App> --prefix <prefix>`, errors ignored. With `--prefix`, the entry is removed only if it still belongs to
this installation: installing the same app twice and uninstalling the older copy leaves the newer registration in place.

## Placeholders
In the template the hooks contain `PROJECT_NAME` and `PYTHON_PROJ_NAME`, substituted in each app repository (the app's display name and its Python package).
An unsubstituted `PYTHON_PROJ_NAME` in the `import` line of `post_install.sh` once made the NucleiSky installer exit with `ModuleNotFoundError`; if you
see that, the substitution did not happen.

## Where the registry is
`~/.labconstrictor/apps` (per user; override with `LC_HOME`). Shared and system-wide directories: docs/OPERATIONS.md.

## Open questions
* Publishing `labconstrictor-tools` on PyPI, so that `LC_TOOLS_SPEC` is no longer needed (and pinning it with hashes in the apps' requirements).
* Per-machine ("all users") installs: supported by `register --dir` and `LC_APPS_PATH`, not wired into the installers.
* Verifying the `.bat` hooks on Windows and the whole flow on macOS.
