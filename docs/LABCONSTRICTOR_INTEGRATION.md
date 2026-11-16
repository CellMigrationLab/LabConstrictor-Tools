# How the LabConstrictor template registers an app's tools (as built)

Implemented in the template (0.1.16 and later); the template's `post_install` hooks pin a Tools tag (`LC_TOOLS_PIN`, [OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers)), and apps get the hooks by the template sync.
The Linux (`.sh`) hooks run inside real installers built with `constructor`; the template's CI runs `post_install` on Linux, Windows and macOS, and the Windows (`.bat`) hooks also run in the release sandbox on a Windows runner ([TESTING.md](TESTING.md)). A person has not yet tested them on Windows or macOS.

## What an app must contain
* A Python package `<package>` listed in `construct.yaml` (`extra_files`, with its `setup.py`), as for any app with external code.
* A module **`<package>_lc_tools`** next to it (for NucleiSky `src/nucleisky_lc_tools/__init__.py`), also listed under `extra_files`.
  Apps without such a module are unaffected: the hook does nothing.

## `post_install.sh` / `post_install.bat` (after the app's own `pip install`)
1. Looks for `<package>_lc_tools` in the app's Python (`importlib.util.find_spec`); the `.sh` also requires the bundled `setup.py`.
2. Reads the app version from the top-level `version:` line of the bundled `construct.yaml` (quotes removed; `0` if missing).
3. Installs `labconstrictor-tools`: `pip install "${LC_TOOLS_SPEC:-https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/${LC_TOOLS_PIN}.zip}"`, with `LC_TOOLS_PIN="v0.3.0-alpha.2"` in the template. The default is the GitHub source archive of the package at a pinned tag (never `main`, see [OPERATIONS.md](OPERATIONS.md#pinning-tools-in-app-installers); an installer that still pins an older tag installs that older Tools)
   (a plain zip: the user's computer needs internet access at that moment but no `git`), because the package is not on PyPI yet; once it is,
   the default becomes `labconstrictor-tools`. `LC_TOOLS_SPEC` overrides it: a wheel, a git URL (for example
   `git+https://github.com/CellMigrationLab/LabConstrictor-Tools@main`), a mirror. If this step fails (no internet, unreachable source) the
   installation still finishes, registration is skipped and `menuinst_debug.log` says `WARNING: tool registration failed`.
4. Runs `python -m labconstrictor_tools register --name <App> --prefix <prefix> --module <package>_lc_tools --version <version> --display-name <App> --app-manifest <prefix>/<App>/labconstrictor-app.yaml`.
   (No `--pythonpath`: the module is installed in the app's environment.) `--app-manifest` passes the app's `hosts:` (and `host_requirements`) to the registry; when the bundled
   `labconstrictor-app.yaml` is missing, the app is registered without hosts (every host lists it) and the log says so.
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
* The `.bat` hooks on Windows and the whole flow on macOS run in CI, and people have done clean installs on Windows and macOS.
