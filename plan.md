# targetlint — Implementation Plan

## What it does
Pure Python CLI. Takes a C source file and a YAML target profile. Cross-references
code assumptions against target constraints using static pattern analysis (regex +
line scanning — no inference, no network). Outputs severity-ranked findings as
markdown and optionally HTML.

---

## File structure

```
targetlint/
├── targetlint/
│   ├── __init__.py
│   ├── cli.py
│   ├── loader.py
│   ├── analyser.py
│   └── rules/
│       ├── __init__.py
│       ├── memory.py
│       ├── stdlib.py
│       ├── timing.py
│       ├── hardware.py
│       └── safety.py
├── reporter.py
├── templates/
│   └── report.html.j2
├── targets/
│   ├── cortex-m0.yaml
│   ├── cortex-m4.yaml
│   └── linux-x86.yaml
├── examples/
│   └── sample.c
├── requirements.txt
├── setup.py
└── README.md
```

---

## What each file does

| File | Responsibility |
|---|---|
| `cli.py` | Parses CLI args, loads inputs, calls `analyser.run()`, writes output files |
| `loader.py` | Reads + validates C source file and YAML target profile; raises clear errors on schema violations |
| `analyser.py` | Iterates over all rule modules, collects findings, sorts by severity |
| `rules/__init__.py` | Exports `ALL_RULES` list — one `check` function per module |
| `rules/memory.py` | Checks for heap use, stack depth assumptions, pointer-size assumptions |
| `rules/stdlib.py` | Checks for stdlib calls (`printf`, `sprintf`, `malloc`, `free`, etc.) |
| `rules/timing.py` | Checks for hardcoded busy-wait loops and clock-cycle assumptions |
| `rules/hardware.py` | Checks for float/double arithmetic (FPU assumption), SIMD intrinsics |
| `rules/safety.py` | Checks for missing watchdog resets, unchecked return values in safety-critical context |
| `reporter.py` | Renders findings to Markdown string and optionally HTML via Jinja2 |
| `templates/report.html.j2` | Self-contained HTML template — inlined CSS, severity badge colours, no external assets |
| `targets/cortex-m0.yaml` | Bundled profile: ARMv6-M, 32KB RAM, no heap, no stdlib, no FPU, 16MHz |
| `targets/cortex-m4.yaml` | Bundled profile: ARMv7E-M, 256KB RAM, no heap, no stdlib, FPU, 120MHz |
| `targets/linux-x86.yaml` | Bundled profile: x86-64, large RAM, heap, full stdlib, no FPU constraint |
| `examples/sample.c` | C file containing patterns that trip all five rule modules — used for smoke testing |

---

## Target profile schema (YAML)

```yaml
arch: string           # e.g. "cortex-m0", "x86-64"
ram_bytes: int         # total RAM in bytes
stack_bytes: int       # max safe stack depth in bytes
has_heap: bool         # true if malloc/free are available
has_stdlib: bool       # true if libc is available
has_fpu: bool          # true if hardware FPU is present
clock_hz: int          # CPU clock in Hz
watchdog_timeout_ms: int | null   # null means no watchdog
word_size_bits: int    # native word size (32 or 64)
safety_critical: bool  # true triggers stricter safety checks
```

---

## Rules modules

Each rule module exports exactly one function:

```python
def check(source_text: str, target: dict) -> list[dict]
```

The function returns an empty list if no violations are found for that target.

Each finding dict:

```python
{
    "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
    "rule": str,           # short rule name, e.g. "heap-use"
    "location": str,       # "line 42" or "global"
    "assumption": str,     # what the code assumes
    "conflict": str,       # what the target says / why it's a problem
    "recommendation": str  # what the developer should do
}
```

### Rule module responsibilities

| Module | What it checks |
|---|---|
| `memory.py` | `malloc`/`calloc`/`realloc`/`free` calls when `has_heap: false`; `alloca` or deeply-nested recursion when `stack_bytes` is small; pointer cast to `int` when `word_size_bits` != 32 |
| `stdlib.py` | `printf`/`sprintf`/`fprintf`/`scanf` family when `has_stdlib: false`; `<string.h>`, `<math.h>` includes when `has_stdlib: false` |
| `timing.py` | Busy-wait loops with hardcoded integer counts (potential clock-speed assumption); `usleep`/`sleep` calls on bare-metal targets |
| `hardware.py` | `float`/`double` variable declarations or arithmetic when `has_fpu: false`; compiler intrinsics for SIMD/NEON when target arch lacks them |
| `safety.py` | No watchdog kick pattern found in long loops when `watchdog_timeout_ms` is set; unchecked return values of critical calls when `safety_critical: true` |

---

## CLI interface

