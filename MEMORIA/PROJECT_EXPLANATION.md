# MEMORIA - Project Explanation

**Project:** MEMORIA - The Game That Forgets You
**Academic title:** Development of an Adaptive Memory-Based Psychological Puzzle Game Using Python
**Technologies:** Python 3, pygame-ce, SQLite (`sqlite3`), `random`, `math`

---

## 1. Abstract

MEMORIA is a 2D desktop puzzle game that trains and tests short-term visual memory inside a dark,
psychological-mystery story. The player explores five rooms in which objects vanish, are replaced, move
position, or flash in a sequence. A simple rule-based system adjusts the difficulty after every question
using the player's correctness, speed and hint usage. Progress, scores and accuracy are stored in a local
SQLite database so the player can continue later. All graphics are drawn in code, so the game runs offline
from a single Python file. The adaptive system is intentionally transparent and does not use machine learning.

## 2. Problem statement

Many memory games are either fixed in difficulty (too easy for some players, too hard for others) or are
plain quizzes with little game feel. There is a need for a small, complete, understandable game that
(a) is genuinely interactive, (b) adapts to the player with an explainable algorithm, and (c) saves
progress, to demonstrate core Python, OOP, event-driven programming and database skills.

## 3. Objectives

1. Build a complete, playable 2D game with a beginning, five levels and an ending.
2. Implement five different memory mechanics: missing object, replaced object, moved object, sequence recall and a combined final challenge.
3. Implement simple, explainable adaptive difficulty.
4. Implement scoring (correct points, time bonus, hint penalty, completion bonus) with no negative scores.
5. Save and load progress with SQLite.
6. Use beginner-friendly object-oriented design and a stable 60 FPS game loop.
7. Create all visuals with Pygame drawing functions (no external assets).

## 4. Proposed system

The system is a single-file Pygame application organised as a **state machine**. Each screen is a state:
`splash`, `how_to`, `profile`, `story`, `level_select`, `play`, `result`, `ending`, `dashboard`.
The `Game` class owns the window and the main loop. Each loop iteration reads events, updates timers using
delta time, and draws the current screen. Puzzles are produced by `LevelManager`, progress is held by
`Player`, and `DatabaseManager` stores it.

## 5. Technologies used

| Technology | Purpose |
|-----------|---------|
| Python 3.14 | Programming language |
| pygame-ce 2.5.x | Window, drawing, events, clock (imported as `pygame`) |
| sqlite3 | Local save database (standard library) |
| random | Choosing objects, positions, sequences |
| math | Circles, angles, animation (sine waves), distance checks |
| datetime | Time stamp for "last played" |
| os, sys | File path for the database, clean exit |

## 6. Module (class) descriptions

| Class / group | Responsibility |
|---------------|----------------|
| Drawing helpers | `draw_object_icon` (12 custom-drawn objects), `draw_symbol` (6 shapes), `draw_card`, `draw_pad`, glow, text wrapping |
| `Button` | Rectangle, label and callback. The same `rect` is used for drawing and click detection, so they always match. Optional `enabled_check` / `visible_check` functions make buttons react to game state. |
| `Player` | Name, unlocked level, difficulty value, per-level records (completed, best score, attempts), totals, accuracy |
| `DatabaseManager` | Creates the database, creates/loads/saves players. Falls back to memory if the file cannot be used. |
| `LevelManager` | Builds the puzzle for each level, holds the adaptive rules and the `is_solvable()` check |
| `Game` | Main loop, state switching, input, gameplay phases, scoring, all screen drawing |

### The five levels

1. **The Forgotten Room** - 5 objects, 15 s to observe, one removed, pick it from 3 choices. Wrong choices are objects that were never shown, so the answer needs real recall.
2. **False Memories** - 6 objects, one replaced by an object that was not in the room. The player clicks the intruder; the explanation names the original object that was replaced.
3. **The Changing Room** - objects stand in a 4 x 2 grid. One object moves into an empty slot. The player clicks the moved object.
4. **The Memory Sequence** - 4 symbols flash on pads; the player repeats them in order (Submit / Clear / Backspace).
5. **The Final Reconstruction** - one room with three changes (vanish, replace, move) answered as stages 1-3, then an escape-lock sequence as stage 4. Passing needs 3 of 4 stages.

### Game phases inside a level

