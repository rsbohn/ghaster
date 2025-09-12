This repo follows the user-provided Repository Guidelines. Key points to observe when editing:

- Place code in `src/`, tests in `tests/`, scripts in `scripts/` with shebangs.
- Keep Python indentation to 4 spaces and filenames in snake_case.
- Use `scripts/dev`, `scripts/test`, and `scripts/build` to run/develop.
- Avoid committing secrets; no external network calls from code.

Project-specific notes:

- The game loop lives in `src/game/main.py` and relies on a small, Pygame-independent physics core in `src/game/physics.py` to keep testing simple.
- Tests avoid importing Pygame and are in `tests/physics/`.