```
targetlint --source path/to/file.c \
           --target targets/cortex-m0.yaml \
           [--output report.md] \
           [--html]
```

| Flag | Default | Description |
|---|---|---|
| `--source` | required | Path to the C source file to analyse |
| `--target` | required | Path to a YAML target profile |
| `--output` | auto-named | Output path for the Markdown report. Auto-name: `<source-stem>-<target-stem>-report.md` |
| `--html` | false | If set, also write `<output-stem>.html` alongside the Markdown |

---

## Output format

### Markdown report

```markdown
# targetlint Report

**Source:** examples/sample.c
**Target:** targets/cortex-m0.yaml
**Date:** 2024-01-15T10:30:00Z
**Findings:** 4 (1 critical, 2 high, 1 medium)

---

## Findings

### [CRITICAL] heap-use — malloc() called, target has no heap
**Location:** line 12
**Assumption:** Runtime provides malloc()
**Conflict:** cortex-m0 profile sets has_heap: false
**Recommendation:** Replace with a static buffer declared at file scope
```

### HTML report

Self-contained single file from `templates/report.html.j2`. All CSS inlined.
Severity badge colours: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue.
No JavaScript. No external URLs.

---

## Design decisions

- **No inference at runtime** — all checks are pure regex/line-scan. No API calls, no `requests`, no `BobClient`. Bob is used only as the development agent.
- **Allowed deps: `pyyaml`, `jinja2` only** — `requirements.txt` lists only these two.
- **`loader.py` validates schema** — raises `ValueError` with a clear message if any required YAML key is missing or the wrong type, before any rules run.
- **Severity sort order** — `analyser.py` sorts findings: CRITICAL → HIGH → MEDIUM → LOW.
- **`rules/__init__.py` auto-collects** — imports all five modules and exposes `ALL_RULES = [memory.check, stdlib.check, timing.check, hardware.check, safety.check]` so `analyser.py` never needs to name each module directly.
- **Jinja2 template path** — resolved with `os.path.join(os.path.dirname(__file__), 'templates')` inside `reporter.py` so the tool works regardless of working directory.
- **Auto-named output** — default output is `<source-stem>-<target-stem>-report.md` to prevent overwriting previous runs with different target profiles.
- **Branch:** all work on `feat/implement-targetlint`, never directly to `main`.

---

## Build order

1. Scaffold + requirements + setup.py + sample.c + target YAMLs
2. `loader.py`
3. `rules/` modules (all five)
4. `analyser.py`
5. `reporter.py` + template
6. `cli.py`
7. End-to-end test
8. README + cleanup

---

## Sub-Task 1 — Project scaffold

- **Status:** [ ] pending
- **Intent:** Establish the Python package skeleton so that all subsequent modules have
  a valid home and `pip install -e .` works from the start. Also write `examples/sample.c`
  and the three bundled target YAMLs now so they are a concrete reference throughout development.
- **Expected Outcomes:**
  - `targetlint/__init__.py` exists (empty)
  - `requirements.txt` contains only `pyyaml` and `jinja2`
  - `setup.py` declares `name="targetlint"` and `console_scripts = ["targetlint=targetlint.cli:main"]`
  - `examples/sample.c` contains patterns covering: `malloc` call, `printf` call, `float`
    arithmetic, busy-wait loop with hardcoded count, recursive function
  - `targets/cortex-m0.yaml`, `targets/cortex-m4.yaml`, `targets/linux-x86.yaml` all exist
    and conform to the target profile schema
  - `pip install -e .` completes without error
- **Todo List:**
  1. Create `targetlint/__init__.py` (empty)
  2. Create `targetlint/rules/__init__.py` (empty for now)
  3. Create `requirements.txt` with `pyyaml` and `jinja2`
  4. Create `setup.py` with `find_packages()` and the `targetlint` console script entry point
  5. Create `examples/sample.c` with the patterns listed above
  6. Create `targets/cortex-m0.yaml`, `targets/cortex-m4.yaml`, `targets/linux-x86.yaml`
  7. Run `pip install -e .` to verify the install succeeds
  8. Commit: `feat: scaffold package, requirements, target profiles, and examples/sample.c`
- **Relevant Context:** `setup.py` entry point must be `targetlint.cli:main`; `cli.py` is written in Sub-Task 6.

---

## Sub-Task 2 — `loader.py`

- **Status:** [ ] pending
- **Intent:** Centralise all file I/O and validation. By the time `analyser.py` receives its
  inputs, they are guaranteed to be correct types — no defensive coding needed downstream.
