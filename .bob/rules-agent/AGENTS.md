# AGENTS.md — Agent Mode (Coding)

This file provides guidance to agents when working with code in this repository.

## Non-Obvious Coding Constraints

- **`.bobignore` blocks files/vars with credential-like names** — any file whose name matches patterns like `*api_key*`, `*secret*`, `*token*`, `*password*`, `*config.json*` cannot be read. Do not name utility files with these patterns.
- **`config.json` / `config.yaml` are git-ignored** — never use these as config file names in application code; they will silently disappear from commits.
- **`bob_sessions/` must be committed** — it is required for hackathon submission. Do not gitignore it or exclude it.
- **No application code exists yet** — this is a template. When scaffolding a new project inside this repo, add language-specific gitignore patterns only below the `DO NOT REMOVE ABOVE PATTERNS` marker in `.gitignore`.
- **Always use environment variables for credentials** — no exceptions. Use `dotenv` pattern for all runtimes.
