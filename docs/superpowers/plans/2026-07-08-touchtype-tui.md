# touchtype TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Textual-based TUI touch-typing trainer with edclub-style progressive lessons for two keyboard layouts (en_us, es_la) plus a code-file practice mode.

**Architecture:** Four layers with downward-only dependencies: Textual UI -> progression (JSON store) -> content (layout data + generated curriculum) -> pure typing engine. The engine and content layers are pure Python with no I/O and are built strict-TDD.

**Tech Stack:** Python >=3.12, Textual (only runtime dep), pytest + pytest-asyncio (dev), uv for env/packaging.

**Spec:** `docs/superpowers/specs/2026-07-08-touchtype-tui-design.md` — read it before starting.

## Global Constraints

- Package name `touchtype`, src layout (`src/touchtype/`).
- All code, comments, UI copy, docs: English. Neutral professional wording.
- Conventional commits only. NEVER add "Co-Authored-By" or any AI attribution.
- Strict TDD for `engine.py`, `curriculum.py`, `layouts/`, `progress.py`, code loader: write the failing test, see it fail, implement, see it pass, commit.
- Run everything through uv: `uv run pytest -q`, `uv run python -m touchtype`.
- Cursor model: cursor does NOT advance on wrong key; every wrong attempt counts against accuracy.
- Stars: 1★ complete · 2★ acc>=90 · 3★ acc>=95 · 4★ acc>=97 AND net_wpm>=target · 5★ acc>=99 AND net_wpm>=target (monotone ladder; 0 if incomplete).
- Progress JSON at `~/.touchtype/progress.json`, schema versioned, atomic writes, corrupt file -> back it up and start fresh (never crash).
- No network access at build or runtime. Wordlists are bundled text files.
- Windows is the primary target; paths via `pathlib`, no POSIX-only APIs.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `src/touchtype/__init__.py`, `src/touchtype/__main__.py`, `tests/__init__.py` (empty), `README.md`

**Steps:**

- [x] `uv init --package --name touchtype` style scaffold (or write pyproject by hand), then `uv add textual` and `uv add --dev pytest pytest-asyncio`.
- [x] `pyproject.toml` must contain: `requires-python = ">=3.12"`, project script `touchtype = "touchtype.__main__:main"`, and:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [x] `src/touchtype/__init__.py`: `__version__ = "0.1.0"`.
- [x] `src/touchtype/__main__.py` minimal `main()` with argparse: `--version` prints `touchtype 0.1.0` and exits 0; no args prints `touchtype: TUI launch comes in a later task` for now (replaced in Task 6); subcommand `practice <path>` parsed but same placeholder message (replaced in Task 8).
- [x] Verify: `uv run python -m touchtype --version` -> `touchtype 0.1.0`; `uv run pytest -q` -> "no tests ran" is acceptable here.
- [x] Commit: `chore: scaffold touchtype package with uv`

### Task 2: Typing engine (pure, strict TDD)

**Files:**
- Create: `src/touchtype/engine.py`
- Test: `tests/test_engine.py`

**Interfaces (later tasks rely on these exact names):**

```python
class TypingSession:
    def __init__(self, target: str, clock: Callable[[], float] = time.monotonic): ...
    def on_key(self, char: str) -> bool      # True if char matched expected and cursor advanced
    def on_backspace(self) -> None           # step back one position if position > 0
    position: int                            # property, index of next expected char
    expected: str | None                     # property, target[position] or None when complete
    is_complete: bool                        # property
    elapsed: float                           # property, seconds since first keystroke; 0.0 before it
    gross_wpm: float                         # (total keystrokes / 5) / minutes; 0.0 if elapsed == 0
    net_wpm: float                           # (position / 5) / minutes; 0.0 if elapsed == 0
    accuracy: float                          # correct keystrokes / total keystrokes * 100; 100.0 if none
    error_positions: dict[int, int]          # target index -> wrong attempt count
    key_errors: dict[str, int]               # expected char -> wrong attempt count
    def stars(self, wpm_target: float) -> int
```