- **Expected Outcomes:**
  - `targetlint/loader.py` exists
  - `load_source(path)` reads the C file as UTF-8 and returns the text string; raises `FileNotFoundError` or `ValueError` with a clear message on failure
  - `load_target(path)` reads the YAML file, validates all required keys are present and
    the correct types, and returns the dict; raises `ValueError` listing any missing/wrong keys
  - Smoke test: `python -c "from targetlint.loader import load_target; print(load_target('targets/cortex-m0.yaml')['arch'])"` prints `cortex-m0`
- **Todo List:**
  1. Create `targetlint/loader.py`
  2. Implement `load_source(path: str) -> str`
  3. Define `REQUIRED_KEYS` dict mapping key name → expected Python type
  4. Implement `load_target(path: str) -> dict` — parse YAML, validate all keys, return dict
  5. Verify smoke test passes
  6. Commit: `feat(loader): add C source and YAML target profile loader with schema validation`
- **Relevant Context:** The 10 required YAML keys and their types are defined in the "Target profile schema" section above.

---

## Sub-Task 3 — `rules/` modules (all five)

- **Status:** [ ] pending
- **Intent:** Implement the five rule modules that perform the actual static analysis.
  Each is independent — they can be written and tested in isolation.
- **Expected Outcomes:**
  - `targetlint/rules/memory.py`, `stdlib.py`, `timing.py`, `hardware.py`, `safety.py` all exist
  - Each exports `check(source_text: str, target: dict) -> list[dict]`
  - Each returns an empty list when no violations apply
  - Each finding dict has all six required keys: `severity`, `rule`, `location`, `assumption`, `conflict`, `recommendation`
  - `targetlint/rules/__init__.py` exports `ALL_RULES = [memory.check, stdlib.check, timing.check, hardware.check, safety.check]`
  - Smoke test: running all five checks against `examples/sample.c` + `targets/cortex-m0.yaml`
    produces at least one finding from each of `memory`, `stdlib`, `hardware`
- **Todo List:**
  1. Implement `rules/memory.py` — detect `malloc`/`calloc`/`realloc`/`free` when `has_heap: false`; detect pointer-to-int cast when `word_size_bits != 32`
  2. Implement `rules/stdlib.py` — detect `printf`/`sprintf`/`fprintf`/`scanf` and `#include <string.h>` / `<math.h>` when `has_stdlib: false`
  3. Implement `rules/timing.py` — detect busy-wait loops with hardcoded integer counts; detect `usleep`/`sleep` on bare-metal (`has_stdlib: false`)
  4. Implement `rules/hardware.py` — detect `float`/`double` declarations or arithmetic when `has_fpu: false`
  5. Implement `rules/safety.py` — detect missing watchdog kick in loops when `watchdog_timeout_ms` is not null; detect unchecked return values of `memcpy`/`write`/`read` when `safety_critical: true`
  6. Update `rules/__init__.py` to export `ALL_RULES`
  7. Verify smoke test against `examples/sample.c` + `targets/cortex-m0.yaml`
  8. Commit: `feat(rules): implement all five rule modules and export ALL_RULES`
- **Relevant Context:** See "Rule module responsibilities" table above for the precise patterns each module checks.

---

## Sub-Task 4 — `analyser.py`

- **Status:** [ ] pending
- **Intent:** Provide the single entry point that runs all rule modules and returns a
  sorted finding list. Keeps orchestration logic out of `cli.py`.
- **Expected Outcomes:**
  - `targetlint/analyser.py` exists
  - Exports `run(source_text: str, target: dict) -> list[dict]`
  - Iterates `ALL_RULES`, calls each `check()`, concatenates results
  - Sorts findings: CRITICAL first, then HIGH, MEDIUM, LOW
  - Smoke test: `python -c "from targetlint import analyser, loader; print(len(analyser.run(loader.load_source('examples/sample.c'), loader.load_target('targets/cortex-m0.yaml'))))"` prints a number > 0
- **Todo List:**
  1. Create `targetlint/analyser.py`
  2. Import `ALL_RULES` from `rules`
  3. Define `SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}`
  4. Implement `run(source_text, target)` — call each rule, collect all findings, sort by severity, return
  5. Verify smoke test passes
  6. Commit: `feat(analyser): add rule orchestration with severity-ranked output`
- **Relevant Context:** `ALL_RULES` is exported from `targetlint/rules/__init__.py` (Sub-Task 3).

---

## Sub-Task 5 — `reporter.py` + `templates/report.html.j2`

- **Status:** [ ] pending
- **Intent:** Convert the structured findings list into human-readable output. All
  presentation logic lives here; `cli.py` only writes the returned strings to disk.