`observe` (countdown or sequence playback) -> `blackout` (1.4 s flicker) -> `answer` (timer, hint, submit) -> `feedback` (shows right answer) -> next question or result.

## 7. Adaptive difficulty algorithm

A hidden integer called the **difficulty offset** ranges from **-1 to +2**.

```
after every answered question:
    if answer was wrong or time ran out:           offset = offset - 1
    elif no hint used AND time left >= 25%:        offset = offset + 1
    else:                                          offset unchanged
    offset = clamp(offset, -1, +2)
```

The offset is looked up in simple tables when the next puzzle is built:

| Setting | -1 Gentle | 0 Normal | +1 Challenging | +2 Intense |
|---------|-----------|----------|----------------|------------|
| Observation time (s) | 20 | 15 | 13 | 11 |
| Answer time (s) | 26 | 20 | 18 | 16 |
| Level 1 objects | 4 | 5 | 6 | 7 |
| Level 2 objects | 5 | 6 | 7 | 8 |
| Level 3 objects | 4 | 5 | 6 | 6 |
| Level 5 objects | 5 | 6 | 6 | 7 |
| Sequence length | 3 | 4 | 5 | 6 |
| Number of pads | 4 | 5 | 6 | 6 |
| Pad on / gap time (s) | 0.9 / 0.30 | 0.7 / 0.25 | 0.6 / 0.22 | 0.5 / 0.20 |

When the offset is negative the Hint button pulses gold and extra help text appears.

**Why it is always solvable:** object counts never exceed the 12 available objects or 8 grid slots, sequences are 3-6 long on 4-6 pads, timers are always positive, and every puzzle passes `is_solvable()` (right answer present, choices unique, answer slot exists, distractors not on screen). A failing puzzle is regenerated automatically.

**Explainable in a viva:** it is a rule table (if-else plus lookup), not machine learning. The player's current difficulty is shown on screen and the result screen states whether it changed.

## 8. System workflow

```
Splash -- Start Game --> Profile --> Story --> Level Select <-----------------+
   |                                              |  ^                         |
   |-- Continue Game (loads latest save) ---------+  |                         |
   |-- How to Play (back)                           v  |                         |
   |-- Exit                       Play: observe -> blackout -> answer -> feedback
                                                   |                            |
                                              Result screen --Retry/Next--------+
                                                   | (Level 5 passed)
                                                   v
                                                Ending <-> Dashboard
                                                   | Restart Game (resets progress)
                                                   v
                                              Level Select
```

Main loop (60 FPS): `dt = clock.tick(60)/1000` (capped at 0.1 s) -> handle events -> `update(dt)` -> `draw()` -> `display.flip()`.

## 9. Database description

File `memoria_save.db`, created automatically next to `main.py`.

**players**

| Column | Type | Meaning |
|--------|------|---------|
| id | INTEGER PRIMARY KEY | Player id |
| name | TEXT UNIQUE (case-insensitive) | Player name |
| unlocked_level | INTEGER | Highest unlocked level (1-5) |
| difficulty_offset | INTEGER | Current adaptive value (-1..2) |
| total_correct / total_questions | INTEGER | For accuracy |
| best_score | INTEGER | Best single-level score |
| overall_score | INTEGER | Sum of best scores |
| last_played | TEXT | ISO time stamp (Continue loads the newest) |

**level_progress** - `player_id`, `level_number` (together the primary key), `completed`, `best_score`, `attempts`. A foreign key links it to `players`.

All SQL uses `?` parameters (no string-built queries). Loaded values are clamped and repaired (for example, a completed level always unlocks the next one). If the file is missing it is created; if it is damaged or read-only the game switches to an in-memory database and shows a warning instead of crashing.

## 10. Testing checklist

The full tick-list is in `README.md` (section 5). Summary of what must be verified:

* Every button on every screen works and every screen can be left.
* Name validation (empty, long, invalid characters, duplicate name).
* All five levels can be started, played, failed and completed.
* Timer expiry, hint use and retries behave correctly; scores never go negative.
* Progressive unlocking, Continue Game, Restart Game, window X and Exit.
* Ending text matches accuracy (80% or more, 55-79%, below 55%).

## 11. Expected output

A 1000 x 650 window with a deep purple/black theme and drifting particles. The title letters pulse and one letter occasionally "forgets" itself. Gameplay shows illustrated object cards, a countdown strip, score, hint and submit buttons. The result screen lists answers, a score breakdown, accuracy and the difficulty change. After Level 5 an ending screen appears and the dashboard summarises total score, completed levels, accuracy and best performance.