Semantics: `on_key("\n")` matches a newline target char. Backspace decrements position (the char must be retyped) and does not erase recorded errors. Clock is injected so tests control time: pass a fake `clock` callable returning controlled floats; `elapsed` = now - time of first `on_key`/`on_backspace` keystroke.

- [ ] **Write failing tests first** — cover at minimum:

```python
def make(target="fj fj", t=[0.0]):
    session = TypingSession(target, clock=lambda: t[0])
    return session, t

def test_correct_key_advances():
    s, _ = make("ab")
    assert s.on_key("a") is True
    assert s.position == 1 and s.expected == "b"

def test_wrong_key_does_not_advance_and_records_error():
    s, _ = make("ab")
    assert s.on_key("x") is False
    assert s.position == 0
    assert s.error_positions == {0: 1}
    assert s.key_errors == {"a": 1}

def test_completion_and_stars():
    s, t = make("ab")
    s.on_key("a"); t[0] = 6.0; s.on_key("b")
    assert s.is_complete
    # 2 chars in 6s -> net_wpm = (2/5)/(0.1min) = 4.0
    assert s.net_wpm == pytest.approx(4.0)
    assert s.accuracy == 100.0
    assert s.stars(wpm_target=4.0) == 5
    assert s.stars(wpm_target=99.0) == 3   # accuracy 100 but wpm target missed -> capped at 3
```

Plus: accuracy math with mixed wrong/right attempts; stars ladder at the 90/95/97/99 boundaries (parametrize); `stars()` returns 0 when incomplete; backspace at 0 is a no-op; backspace after a correct char requires retyping it; newline handling; `elapsed == 0.0` and wpm 0.0 before first key; extra `on_key` after completion is ignored (returns False, no metric change).

- [x] Run `uv run pytest tests/test_engine.py -q` -> all FAIL (module missing).
- [x] Implement `engine.py` minimally to pass. Timer starts on the first keystroke event. Guard divisions by zero.
- [x] `uv run pytest -q` -> PASS.
- [x] Commit: `feat: add pure typing engine with edclub cursor model and star rating`

### Task 3: Layout data (en_us, es_la)

**Files:**
- Create: `src/touchtype/layouts/__init__.py`, `src/touchtype/layouts/en_us.py`, `src/touchtype/layouts/es_la.py`
- Test: `tests/test_layouts.py`

**Interfaces:**

```python
Modifier = Literal["none", "shift", "altgr", "dead"]

@dataclass(frozen=True)
class KeyInfo:
    row: int          # 0=number row, 1=top, 2=home, 3=bottom, 4=space row
    col: int
    finger: str       # "left pinky" | "left ring" | "left middle" | "left index"
                      # | "right index" | "right middle" | "right ring" | "right pinky" | "thumb"
    modifier: Modifier
    hint: str = ""    # extra hint for dead-key chars, e.g. "´ then a"

@dataclass(frozen=True)
class Layout:
    id: str                      # "en_us" | "es_la"
    name: str                    # "English (US)" | "Español (Latinoamérica)"
    rows: list[list[str]]        # display caps per physical row (base char per key)
    char_map: dict[str, KeyInfo]
    key_order: list[tuple[str, str]]   # (unit title, new chars as a string)
    def typable(self, char: str) -> bool: ...   # char in char_map or char in (" ", "\n")

LAYOUTS: dict[str, Layout]       # {"en_us": EN_US, "es_la": ES_LA}
```

**Physical reference — en_us (base / shifted):**

```
row0: ` 1 2 3 4 5 6 7 8 9 0 - =        shifted: ~ ! @ # $ % ^ & * ( ) _ +
row1: q w e r t y u i o p [ ] \        shifted: Q W E R T Y U I O P { } |
row2: a s d f g h j k l ; '            shifted: A S D F G H J K L : "
row3: z x c v b n m , . /              shifted: Z X C V B N M < > ?
```

**Physical reference — es_la (base / shifted / AltGr):** transcribe the standard Latin American Spanish layout. Key facts to honor: home row is `a s d f g h j k l ñ`; `´` is a dead key (top row, right of `p`) producing `á é í ó ú` (shift gives `¨` -> `ü`); `@` is AltGr+q; `¿` and `¡` on the number row area; `{ } [ ]` via AltGr on the keys right of `ñ` and `´`; `< >` on the key left of `z`; `?` is shift+`'` area, `/` is shift+7, `( )` shift+8/9, `=` shift+0. Cross-check against your knowledge of the standard es-LA layout and keep it internally consistent; perfection is not required for v1 but home row, letters, ñ, accents, and digits must be right. Dead-key chars get `modifier="dead"` and `hint="´ then a"` style hints, positioned at the vowel's key for finger data.

