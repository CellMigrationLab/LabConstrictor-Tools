Raw outputs of the proofs of 14 Oct 2026 (container, Linux). How each was produced is in ../README.md.
run_cases_* : every case of the generated cases.json through `python -m labconstrictor_tools run` (the worker, no GUI).
  GuessTheCondition: the INSTALLED app (/home/user/apps/GuessTheCondition). LabConstrictor-Playground and CellTracksColab: the app SOURCE registered into a scratch LC_HOME with the
  Tools venv (CellTracksColab with matplotlib/ipywidgets stubbed: only the metric functions are real); NOT the installed apps.
  NucleiSky and VLab4Mic: not run (apps not installed).
check_ground_truth_* : check_ground_truth.py on those reports (FAIL lines are findings, see the report).
sandbox_checks_cases_GuessTheCondition.txt : tests/release_sandbox/sandbox_checks.py cases on a copy of the generated folder.