- **Expected Outcomes:**
  - `reporter.py` exists at the project root (not inside the `targetlint/` package)
  - Exports `render_markdown(findings, source_path, target_path) -> str`
  - Exports `render_html(findings, source_path, target_path) -> str`
  - `templates/report.html.j2` exists with inlined CSS and severity badge colours
  - No external CSS/JS URLs in the HTML template
  - Jinja2 loader resolves `templates/` relative to `reporter.py` using `__file__`
  - Smoke test: `render_markdown([{"severity":"CRITICAL","rule":"heap-use","location":"line 1","assumption":"x","conflict":"y","recommendation":"z"}], "a.c", "t.yaml")` returns a string containing `[CRITICAL]`
- **Todo List:**
  1. Create `reporter.py` at project root
  2. Implement `render_markdown` — header block with source/target/date/finding counts; one section per finding with severity tag
  3. Implement `render_html` — use `os.path.join(os.path.dirname(__file__), 'templates')` for Jinja2 `FileSystemLoader`
  4. Create `templates/report.html.j2` — full HTML document; inline `<style>` block; severity colours (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue); loop over findings
  5. Verify smoke test passes
  6. Commit: `feat(reporter): add markdown and HTML report rendering`
- **Relevant Context:** `reporter.py` sits at the project root; `templates/` is a sibling directory. The `__file__`-based path is required so the tool works when run from any directory.

---

## Sub-Task 6 — `cli.py`

- **Status:** [ ] pending
- **Intent:** Wire all components together into the `targetlint` command. This is the last
  module written because it depends on all the others being complete.
- **Expected Outcomes:**
  - `targetlint/cli.py` exists with a `main()` function
  - `targetlint --help` prints usage including all four flags
  - On valid invocation: loads source + target via `loader`, runs `analyser.run()`, writes output via `reporter`, prints a summary line
  - Default output filename is `<source-stem>-<target-stem>-report.md`
  - `targetlint --source examples/sample.c --target targets/cortex-m0.yaml` completes without error and writes a report file
- **Todo List:**
  1. Create `targetlint/cli.py`
  2. Build `argparse.ArgumentParser` with `--source`, `--target`, `--output` (default `None`), `--html` (store_true)
  3. Validate that `--source` and `--target` files exist; exit with clear error if not
  4. Call `loader.load_source()` and `loader.load_target()`
  5. If `--output` is not given, derive output path: `<source-stem>-<target-stem>-report.md`
  6. Call `analyser.run()`, then `reporter.render_markdown()`, write to output path
  7. If `--html`, replace `.md` with `.html`, call `reporter.render_html()`, write HTML file
  8. Print summary: `Wrote <output-path> (N findings: X critical, Y high, ...)`
  9. Verify `targetlint --help` works and the smoke invocation from Expected Outcomes succeeds
  10. Commit: `feat(cli): add argparse entry point wiring loader, analyser, and reporter`
- **Relevant Context:** `setup.py` already declares `targetlint.cli:main` as the console script (Sub-Task 1). `reporter.py` is at the project root — import it as a top-level module, not from the `targetlint` package.

---

## Sub-Task 7 — End-to-end test

- **Status:** [ ] pending
- **Intent:** Verify the complete tool works against a real C file and all three bundled
  target profiles. `examples/sample.c` is the test input.
- **Expected Outcomes:**
  - Running the command below completes without error for all three target profiles:
    ```
    targetlint --source examples/sample.c --target targets/cortex-m0.yaml --html
    targetlint --source examples/sample.c --target targets/cortex-m4.yaml --html
    targetlint --source examples/sample.c --target targets/linux-x86.yaml --html
    ```
  - Each produces a `.md` and `.html` file with at least one finding
  - The cortex-m0 run produces at least one CRITICAL or HIGH finding
  - No credentials, API calls, or network activity during any run
  - If any bugs are found, fix and commit with `fix(<module>): <description>`
- **Todo List:**
  1. Run all three invocations above; inspect output files
  2. Verify each markdown report contains a `## Findings` section with populated findings
  3. Verify each HTML file is valid and contains severity badges
  4. Fix any bugs found; commit each fix individually
  5. Commit (if no bugs): `test: verify end-to-end runs against all three bundled target profiles`
- **Relevant Context:** No network access needed — this is pure local static analysis.

---

## Sub-Task 8 — README + cleanup

- **Status:** [ ] pending
- **Intent:** Make the repo submission-ready with accurate documentation.
- **Expected Outcomes:**
  - `README.md` describes what targetlint does, installation steps, and example invocations
  - `git status` shows a clean working tree
  - All files are on branch `feat/implement-targetlint`
- **Todo List:**
  1. Update `README.md`: project description, `pip install -e .` instructions, example command, example output snippet, description of bundled target profiles
  2. Run `git status` and confirm clean tree; stage any untracked files that should be committed
  3. Commit: `docs: update README with installation, usage, and target profile descriptions`
- **Relevant Context:** Per AGENTS.md, never commit directly to `main`. All work stays on `feat/implement-targetlint`.
