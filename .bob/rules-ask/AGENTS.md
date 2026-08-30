# AGENTS.md — Ask Mode

This file provides guidance to agents when working with code in this repository.

## Non-Obvious Context

- **This repo has no application code** — it is a pure security scaffold template for IBM Hackathon teams. Questions about "the app" or "the project" refer to code teams will add themselves.
- **`.bobignore` is not `.gitignore`** — it specifically prevents Bob from reading credential-pattern files into session history. Both files exist for different reasons.
- **`bob_sessions/` is intentionally tracked in git** — the `.gitignore` explicitly excludes live session files but the exported folder must be committed for hackathon submission.
- **`.env.example` is the only env file in git** — it documents required environment variable names without real values. Teams populate a local `.env` from it.
