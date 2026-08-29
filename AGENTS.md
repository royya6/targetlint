# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## What This Repo Is

**targetlint** is a pure Python CLI tool for embedded/firmware developers. It takes a C source file and a YAML target profile and performs target-aware static analysis, producing a severity-ranked report of constraint violations.

Output is a severity-ranked markdown report and an optional self-contained HTML summary.

## Runtime Architecture

targetlint has **zero network dependencies at runtime**. All analysis is performed locally using pure Python logic.

- **No API calls of any kind** in the implementation
- **No `requests` library** — do not add it as a dependency
- **No `inference.py` or `BobClient`** — Bob is a development tool only, not a runtime dependency
- **Allowed runtime dependencies:** `pyyaml`, `jinja2` only

Bob is used as the development tool (coding agent, planning, etc.) — it is not invoked by the tool at runtime.

## Critical Security Constraints

- **Never read `.env` or `.env.*`** — blocked by `.bobignore`. Advise users to add credentials themselves.
- **Never suggest hardcoding credentials** — always use `os.getenv('VAR')` in Python code.
- **`.bobignore` blocks files matching credential patterns** (e.g. `*api_key*`, `*secret*`, `*password*`, `*token*`). Files or variables with these name patterns will not be readable by Bob.
- **`config.json` and `config.yaml` are git-ignored** — do not use these filenames for config; they will never be committed.
- **`bob_sessions/` must be committed** — required for hackathon project submission.

## Git Commit Protocol

After completing each discrete implementation step that results in working, testable code, always:

1. Stage the relevant changed files with `git add`
2. Generate a conventional commit message describing what was implemented and that it is working
3. Commit the staged changes
4. Report what was committed before moving to the next step

**Never commit:** `.env`, `__pycache__/`, `*.pyc`, or any file matched by `.gitignore`.

**Always commit on a feature branch — use `feat/implement-targetlint`, never directly to `main`.**
