# What the LabConstrictor template would change

**Status: proposal. None of this has been run inside a real installer build** (the runtime itself was tested with real installed
apps on Linux and the worker/registry layer with a real Windows installer under Wine).

1. `requirements.txt` (merged from notebooks' requirements): add `labconstrictor-tools==<x.y.z>` (+ hash).
2. `app/bash_bat_scripts/post_install.sh` / `.bat`, after the existing `pip install -r requirements.txt`:
   ```sh
   # only if the app ships a declaration module (see docs/AUTHORING.md)
   if [ -f "$PROJECT_ROOT/lc_tools.py" ]; then
       "$PYTHON_EXE" -m labconstrictor_tools register --name "$APP_NAME" --prefix "$PREFIX" \
           --module lc_tools --pythonpath "$PROJECT_ROOT" --version "$APP_VERSION" --display-name "$APP_DISPLAY_NAME" \
           >> "$LOG_FILE" 2>&1 || echo "tool registration failed (the app itself is fine)" >> "$LOG_FILE"
   fi
   ```
   (`.bat`: the same with `%PREFIX%\python.exe`.) A failure must never fail the installation.
3. `pre_uninstall.sh` / `.bat`: `"$PYTHON_EXE" -m labconstrictor_tools unregister --name "$APP_NAME" || true`.
4. Template files: ship `lc_tools.py` from the app repo (listed in `construct.yaml` `extra_files`, like `src/`), and add the docs page.
5. Template sync: a migration that adds items 1-3 to existing app repos; apps without `lc_tools.py` are unaffected.
6. Updating an app (re-running its installer) re-registers it, which refreshes the cached schema.

Open questions for the template maintainers: where `APP_NAME`/version variables come from in the scripts; whether the registry
should be per-user or per-machine for "All users" installs (supported by `--dir` + `LC_APPS_PATH`, not wired up here);
the final package name and hosting.
