# Tiny Pygame Platformer

A small platformer built with Pygame. Move left/right and jump across a few platforms. Reset with `R`, quit with `Esc`.

## Run

- With uv (recommended):

```
uv run mygame
```

- Or with Python directly (ensure Pygame is installed):

```
pip install pygame
scripts/dev
# or
PYTHONPATH=src python3 -m game.main
```

## Test

Physics is decoupled from Pygame for testability.

```
scripts/test
```

## Build

Creates a simple zip containing the source and scripts.

```
scripts/build
```

## Controls

- A/D or Left/Right: Move
- Space / W / Up: Jump
- PgUp / PgDn: Increase / Decrease gravity
- - / =: Decrease / Increase jump strength
- R: Reset
- Esc: Quit

## Logging

- The game writes a fresh log each run to `logs/game.log` (truncated on start).
- Each frame logs: position and velocity only, e.g. `POS x=... y=... VEL vx=... vy=...`.
