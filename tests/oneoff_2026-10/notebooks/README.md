# Notebook family (`nb`) of the one-off run

Checks every notebook an installed app packages: `packaged`, `valid`, `kernel`, `imports`, `runs` (simulated clicks), `oracle`, `sideeffects`, `downloads`, `noleak`, plus a `net_<n>` NOTE row for every HTTP request (URL, status or failure, size).

    python nb_runner.py --app NAME --prefix PREFIX --src SRC_CHECKOUT_AT_TAG --tag TAG --results DIR --lc-home LC_HOME [--only NB[,NB]]

* One worker (`nb_worker.py`, the app's own interpreter) and one kernel per notebook; outer watchdog `LC_NB_TOTAL_TIMEOUT` (3600 s), per-cell timeout `LC_NB_CELL_TIMEOUT` (300 s), download cap `LC_NB_DOWNLOAD_CAP_MB` (300).
* Notebooks run in a scratch copy of the app folder with HOME in `<results>/<app>/home_<nb>`; pip has no index; the scratch home is emptied afterwards (small text files kept).
* Click scripts: `scripts/<app>/<notebook>.py` (stages run after named cells, `AUTO_DRIVE_ALL`, `HUMAN_CELLS`, `edit_cells`, `oracle`). Kernel helpers: `lcnb_kernel.py`.
* `check_scripts.py` checks every script against the notebooks at the tag; `test_nb_runner.py` holds the negative controls (seeded failures that must go red).