## 12. Limitations

* Difficulty rules are simple and fixed; they do not learn from the player over time.
* Single player, local save only; no sound.
* Object icons are simple shapes, not detailed art.
* The window size is fixed at 1000 x 650.
* Accuracy-only endings (three variants).
* Leaving a level with Menu or Esc abandons that attempt.

## 13. Future enhancements

* Sound effects and ambient music.
* More levels and more object types, difficulty modes, a timed "endless" mode.
* Per-player statistics charts and a leaderboard.
* Real data-driven adaptation (for example a model trained on logged sessions), clearly labelled as such.
* Colour-blind palettes, resizable window, gamepad support.

## 14. Conclusion

MEMORIA is a compact but complete game that demonstrates the event loop, state machines, object-oriented design, rule-based adaptation, scoring logic and SQLite persistence in one readable Python file. Because the adaptive logic is transparent, it can be explained and defended in an academic viva.

---

## 15. Twenty MCA viva questions

1. **What is pygame-ce and how is it different from pygame?**
   A community-maintained fork of pygame with more features and faster updates. It is imported with the same `import pygame`, but you install it with `pip install pygame-ce` (not both).

2. **What is a game loop?**
   A loop that repeats about 60 times a second: handle events, update the game state, draw the screen.

3. **What is delta time and why use it?**
   The seconds since the last frame (`dt`). Timers subtract `dt`, so a countdown lasts the same real time on slow or fast computers. It is capped at 0.1 s so a freeze cannot make timers jump.

4. **How is the frame rate limited?**
   `clock.tick(60)` pauses the loop so it runs at most 60 frames per second.

5. **What is a state machine and where is it used?**
   A program that is always in exactly one state and moves between states on events. MEMORIA's screens (`splash`, `play`, `result`, ...) and the phases inside a level (`observe`, `blackout`, `answer`, `feedback`) are states.

6. **Explain the adaptive difficulty algorithm.**
   A number from -1 to +2 goes down after a wrong answer, goes up after a fast correct answer without a hint, and is otherwise unchanged. Lookup tables turn it into object counts and time limits.

7. **Is this machine learning?**
   No. It is rule-based (if/else and tables). It adapts, but it does not learn from data.

8. **How do you make sure a puzzle is solvable?**
   Counts stay inside the available objects and slots, and `is_solvable()` checks the correct answer exists, options are unique and distractors are not on screen. Bad puzzles are regenerated.

9. **How is the score calculated?**
   100 per correct answer + up to 50 time bonus - 25 per hint + 100 for passing, with a minimum of 0.

10. **How are negative scores prevented?**
    The level score is `max(0, ...)`, and the live attempt score is also clamped at 0.

11. **How do you avoid counting retries incorrectly?**
    Total score is the sum of the best score of each level, so retries never add up. Each question is registered once when it is answered.

12. **Why SQLite?**
    It is part of Python, needs no server, stores data in one file, and supports SQL, primary keys and foreign keys.

13. **What are your tables and keys?**
    `players` (primary key `id`, unique `name`) and `level_progress` (composite primary key `player_id` + `level_number`, foreign key to `players`).

14. **Why use `?` placeholders in SQL?**
    They are parameterised queries. They stop SQL injection and handle quotes in names safely.

15. **How does Continue Game work?**
    It finds the player with the newest `last_played`, loads the row and level records, and opens Level Select with the saved unlocks and scores.

16. **How does the Button class ensure clicks match the drawing?**
    Each button has one `pygame.Rect`. The draw function and `rect.collidepoint(mouse_pos)` both use that same rectangle.

17. **How are the graphics made without image files?**
    Using `pygame.draw` functions (rectangles, circles, polygons, arcs, lines) combined in `draw_object_icon` and `draw_symbol`.

18. **How does the sequence level know the clicked symbol?**
    It measures the distance from the click to each pad centre with `math.hypot`; if it is less than the pad radius, that pad was clicked.

19. **What happens if the database file cannot be opened?**
    The `DatabaseManager` catches the error, switches to an in-memory database, and the title screen warns that progress will not be saved. The game keeps running.

20. **Why was everything placed in one file, and what is the trade-off?**
    The project requirement was a simple single-file structure that is easy to run and read. The trade-off is a long file; in a larger project the classes would be split into modules.
