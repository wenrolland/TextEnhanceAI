# Repository Guidelines

## Project Structure & Module Organization
- Root files: `TextEnhanceAI.py` (main app), `README.md`, `LICENSE`, screenshots `TextEnhanceAI-*.png`.
- Runtime artifacts: scratchpads `TextEnhanceAI-scratchpad_*.md` are generated next to the script.
- No package layout yet; the GUI and logic live in a single module. If you split code, keep UI in `ui/` and LLM/helpers in `core/`.

## Build, Test, and Development Commands
- Run locally: `python TextEnhanceAI.py`
- Create venv (optional):
  - Windows: `python -m venv .venv && .venv\\Scripts\\activate`
  - Unix: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install ollama` (Tkinter and difflib are stdlib).
- Ollama model: `ollama pull llama3.1:8b` (ensure Ollama is installed and running).

## Coding Style & Naming Conventions
- Python 3.7+; follow PEP 8 with 4‑space indents.
- Functions/variables: `snake_case`; classes: `PascalCase`; constants: `UPPER_CASE`.
- Docstrings: short summary + key args/returns where useful.
- UI labeling: keep button text concise; tooltips explain behavior.
- Prompts: extend the `PROMPTS` dict; avoid duplicating strings across the UI.

## Testing Guidelines
- No formal test suite yet. For changes, provide manual steps to reproduce and verify (what you typed, which button you clicked, expected diff/behavior).
- If adding tests later, place them in `tests/` and name `test_*.py` (pytest style). Aim for smoke tests around diff generation and scratchpad logging.

## Commit & Pull Request Guidelines
- Commits: imperative mood, present tense (e.g., "Fix grammar prompt", "Update README"). Keep focused and small.
- PRs: include a clear description, linked issues (if any), and before/after screenshots for UI changes.
- Checklists: note local run results and any edge cases tested.

## Security & Configuration Tips
- The app uses a local LLM via the `ollama` Python client. No cloud calls are required; ensure your model is local.
- Do not commit runtime artifacts (e.g., `TextEnhanceAI-scratchpad_*.md`).
- If you introduce config, prefer environment variables with safe defaults.

