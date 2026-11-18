# How the template registers an app's tools

An app built from the LabConstrictor template registers its tools when it is installed. The work is done by the template's `post_install` and `pre_uninstall` scripts in `app/bash_bat_scripts/` (`.sh` for Linux and macOS, `.bat` for Windows); apps get them through the template sync. How an app author exposes tools is in [Expose your app's tools](https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tools-bridge/).

## What an app must contain

* A Python package `<package>`, listed with its `setup.py` under `extra_files` in `construct.yaml`, as for any app with external code.
* A module named exactly **`<package>_lc_tools`** next to it (for NucleiSky, `src/nucleisky_lc_tools/__init__.py`), also under `extra_files`.
* `labconstrictor-app.yaml` under `extra_files`, so that the installer can pass its `hosts:` and `host_requirements` to Tools.

An app without a `<package>_lc_tools` module is not affected: the steps below do nothing.

## What `post_install` does

After the app's own packages are installed:

1. **Installs Tools**, if the app's Python finds `<package>_lc_tools` (`importlib.util.find_spec`). This happens before the app's import check, because the app's package may import `labconstrictor_tools`. The command is `pip install "${LC_TOOLS_SPEC:-https://github.com/CellMigrationLab/LabConstrictor-Tools/archive/refs/tags/${LC_TOOLS_PIN}.zip}"`: the source archive of the pinned tag, which needs internet access at that moment but no `git`. `LC_TOOLS_SPEC` overrides it with a wheel, a git URL or a mirror ([Pinning Tools in app installers](OPERATIONS.md#pinning-tools-in-app-installers)).
2. **Reads the app version** from the top-level `version:` line of the bundled `construct.yaml` (quotes removed; `0` if missing).
3. **Registers the tools:**

       python -m labconstrictor_tools register --name <App> --prefix <prefix> --module <package>_lc_tools \
           --version <version> --display-name <App> --app-manifest <prefix>/<App>/labconstrictor-app.yaml

   There is no `--pythonpath`, because the module is installed in the app's environment. `--app-manifest` passes the app's `hosts:` and `host_requirements` to the registry. Without the bundled `labconstrictor-app.yaml` the app is registered without hosts, so every host lists it, and the log says so.
4. **Writes to `menuinst_debug.log`** in the install folder: `Found <package>_lc_tools: registering the tools of <App> for Napari, Fiji and QuPath`, then on success `Tools registered (labconstrictor-tools list shows them).` (Linux and macOS; on Windows the output of `register`), or on failure `WARNING: tool registration failed - see the pip and register output above in this file; <App> itself is installed.`

**A failure here never fails the installation.** If Tools cannot be installed (no internet, unreachable source), the app is still installed and its tools are not registered.

## What `pre_uninstall` does

It runs `python -m labconstrictor_tools unregister --name <App> --prefix <prefix>`. A failure does not stop the uninstall; if the entry is still there, a warning names the two files to delete (`<App>.json` and `<App>.schema.json` in the registry). With `--prefix`, the entry is removed only if it still belongs to this installation: after installing the same app twice, uninstalling the older copy leaves the newer registration in place.

## Placeholders

In the template the scripts contain `PROJECT_NAME` (the app's display name) and `PYTHON_PROJ_NAME` (its Python package), replaced in each app repository. If an installer stops with `ModuleNotFoundError` for `PYTHON_PROJ_NAME`, the replacement did not happen.

## Where the registry is

`~/.labconstrictor/apps`, per user (`LC_HOME` overrides the base folder). Shared and system-wide directories are in [Operations](OPERATIONS.md#many-apps-many-users-network-shares). The installers register per user only; per-machine installs are possible with `register --dir` and `LC_APPS_PATH` but are not wired into the installers.