**Curriculum key order — en_us (exact):**

```python
KEY_ORDER_EN = [
    ("Home row: F & J", "fj"), ("Home row: D & K", "dk"), ("Home row: S & L", "sl"),
    ("Home row: A & ;", "a;"), ("Center: G & H", "gh"), ("Top row: E & I", "ei"),
    ("Top row: R & U", "ru"), ("Top row: T & Y", "ty"), ("Top row: W & O", "wo"),
    ("Top row: Q & P", "qp"), ("Bottom: V & M", "vm"), ("Bottom: B & N", "bn"),
    ("Bottom: C & ,", "c,"), ("Bottom: X & .", "x."), ("Bottom: Z & /", "z/"),
    ("Capitals (Shift)", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("Punctuation", "'\"!?"), ("Numbers", "0123456789"),
    ("Symbols", "@#$%^&*()"), ("Code symbols I", "-_=+[]{}"),
    ("Code symbols II", "<>:\\|~`"),
]
```

**Curriculum key order — es_la (exact):**

```python
KEY_ORDER_ES = [
    ("Fila base: F y J", "fj"), ("Fila base: D y K", "dk"), ("Fila base: S y L", "sl"),
    ("Fila base: A y Ñ", "añ"), ("Centro: G y H", "gh"), ("Fila superior: E e I", "ei"),
    ("Fila superior: R y U", "ru"), ("Fila superior: T e Y", "ty"), ("Fila superior: W y O", "wo"),
    ("Fila superior: Q y P", "qp"), ("Fila inferior: V y M", "vm"), ("Fila inferior: B y N", "bn"),
    ("Fila inferior: C y ,", "c,"), ("Fila inferior: X y .", "x."), ("Fila inferior: Z y -", "z-"),
    ("Mayúsculas (Shift)", "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"),
    ("Acentos y diéresis", "áéíóúü"), ("Puntuación", "'?!¿¡"), ("Números", "0123456789"),
    ("Símbolos", "\"#$%&/()="), ("Símbolos de código I", "+*{}[]"),
    ("Símbolos de código II", "<>|~^@_"),
]
```

(Unit titles for es_la are Spanish because they are curriculum CONTENT for Spanish-layout learners, not UI chrome — UI chrome stays English.)

- [ ] Failing tests first: `LAYOUTS` has both ids; en_us `char_map["f"].finger == "left index"` and row/col of home keys; es_la home row list equals `["a","s","d","f","g","h","j","k","l","ñ"]`; `char_map["{"].modifier` is `"shift"` in en_us and `"altgr"` in es_la; `char_map["á"].modifier == "dead"` in es_la; every char used in every `key_order` entry is `typable()`; no char appears in two different `key_order` entries of the same layout; uppercase letters resolve to the base key with `modifier="shift"`.
- [ ] Red -> implement -> green.
- [ ] Commit: `feat: add en_us and es_la keyboard layout data`

### Task 4: Curriculum generator + wordlists

**Files:**
- Create: `src/touchtype/curriculum.py`, `src/touchtype/wordlists/en.txt`, `src/touchtype/wordlists/es.txt`
- Test: `tests/test_curriculum.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class Exercise:
    text: str

@dataclass(frozen=True)
class Unit:
    id: str                      # "en_us-01", "es_la-review-05", ...
    title: str
    kind: Literal["lesson", "review", "speedtest"]
    new_chars: str
    wpm_target: float
    exercises: tuple[Exercise, ...]

