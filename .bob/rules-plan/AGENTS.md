# AGENTS.md — Plan Mode

This file provides guidance to agents when working with code in this repository.

## Non-Obvious Architectural Constraints

- **Security files must not be modified** — `.gitignore` and `.bobignore` have an explicit `DO NOT REMOVE OR MODIFY` header. Any plan that touches these files for convenience will break hackathon compliance.
- **`config.json` / `config.yaml` are permanently git-ignored** — architectural plans must not use these filenames for application configuration; the files will never be committed.
- **Credential-named files are invisible to Bob** — plan any file naming scheme to avoid patterns like `*secret*`, `*token*`, `*api_key*`, `*password*`. Otherwise Bob cannot assist with those files.
- **The template is language-agnostic** — `.gitignore` covers Node.js, Python, and Java simultaneously. Application architecture can use any of these stacks.
- **`bob_sessions/` must be in the committed file tree at submission** — architectural plans for CI/CD or repo cleanup must preserve this directory.
