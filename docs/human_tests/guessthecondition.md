# Human tests: Guess the Condition (Napari, Fiji, QuPath)

Part of the [human test protocol](../HUMAN_TEST_PROTOCOL.md): fill in its record sheet first, install the app (proposed release 0.0.1, to be confirmed; 0.0.0 is the only release today) and the host(s) as it says.
Guess the Condition shows microscopy images without their condition; you guess, and the app compares your accuracy with chance, per biological repeat. **Discovery:** listed in Napari, Fiji and QuPath.
Registered name `GuessTheCondition`; six tools: **Create a demo experiment**, **Prepare the game**, **Show the conditions** (a helper that fills the guess list), **Play a round**, **Undo my last guess**,
**Analyse the results**. Expected values come from the app's README and its `lc_tests/cases.json` (22 cases, 22 run and passed in a local check by the authors, not in CI); the way each host shows a step: not verified unless stated.

Use the **same steps in each host**; write the host in the Notes. The game is played one tool run at a time: *Play a round* shows an image; you pick the condition in the **Guess** list and press Run/OK:
your guess is recorded and the next image appears.

## GC-1. Create a demo experiment
**Do:** make an empty folder `<GAME>`. Run **Create a demo experiment** with *output folder* = `<GAME>` and *images per repeat* = 2. Terminal: `<APP_PY> -m labconstrictor_tools run GuessTheCondition create_demo_experiment output_folder=<GAME> images_per_repeat=2`.
**Expect:** a folder `<GAME>/GuessTheCondition_demo` (the experiment: 2 conditions x 3 repeats x 2 images = **12 images**; the result says `images` 12 and names the folder). Run it again: **refused** (`already_exists`, "already exists"; nothing is overwritten). With a folder that does not exist: refused.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## GC-2. Prepare the game
**Do:** run **Prepare the game**: *experiment folder* = `<GAME>/GuessTheCondition_demo`, *results folder* = a second existing empty folder `<RESULTS>`, *your name* = `Ana`, *percentage to guess* = 25, *start again* ticked, and under advanced settings *random seed* = 7.
**Expect:** `images 12`, `to_guess 3` (25 percent of 12), `guessed 0`, `remaining 3`, conditions `1: Control | 2: Mutant` (demo condition names as in the app's cases), the game folder `<RESULTS>/Ana`, and a hint to run **Play a round**. A name that is not a folder name (`a/b`) is refused (`bad_user_name`, "folder name").

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## GC-3. Play a round: the first image, a guess, the guess list
**Do:** run **Play a round** with the guess unset. Look at the image and the message. Then pick a condition in the **Guess** list and run again.
**Expect:** first: an image (**the condition and file name of the image are never shown**) and the message `image 1 of 3`, `conditions 1: Control | 2: Mutant`; the guess box is a drop-down filled by **Show the conditions**. Second: your guess is recorded and `image 2 of 3` appears; the **Guess** box is emptied after the run (it must be chosen again every round); each run replaces the previous image (one layer / window / results window, not a pile). **Fiji:** the list appears only from your second run onwards (before that a text field; tick *Set guess* and choose). **Napari:** the form scrolls and Run/status stay in view. **QuPath:** the image is a preview with an "Open in QuPath" button (how the image is shown for guessing: not verified).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (host): ______________________________

## GC-4. Wrong guesses are explained
**Do:** type a guess that is not a condition (`Nonsense`) where the host allows free text (Napari/QuPath may only offer the list: then N/A; the terminal always allows it: `... play_round results_folder=<RESULTS> user_name=Ana guess=Nonsense`). Also try a guess by number (`2`) and in another case (`mutant`).
**Expect:** `Nonsense`: a failure with `unknown_condition` and `Choose one of: 1: Control | 2: Mutant`; the game is not advanced. A number and any letter case are accepted. A blank guess is refused (`empty_guess`).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## GC-5. Undo my last guess
**Do:** after at least one recorded guess run **Undo my last guess**; then play that image again.
**Expect:** the result names the forgotten guess and `guessed` goes down by one; the image you undid is shown again.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## GC-6. Finish the game
**Do:** play on until the game says it is over (the last guess of 3).
**Expect:** the last guess is saved and the game says it was the last image (`no_result`, "last image": a notice, not an error); running **Play a round** again says `finished` ("Thank you"). `<RESULTS>/Ana/game_results.csv` has one row per image (the true condition, your guesses, decision times) and `session.json` exists.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## GC-7. Analyse the results
**Do:** run **Analyse the results** (results folder `<RESULTS>`, name `Ana`).
**Expect:** a readout that mentions the 3 images guessed, a confusion matrix, decision times and a **PDF report** at `<RESULTS>/Ana/analysis/analysis_results.pdf` (with figures and tables next to it). With 3 guesses and 3 repeats of which each has too few images this is a pilot: the app does not claim a verdict across repeats (with 1-2 repeats an exploratory test of these images; with 3 or more usable repeats a test across repeats). A player with no guesses (`Fresh`): refused (`no_guesses`, "play some rounds first").
Decision times are plausible (they include about half a second of display delay, the same for every guess; not verified).

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes (what the readout says): ______________________________

## GC-8. Stop and resume
**Do:** run **Prepare the game** again for `Ana` with *start again* **unticked** and percentage 100; then **Play a round**.
**Expect:** the guesses are kept (`guessed 3`), `to_guess 12`, `remaining 9`, and the game goes on with `image 4 of 12`. With *start again* ticked the earlier results are kept as a backup. Running **Play a round** for a name with no game (`Nobody`): `no_session`, "prepare the game first".

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________

## GC-9. Your own experiment (optional)
**Do:** make a folder with one subfolder per condition (at least two) and in each one subfolder per biological repeat holding `.tif` images; run **Prepare the game** on it.
**Expect:** the conditions and repeats are listed in the result; unreadable images are skipped and flagged during play. 2D, multichannel and stack images are accepted (channels are shown separately; a stack is normally a maximum-intensity projection). Each channel is contrast-stretched on its own, so the game cannot judge differences in absolute brightness: not a bug.

- [ ] PASS  - [ ] FAIL  - [ ] N/A   Notes: ______________________________