def load_wordlist(layout_id: str) -> list[str]      # reads bundled txt via importlib.resources
def build_curriculum(layout: Layout, words: list[str]) -> list[Unit]
```

**Rules (exact):**

- Wordlists: ~300 lowercase common words per language, one per line, bundled via `importlib.resources`. `es.txt` MUST include a healthy share of words with `ñ` and accented vowels (año, señor, café, música, día...). Write them inline in this task — no network.
- One lesson Unit per `key_order` entry, in order. After every 5th lesson insert a `review` unit (all chars learned so far). Append one final `speedtest` unit after all lessons.
- `wpm_target`: linear ramp from 10.0 (first unit) to 40.0 (last unit), rounded to 1 decimal, computed over the full unit list.
- Deterministic: all randomness from `random.Random(f"{layout.id}:{unit_index}:{exercise_index}")`.
- Lesson exercises (3-5 per unit, each 40-120 chars):
  1. Drill on the new chars with spaces, patterns like `fff jjj fjf jfj` built by seeded sampling.
  2. Drill mixing new chars with the learned pool (weighted ~60% new).
  3. Words: sample wordlist words whose chars are all in the learned pool; if fewer than 5 such words exist, generate pseudo-words (3-5 chars seeded from the pool, vowel-ish alternation when vowels are available).
  4. (only if pool has >=12 distinct letters) Longer word stream ~100 chars.
  For the Capitals unit, capitalize word initials; for Punctuation/Numbers/Symbols/Code units, interleave words with the new tokens (e.g. `word (word) [word]`, `12 34 word 56`).
- Review exercises: 4 word-stream exercises over the full learned pool.
- Speedtest: 1 exercise, ~200 chars of words over the full alphabet pool.
- Every exercise char must satisfy `layout.typable()` — filter or regenerate otherwise. No leading/trailing spaces, no double spaces, no newlines inside lesson exercises.

- [ ] Failing tests first: determinism (two builds are equal); first en_us unit exercises only contain chars from `"fj "`; unit count == len(key_order) + reviews + 1; wpm targets ramp monotonically from 10 to 40; all chars of all exercises typable; review appears after each 5th lesson; es_la word exercises eventually include `ñ` words once ñ is learned (build full curriculum, scan a review unit late in the list).
- [ ] Red -> implement -> green.
- [ ] Commit: `feat: add deterministic layout-aware curriculum generator with bundled wordlists`

### Task 5: Progress store

**Files:**
- Create: `src/touchtype/progress.py`
- Test: `tests/test_progress.py`

**Interfaces:**

```python
class ProgressStore:
    def __init__(self, path: Path | None = None):    # default: Path.home()/".touchtype"/"progress.json"
        ...                                           # loads immediately; missing/corrupt -> fresh state
    @property
    def active_layout(self) -> str | None: ...
    def set_active_layout(self, layout_id: str) -> None:          # persists
    def record(self, layout_id: str, unit_id: str, stars: int,
               wpm: float, accuracy: float, key_errors: dict[str, int]) -> None
        # keeps per-unit BEST stars/wpm/accuracy, accumulates key_errors; persists atomically
    def stars_for(self, layout_id: str, unit_id: str) -> int      # 0 when unseen
    def is_unlocked(self, layout_id: str, unit_index: int, units: list[Unit]) -> bool
        # index 0 always True; else stars_for(previous unit) >= 2
    def key_errors(self, layout_id: str) -> dict[str, int]
```

Schema exactly as in the spec (`version: 1`). Atomic write: write `progress.json.tmp` then `os.replace`. Corrupt JSON: rename existing file to `progress.json.bak` and start fresh.

- [ ] Failing tests first (use `tmp_path`): fresh store defaults; record + reload round-trip; best-keeping (lower later score does not overwrite stars/wpm bests, key_errors still accumulate); unlock logic (0 unlocked, 1 locked until unit 0 has >=2 stars); corrupt file -> `.bak` created and store usable; atomic tmp file not left behind.
- [ ] Red -> implement -> green.
- [ ] Commit: `feat: add JSON progress store with star unlocking and atomic writes`

### Task 6: Textual app shell — layout select + lesson map

**Files:**
- Create: `src/touchtype/app.py`, `src/touchtype/screens/__init__.py`, `src/touchtype/screens/layout_select.py`, `src/touchtype/screens/lesson_map.py`, `src/touchtype/styles.tcss`
- Modify: `src/touchtype/__main__.py` (launch the app for the no-arg case)
- Test: `tests/test_app.py`

**Interfaces:**

```python
class TouchTypeApp(App):
    def __init__(self, progress_path: Path | None = None, practice_file: Path | None = None): ...
