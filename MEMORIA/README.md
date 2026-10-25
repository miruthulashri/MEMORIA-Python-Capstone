# MEMORIA - The Game That Forgets You

**Academic title:** Development of an Adaptive Memory-Based Psychological Puzzle Game Using Python
**Category:** Python Game Development | **Genre:** Psychological Mystery / Memory Puzzle / 2D

MEMORIA is a complete desktop memory-puzzle game. You wake up inside a building whose rooms keep changing:
objects vanish, get replaced and move around. Clear five memory rooms to escape. The game watches how you
perform and quietly adjusts its difficulty (simple rules, **no machine learning**).

Everything is drawn with Pygame shapes. There are **no image or sound files** and no internet is needed.

---

## 1. Requirements

| Item | Version |
|------|---------|
| Operating system | Windows 10 / 11 |
| Python | 3.14.7 (any recent Python 3 should work) |
| Game library | **pygame-ce** (imported as `pygame`) |
| Save system | SQLite (built into Python, nothing to install) |

> Use **pygame-ce**, not the original `pygame`. Installing both together causes conflicts.

## 2. Installation and running (Windows + VS Code)

1. Copy the `MEMORIA` folder somewhere easy, for example `C:\Projects\MEMORIA`.
2. Open VS Code, then **File > Open Folder...** and choose the `MEMORIA` folder.
3. Open a terminal: **Terminal > New Terminal** (PowerShell).
4. Check Python:
   ```
   py --version
   ```
5. Install the game library:
   ```
   py -m pip install -r requirements.txt
   ```
   (or `py -m pip install pygame-ce`)
6. Check it:
   ```
   py -c "import pygame; print(pygame.version.ver)"
   ```
   You should see a version number such as `2.5.8`.
7. Run the game:
   ```
   py main.py
   ```

Optional: press `Ctrl+Shift+P`, choose **Python: Select Interpreter**, and pick Python 3.14 so VS Code's
play button (Run Python File) also works.

**Save file:** `memoria_save.db` is created automatically next to `main.py` the first time you run the game.
Delete that file to wipe all saved profiles.

### Troubleshooting

* `ModuleNotFoundError: No module named 'pygame'` - run step 5 again in the same terminal.
* Both `pygame` and `pygame-ce` installed - run
  `py -m pip uninstall pygame -y` then `py -m pip install --force-reinstall pygame-ce`.
* Window opens but fonts look plain - fonts fall back automatically (Segoe UI, Calibri, Arial, then default).
* A red warning on the title screen says the save file could not be used - the folder may be read-only.
  Move the project to a normal folder such as Documents. The game still works but will not save.

## 3. How to play

