# targetlint

Target-aware static analyser for embedded C.

## What it does

targetlint cross-references C source code against a YAML hardware target profile to find constraint violations that are invisible to conventional analysers like cppcheck or clang-tidy.

## The problem

`cppcheck` and `clang-tidy` analyse code in isolation — they have no concept of your deployment target.

| Code | Linux | Bare-metal Cortex-M0 |
|------|-------|----------------------|
| `malloc()` | fine | silent crash — no heap |
| `printf()` | fine | links but does nothing — no stdlib |
| `float` arithmetic | fine | compiles, runs, costs 10 KB of flash and 10× the CPU time — no FPU |

targetlint knows the difference. The compiler does not.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Markdown report (stdout)
targetlint --source path/to/file.c --target path/to/target.yaml

# Self-contained HTML report
targetlint --source path/to/file.c --target path/to/target.yaml --html
```

## Example — same code, three targets

```
cortex-m0:  14 findings (7 critical, 6 high, 0 medium, 1 low)
cortex-m4:   8 findings (5 critical, 2 high, 1 medium, 0 low)
linux-x86:   3 findings (0 critical, 1 high, 2 medium, 0 low)
```

## Target profile

Target profiles are YAML files that describe the hardware constraints of your deployment target. Example — `targets/cortex-m0.yaml`:

```yaml
arch: "ARM Cortex-M0"
ram_bytes: 32768
stack_bytes: 8192
has_heap: false
has_stdlib: false
has_fpu: false
clock_hz: 16000000
watchdog_timeout_ms: 2000
word_size_bits: 32
safety_critical: true
```

| Field | Type | Description |
|-------|------|-------------|
| `arch` | string | Human-readable architecture name |
| `ram_bytes` | int | Total RAM in bytes |
| `stack_bytes` | int | Stack budget in bytes |
| `has_heap` | bool | Whether dynamic allocation is available |
| `has_stdlib` | bool | Whether C standard library is available |
| `has_fpu` | bool | Whether a hardware FPU is present |
| `clock_hz` | int | Target clock frequency in Hz |
| `watchdog_timeout_ms` | int \| null | Watchdog timeout in milliseconds; `null` if none |
| `word_size_bits` | int | Native word size in bits |
| `safety_critical` | bool | Whether MISRA/safety rules apply |

## Rules

Five rule modules run on every analysis:

| Module | What it checks |
|--------|----------------|
| `memory.py` | Heap usage, null-check omissions, stack array size |
| `stdlib.py` | `printf`, `stdio.h`, `stdlib.h`, `string.h`, `strcpy`/`strcat` |
| `timing.py` | Hardcoded clock assumptions, busy-wait loops |
| `hardware.py` | FPU assumptions, word size, inline assembly |
| `safety.py` | Recursion, watchdog kicks, MISRA basics |