```

- `TouchTypeApp` builds `LAYOUTS`, a `ProgressStore(progress_path)`, and per-layout curricula lazily.
- On mount: if `practice_file` -> go straight to code practice (Task 8); elif `store.active_layout` is None -> `LayoutSelectScreen`; else -> `LessonMapScreen`.
- `LayoutSelectScreen`: an `OptionList` with the two layout names; selecting sets active layout and pushes the lesson map. Reachable later from the map with key `l`.
- `LessonMapScreen`: `OptionList` (or `ListView`) of units — each row shows lock state, stars as `★`/`☆` (5 slots), title, best WPM. Locked rows are disabled. `enter` opens `PracticeScreen` (Task 7 — until then, a no-op with a footer note is fine for this task's tests). Footer bindings: `q` quit, `l` change layout, `p` practice a file (Task 8).
- `styles.tcss`: minimal, dark-friendly; keep it small.
- `__main__.py`: no-arg case now runs `TouchTypeApp().run()`.

- [ ] Failing Pilot test first:

```python
async def test_first_run_shows_layout_select_then_map(tmp_path):
    app = TouchTypeApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        assert app.screen.__class__.__name__ == "LayoutSelectScreen"
        await pilot.press("enter")            # pick first option (English US)
        await pilot.pause()
        assert app.screen.__class__.__name__ == "LessonMapScreen"
```

Plus: second run (store with active_layout preset) goes straight to the map; unit 1 is enabled, unit 2 disabled with a fresh store.
- [ ] Red -> implement -> green (`uv run pytest -q`).
- [ ] Commit: `feat: add Textual app shell with layout select and lesson map screens`

### Task 7: Practice + results screens (the core loop)

**Files:**
- Create: `src/touchtype/screens/practice.py`, `src/touchtype/screens/results.py`, `src/touchtype/widgets.py` (KeyboardWidget)
- Modify: `src/touchtype/screens/lesson_map.py` (open practice on enter)
- Test: `tests/test_practice_flow.py`

**Behavior:**

- `PracticeScreen(unit: Unit, exercise_index: int, layout: Layout, store: ProgressStore)` creates a `TypingSession(exercise.text)`.
- Rendering (a `Static` updated on every keystroke): typed part green, cursor char reversed (red-reversed right after a wrong attempt), rest dim. Header shows unit title + `exercise i/n`; a stats bar shows live `WPM` (net) and `ACC %` refreshed via `set_interval(0.5, ...)` while running.
- `KeyboardWidget(layout)` renders `layout.rows` as key caps; `highlight(char)` marks the cap for `char_map[char]` and shows a hint line: finger name plus `Shift + X` / `AltGr + X` / `´ then a` when the modifier is not `"none"`.
- Input: `on_key(event)` — printable single chars -> `session.on_key(event.character)`; `enter` -> `session.on_key("\n")`; `backspace` -> `session.on_backspace()`; `escape` -> back to map. Consume events so bindings don't fire while typing (`event.stop()`; keep `escape` working).
- On exercise completion: if more exercises remain, advance within the unit (running stats reset per exercise; unit result aggregates: mean accuracy, mean net wpm, min stars across exercises). After the last exercise: `store.record(...)` with the aggregate and the union of key_errors, then push `ResultsScreen`.
- `ResultsScreen(unit, stars, wpm, accuracy, worst_keys)` shows `★★★☆☆`, WPM, ACC, top-3 error keys; bindings: `r` retry unit, `enter` back to map (map refreshes lock/star states).

- [ ] Failing Pilot test first — full happy path:

```python
async def test_type_through_first_exercise_earns_stars(tmp_path):
    app = TouchTypeApp(progress_path=tmp_path / "p.json")
    async with app.run_test() as pilot:
        await pilot.press("enter")                    # layout select -> en_us
        await pilot.pause()
        await pilot.press("enter")                    # open unit 1
        await pilot.pause()
        unit = app.current_unit                       # expose for tests
        for ch in unit.exercises[0].text:
            await pilot.press("enter" if ch == "\n" else ch)
        # ... advance through remaining exercises the same way ...
        # after last exercise:
        assert app.screen.__class__.__name__ == "ResultsScreen"
        assert app.store.stars_for("en_us", unit.id) >= 1