1. **Start Game**, type your name, read the story, pick **Level 1**.
2. **Observe** the room until the countdown ends (or press **I'm Ready**).
3. The lights flicker and the room changes.
4. **Answer:** click a card to select it, then press **Submit Answer**.
5. Use **Hint** (one per question, costs 25 points) if you are stuck.
6. Finish the level to unlock the next. Clear all five to reach the ending.

### The five levels

| Level | Name | What happens |
|------|------|--------------|
| 1 | The Forgotten Room | Memorize 5 objects (15 s). One vanishes. Pick it from three choices. |
| 2 | False Memories | Memorize 6 objects. One is replaced by a different object. Click the intruder. |
| 3 | The Changing Room | Objects stand in fixed positions. One moves to a new spot. Click it. |
| 4 | The Memory Sequence | Watch glowing symbols, then click them in the same order. |
| 5 | The Final Reconstruction | One room, three changes (vanish, replace, move), then an escape-lock sequence. Get 3 of 4 stages right. |

(The numbers above are for **Normal** difficulty. They go up or down as the game adapts.)

### Controls

| Key / mouse | Action |
|------------|--------|
| Left click | Press buttons, select cards, click symbols |
| Enter | Submit answer / continue / create profile |
| Space | "I'm Ready" while observing, continue after feedback |
| H | Use hint |
| Backspace | Undo last symbol (sequence levels) / delete a letter (name box) |
| Esc | Go back (leaving a level abandons that attempt) |

### Scoring

* Correct answer: **+100**
* Time bonus: **up to +50** (more time left = more bonus)
* Hint: **-25** (the level score is never below 0)
* Passing a level: **+100**
* **Total score = sum of your BEST score on each level.** Retrying can raise a level's best score but
  never stacks up, so retries are never double counted.
* Accuracy = correct answers / answered questions (each question is counted once, including failed attempts).

### Adaptive difficulty (rule-based)

After every question the hidden difficulty value moves between **-1 (Gentle)** and **+2 (Intense)**:

* Wrong answer or time-out: **-1** (more time, fewer objects, shorter sequence, hint button glows).
* Correct, no hint, at least 25% of the time left: **+1** (more objects, less time, longer/faster sequence).
* Otherwise: unchanged.

Every generated puzzle is checked by `LevelManager.is_solvable()` before it is shown.

### Endings

Based on overall accuracy when you clear Level 5: **The Awakening** (80% or more), **The Echo** (55-79%),
**The Loop** (below 55%).

## 4. Project files

```
MEMORIA/
    main.py                  the complete game
    requirements.txt         pygame-ce
    README.md                this file
    PROJECT_EXPLANATION.md   report text + viva questions
    memoria_save.db          created automatically on first run
```

## 5. Manual testing checklist

Tick each item while running `py main.py`.

**Start-up and menus**
- [ ] Game window opens (1000 x 650) with the MEMORIA title and floating particles.
- [ ] Continue Game with no save shows "No saved game found" and does not crash.
- [ ] How to Play opens and Back returns to the title screen.
- [ ] Exit closes the game. Closing with the window X also works.

**Profile and story**
- [ ] Create Profile with an empty name shows an error.
- [ ] Typing letters works, Backspace works, the name stops at 16 characters.
- [ ] Creating a profile opens the story; Continue opens Level Select.
- [ ] Entering an existing name warns first; a second click erases and restarts that profile.

**Level Select**
- [ ] Only Level 1 is unlocked on a new profile; clicking Level 2 shows "Locked".
- [ ] Completed levels show a green COMPLETED label and a best score.

**Level 1 - The Forgotten Room**
- [ ] 5 objects and a countdown (about 15 s) are shown. I'm Ready skips ahead.
- [ ] "The lights flicker..." appears, then 4 remaining objects and 3 choices.
- [ ] Submit stays disabled until a choice is selected.
- [ ] Correct answer turns the card green; a wrong answer shows red and highlights the right card.

**Level 2 - False Memories**
- [ ] 6 objects are shown; afterwards one is different and clicking it works.

**Level 3 - The Changing Room**
- [ ] Objects sit in a 4 x 2 grid with faint empty slots; after the flicker one object has moved.

**Level 4 - The Memory Sequence**
- [ ] Symbols light up one by one; clicking is ignored during playback.
- [ ] Clicked symbols appear in "Your sequence"; Clear and Backspace remove them.
- [ ] Submit is enabled only when the sequence is full; the feedback shows the correct order.

**Level 5 - The Final Reconstruction**
- [ ] Observe a room, answer three change questions (stages 1-3), then the lock sequence (stage 4).
- [ ] Continue appears after each stage; the result screen lists all four stages.
- [ ] With 3 or 4 correct the level is complete; with fewer, Retry is offered.

**Hints, timer, scoring**
- [ ] Hint disables a wrong card (or replays a sequence), costs 25 points, and can be used once per question.
- [ ] Letting the answer timer reach 0 marks the question as incorrect (no crash).
- [ ] Score never goes negative. Retrying and doing worse does not lower the total.
- [ ] After wrong answers the next puzzle is easier; after fast correct answers it gets harder.

**Results, dashboard, ending**
- [ ] Results show correct/incorrect, accuracy, score breakdown, and Next Level / Retry / Level Select / Main Menu.
- [ ] Dashboard shows total score, completed levels, accuracy and best performance.
- [ ] Clearing Level 5 and pressing See Ending shows an ending that matches your accuracy.

**Saving, loading, restarting**
- [ ] Close the game after clearing Level 1, reopen, press Continue Game: Level 2 is unlocked.
- [ ] Restart Game on the ending screen resets progress to Level 1 only.
- [ ] Deleting `memoria_save.db` and starting again works (the file is recreated).

## 6. Command to run

```
py main.py
```
