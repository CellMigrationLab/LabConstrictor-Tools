# Windows check (Wine)

No Windows machine was available, so the real Windows installer is run under Wine 9 and the tests run with the Windows
`python.exe` (host AND worker are Windows processes). This is *not* a substitute for real Windows - see REPORT_V2.md §17.

1. `wine installer.exe /S /D=C:\apps\<App>` (needs `wine64` + `wine32`; the constructor installers are 32-bit NSIS).
2. Install the app's requirements into it (inside a sandbox with TLS interception set `PIP_CERT`).
3. Copy `labconstrictor_tools/`, `apps/synthetic`, `apps/celltracks`, `tests/` to `C:\poc`, then `bash run_suite.sh`.

Wine quirks (not product issues): Python needs stdout to be a pipe and stdin valid (`winpy.sh` does this), non-ASCII file
names need a UTF-8 locale, and the first `import pandas` is very slow. `winpy.sh` pins `LC_HOME` inside the prefix so the
Windows tests can never touch the Linux registry.