```

(Space is pressed as `"space"` in Pilot — map chars: `" "` -> `"space"`.) Also test: wrong key does not advance (press a wrong char, screen still expects same char); escape returns to map without recording.
- [ ] Red -> implement -> green.
- [ ] Commit: `feat: add practice loop with live stats, on-screen keyboard and results`

### Task 8: Code-file practice mode

**Files:**
- Create: `src/touchtype/codeload.py`, `src/touchtype/screens/file_picker.py`
- Modify: `src/touchtype/__main__.py` (wire `practice <path>`), `src/touchtype/app.py` (practice_file flow), `src/touchtype/screens/lesson_map.py` (`p` opens picker)
- Test: `tests/test_codeload.py`

**Interfaces:**

```python
def load_code_exercises(path: Path) -> tuple[list[Exercise], list[str]]:
    # returns (exercises, notices)
```

**Rules (exact):**

- Read utf-8; on `UnicodeDecodeError` retry latin-1 and add notice `"decoded as latin-1"`.
- `expandtabs(4)`, strip trailing whitespace per line, drop leading whitespace per line (`lstrip()` — editors handle indentation), skip lines that become empty.
- Cap at 2000 lines with notice `"truncated to first 2000 lines"`.
- Remove chars not in the ACTIVE layout... code practice is layout-independent in v1: filter against the `en_us` char_map ∪ `es_la` char_map is wrong — instead accept printable ASCII plus the active layout's extras; simplest correct rule: keep chars where `layout.typable(ch)` for the active layout, collect removed chars into one notice `"skipped untypable: <sorted unique chars>"`. Pass the active layout into `load_code_exercises(path, layout)` — adjust the signature accordingly.
- Chunk into exercises of 10 processed lines joined with `"\n"`.
- `FilePickerScreen`: Textual `DirectoryTree` over cwd; selecting a file loads exercises and opens `PracticeScreen` with a synthetic `Unit(kind="lesson", id=f"code:{path.name}", wpm_target=30.0, ...)`; code results are shown but NOT recorded to lesson progress (record only key_errors).
- `touchtype practice <path>`: app opens directly into the first code exercise (layout: active or en_us fallback without prompting).

- [ ] Failing tests first for every rule above (tmp files; include a latin-1 file, a tabbed+indented Python sample, an 8-line file -> 1 exercise, a 25-line file -> 3 exercises).
- [ ] Red -> implement -> green. Manual check: `uv run python -m touchtype practice src/touchtype/engine.py` boots into typing.
- [ ] Commit: `feat: add code-file practice mode with CLI entry and file picker`

### Task 9: Final wiring, README, full verification

**Files:**
- Modify: `README.md`

**Steps:**

- [ ] README: what it is, install (`uv sync`), run (`uv run touchtype`), practice a file, run tests, progress file location, both layouts note. Short.
- [ ] Full suite: `uv run pytest -q` -> ALL PASS.
- [ ] `uv run python -m touchtype --version` -> `touchtype 0.1.0`; `uv run touchtype --help` works (console script).
- [ ] Commit: `docs: add README with usage instructions`

## Self-Review (done at plan time)

Spec coverage: engine/cursor/stars (T2), layouts both (T3), curriculum+wordlists+reviews+speedtest (T4), progress+unlock+atomic (T5), screens map/select (T6), practice/results/keyboard/finger hints (T7), code mode+CLI+picker+encoding/truncate/indent rules (T8), README/DoD (T9). Types cross-checked: `Unit.exercises` is a tuple; `load_code_exercises(path, layout)` final signature is the two-arg form noted in Task 8. No placeholders: es_la physical transcription is delegated to the implementer's layout knowledge with hard invariants tested (home row, ñ, dead keys, AltGr braces) — deliberate, tested-around choice, not an omission.
