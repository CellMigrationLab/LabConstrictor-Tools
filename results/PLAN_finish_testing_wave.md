# Plan to finish this wave of testing (15 Oct 2026)

Goal: the final test set is released, verified on Linux, documented, and ready for the human round; every code change is in a reviewed PR; nothing is left only on a scratch branch.

## Final test set (frozen)
Hosts Napari / Fiji / QuPath `v0.1.0-alpha.4` (Tools pin `v0.3.0-alpha.1`); apps Guess the Condition 0.0.1, Playground 0.0.5, VLab4Mic 0.1.7, NucleiSky 0.1.4, CellTracksColab 1.1.3.

## Steps (gate = what must be true before the next step)
1. **Docs PR #143 merged** (VLab4Mic 0.1.7, CellTracksColab 1.1.3, known issues, Wave 2 item 5). Gate: CI green, head verified.
2. **Issue #141 corrected** (it still names VLab4Mic 0.1.6 and CellTracksColab 1.1.2). Gate: body matches the start page.
3. **Website rebuilt** so the App Centre shows VLab4Mic 0.1.7 and CellTracksColab 1.1.3. Gate: the live apps page lists both versions.
4. **Final-set checks on Linux** (background agent): VLab4Mic 0.1.7 (new refusals, no stray radio windows), CellTracksColab 1.1.3 (new refusals, still hidden, Custom notebook), NucleiSky 0.1.4 in full (never run before: sandbox, 7 notebooks, three hosts, synthetic data). Gate: results in `results/alpha4/`, findings classified.
5. **Fix what the checks find**: host and Tools bugs by PR; app bugs by PR to the app (the owner's call for NucleiSky); a new release only for a blocker.
6. **Make the test code permanent**: open PRs for the audit drivers (Napari, Fiji, QuPath), the notebook runner, the synthetic generators and the strategy tooling, each passing the repository's own lint and type checks. Gate: PRs open, nothing merged without a go.
7. **Evidence for the team**: consolidate `RESULTS.md` (alpha.1 to alpha.4) and publish the private screenshot gallery (one page per app and host).
8. **Announce the round** (owner): testers follow the start page and issue #141.
9. **Housekeeping**: remove my scratch worktrees and installs; confirm no uncommitted or unpushed work.

## Owner steps (not mine): announce the round; open the two upstream VLab4Mic PRs; decide on enabling Issues on the VLab4Mic fork; tag any release a blocker needs.
