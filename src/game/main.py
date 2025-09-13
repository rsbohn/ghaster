import sys
import os
import math
import logging
from pathlib import Path
from typing import List

import pygame

from .physics import Rect, resolve_collisions
from dataclasses import dataclass
from typing import Tuple, Optional


WIDTH, HEIGHT = 800, 600
FPS = 60
GRAVITY = 1700.0  # px/s^2 (base value; adjustable at runtime)
MOVE_ACCEL = 8000.0
MOVE_MAX_SPEED = 300.0
GROUND_FRICTION = 8.0  # per second
AIR_FRICTION = 1.5
JUMP_SPEED = 820.0  # base jump speed (adjustable)
COYOTE_TIME = 0.12  # seconds after leaving ground to still allow jump
JUMP_BUFFER = 0.12  # seconds to buffer jump input

PLAYER_W, PLAYER_H = 40, 50


@dataclass
class Door:
    rect: Rect
    label: str
    target_board: str


def build_top_board() -> Tuple[List[Rect], List[Door], Tuple[float, float]]:
    """Top (main) board with a vertical climb and two doors at the top."""
    solids: List[Rect] = []
    # Base floor
    solids.append(Rect(0, HEIGHT - 40, WIDTH, 40))
    # Side walls to keep the player within the screen
    solids.append(Rect(-40, -5000, 40, 10000))  # left wall
    solids.append(Rect(WIDTH, -5000, 40, 10000))  # right wall

    # Ascending platforms (closer spacing, slightly wider)
    platform_w, platform_h = 200, 20
    xs = [60, WIDTH // 2 - platform_w // 2, WIDTH - platform_w - 60]
    y = HEIGHT - 100
    for i in range(1, 60):  # more platforms upwards
        x = xs[i % len(xs)]
        y -= 90  # closer vertical step for easier jumps
        solids.append(Rect(x, y, platform_w, platform_h))

    # Find the highest platform within the visible width
    top_candidates = [
        s for s in solids if 0 <= s.x < WIDTH and s.w >= 100 and s.h <= 40 and s.y < HEIGHT - 60
    ]
    if top_candidates:
        top_plat = min(top_candidates, key=lambda r: r.y)
    else:
        # Fallback to the floor if something goes odd
        top_plat = Rect(WIDTH // 2 - platform_w // 2, HEIGHT - 1000, platform_w, platform_h)

    # Place two doors on the top platform: ♦ and ♠
    door_w, door_h = 40, 60
    d1x = top_plat.x + top_plat.w * 0.30 - door_w / 2
    d2x = top_plat.x + top_plat.w * 0.70 - door_w / 2
    dy = top_plat.y - door_h
    doors = [
        Door(Rect(d1x, dy, door_w, door_h), "♦", "diamond"),
        Door(Rect(d2x, dy, door_w, door_h), "♠", "spades"),
    ]

    spawn = (64.0, HEIGHT - 200.0)
    return solids, doors, spawn


def build_placeholder_board() -> Tuple[List[Rect], List[Door], Tuple[float, float]]:
    """Placeholder board: floor + two layers of platforms."""
    solids: List[Rect] = []
    # Base floor and side walls
    solids.append(Rect(0, HEIGHT - 40, WIDTH, 40))
    solids.append(Rect(-40, -5000, 40, 10000))
    solids.append(Rect(WIDTH, -5000, 40, 10000))

    # Two platform layers spanning the screen with gaps
    layer_h = 20
    y1 = HEIGHT - 240
    y2 = HEIGHT - 400
    gap = 80
    plat_w = 220
    xs = [40, 40 + plat_w + gap, WIDTH - plat_w - 40]
    for x in xs:
        solids.append(Rect(x, y1, plat_w, layer_h))
        solids.append(Rect(x, y2, plat_w, layer_h))

    doors: List[Door] = []  # No exits yet; this is a placeholder
    spawn = (80.0, HEIGHT - 200.0)
    return solids, doors, spawn


def build_diamond_board() -> Tuple[List[Rect], List[Door], Tuple[float, float]]:
    """Diamond board: lots of narrow platforms; top door returns to board 1 (top)."""
    solids: List[Rect] = []
    # Base floor and side walls
    solids.append(Rect(0, HEIGHT - 40, WIDTH, 40))
    solids.append(Rect(-40, -5000, 40, 10000))
    solids.append(Rect(WIDTH, -5000, 40, 10000))

    # Narrow platforms in a long ascent
    plat_w, plat_h = 90, 16
    step_y = 80
    y = HEIGHT - 140
    cols = [60, WIDTH // 2 - plat_w // 2, WIDTH - plat_w - 60]
    for i in range(1, 55):
        x = cols[i % len(cols)]
        y -= step_y
        solids.append(Rect(x, y, plat_w, plat_h))

    # Highest platform
    top_plat = min([s for s in solids if s.h <= 40 and s.w >= 60], key=lambda r: r.y)

    # Door at the top returning to top board
    door_w, door_h = 40, 60
    dx = top_plat.x + top_plat.w * 0.5 - door_w / 2
    dy = top_plat.y - door_h
    doors = [Door(Rect(dx, dy, door_w, door_h), "♦", "top")]

    spawn = (80.0, HEIGHT - 200.0)
    return solids, doors, spawn


def build_spades_board() -> Tuple[List[Rect], List[Door], Tuple[float, float]]:
    """Spades room: platforms along each side, open middle.
    Platforms are dark gray; background handled in render.
    """
    solids: List[Rect] = []
    # Base floor and side walls
    solids.append(Rect(0, HEIGHT - 40, WIDTH, 40))
    solids.append(Rect(-40, -5000, 40, 10000))
    solids.append(Rect(WIDTH, -5000, 40, 10000))

    # Side platforms (left and right), leave large open middle
    plat_w, plat_h = 180, 20
    left_x = 40
    right_x = WIDTH - plat_w - 40
    y = HEIGHT - 120
    step_y = 90
    for _ in range(1, 24):
        y -= step_y
        solids.append(Rect(left_x, y, plat_w, plat_h))
        solids.append(Rect(right_x, y, plat_w, plat_h))

    doors: List[Door] = []  # No exits defined; reset (R) to return
    spawn = (80.0, HEIGHT - 200.0)
    return solids, doors, spawn


def build_board(name: str) -> Tuple[List[Rect], List[Door], Tuple[float, float]]:
    if name == "top":
        return build_top_board()
    elif name == "placeholder":
        return build_placeholder_board()
    elif name == "diamond":
        return build_diamond_board()
    elif name == "spades":
        return build_spades_board()
    else:
        return build_top_board()


def run():
    # Setup logging (truncate each run)
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "game.log"
    logging.basicConfig(
        level=logging.INFO,
        filename=str(log_path),
        filemode="w",
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger("game")

    pygame.init()
    pygame.display.set_caption("Tiny Platformer")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Game state
    current_board = "top"
    solids, doors, spawn = build_board(current_board)
    player = Rect(spawn[0], spawn[1], PLAYER_W, PLAYER_H)
    vx, vy = 0.0, 0.0
    on_ground = False
    gravity = GRAVITY
    jump_speed = JUMP_SPEED
    coyote_timer = 0.0
    jump_buffer = 0.0
    jump_held = False

    camera_y = 0.0

    # Cheat input state (e.g., "/d" for diamond, "/s" for spades)
    cheat_active = False
    cheat_buffer = ""

    # Level bounds for progress: base is floor, top is highest platform
    def compute_bounds(solids_list: List[Rect]) -> Tuple[float, float]:
        base = HEIGHT - 40
        # Consider platform-like solids: not huge walls, within screen, reasonable size
        candidates = [
            s
            for s in solids_list
            if (s.h <= 60) and (s.w >= 40) and (s.x + s.w > 0) and (s.x < WIDTH)
        ]
        top = min((s.y for s in candidates), default=base - 1)
        return base, top

    base_y, top_y = compute_bounds(solids)

    # Use default font to avoid dependency on system font config (fc-list)
    font_small = pygame.font.Font(None, 18)

    def try_enter_door(player_rect: Rect) -> Optional[Door]:
        for d in doors:
            if player_rect.intersects(d.rect):
                return d
        return None

    def switch_board(name: str, door_from: Optional[Door] = None):
        nonlocal solids, doors, spawn, current_board, player, vx, vy, on_ground, base_y, top_y, camera_y
        current_board = name
        solids, doors, spawn = build_board(name)
        # Place player at spawn; if coming from a door, keep horizontal center if reasonable
        px = spawn[0]
        py = spawn[1]
        player = Rect(px, py, PLAYER_W, PLAYER_H)
        vx, vy = 0.0, 0.0
        on_ground = False
        base_y, top_y = compute_bounds(solids)
        camera_y = max(0.0, player.y - HEIGHT * 0.5)

    running = True
    # In headless test mode, exit after a few frames to avoid blocking CI/CLI
    headless = os.environ.get("PYGAME_HEADLESS_TEST")
    max_frames = 12 if headless else None
    frames = 0
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Capture textual input for simple cheats starting with '/'
                try:
                    ch = event.unicode
                except Exception:
                    ch = ""
                if ch == "/":
                    cheat_active = True
                    cheat_buffer = ""
                elif cheat_active and ch:
                    if ch.lower() in ("d", "s"):
                        if ch.lower() == "d":
                            switch_board("diamond")
                        elif ch.lower() == "s":
                            switch_board("spades")
                        cheat_active = False
                        cheat_buffer = ""
                    elif ch in ("\r", "\n", " "):
                        cheat_active = False
                        cheat_buffer = ""
                    else:
                        cheat_buffer += ch
                        # Keep buffer small; cancel if unexpected long
                        if len(cheat_buffer) > 8:
                            cheat_active = False
                            cheat_buffer = ""
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    # Reset to top board spawn
                    switch_board("top")
                    gravity = GRAVITY
                    jump_speed = JUMP_SPEED
                if event.key == pygame.K_BACKSPACE and cheat_active:
                    cheat_buffer = cheat_buffer[:-1]
                    if not cheat_buffer:
                        # remain active waiting for next char
                        pass
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    # If overlapping a door and pressing up/w, enter door instead of jump
                    entered = False
                    if event.key in (pygame.K_w, pygame.K_UP) and on_ground:
                        d = try_enter_door(player)
                        if d is not None:
                            switch_board(d.target_board, d)
                            jump_buffer = 0.0
                            jump_held = False
                            entered = True
                    if not entered:
                        jump_buffer = JUMP_BUFFER
                        jump_held = True
                if event.key == pygame.K_PAGEUP:
                    gravity = min(4000.0, gravity + 100.0)
                if event.key == pygame.K_PAGEDOWN:
                    gravity = max(100.0, gravity - 100.0)
                if event.key == pygame.K_EQUALS:  # '+' key without shift
                    jump_speed = min(2000.0, jump_speed + 40.0)
                if event.key == pygame.K_MINUS:
                    jump_speed = max(200.0, jump_speed - 40.0)
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    jump_held = False
                    # Variable jump height: cut upward velocity when jump released
                    if vy < 0:
                        vy *= 0.45

        keys = pygame.key.get_pressed()
        ax = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            ax -= MOVE_ACCEL
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            ax += MOVE_ACCEL

        # friction depends on grounded
        friction = GROUND_FRICTION if on_ground else AIR_FRICTION
        if abs(ax) < 1e-3:
            vx -= vx * friction * dt
        else:
            vx += ax * dt
            vx = max(-MOVE_MAX_SPEED, min(MOVE_MAX_SPEED, vx))

        # coyote time and jump buffer
        if on_ground:
            coyote_timer = COYOTE_TIME
        else:
            coyote_timer = max(0.0, coyote_timer - dt)

        jump_buffer = max(0.0, jump_buffer - dt)
        if jump_buffer > 0 and (on_ground or coyote_timer > 0):
            vy = -jump_speed
            on_ground = False
            jump_buffer = 0.0

        # gravity
        vy += gravity * dt
        vy = min(vy, 1000.0)

        # integrate with collision resolution
        dx, dy = vx * dt, vy * dt
        player, rdx, rdy, landed, hit_ceiling = resolve_collisions(player, dx, dy, solids)
        # Zero velocities on collision resolution
        if rdx != dx:
            vx = 0.0
        if rdy != dy or landed or hit_ceiling:
            vy = 0.0
        on_ground = landed

        # Log position and velocity each frame (only)
        logger.info("POS x=%.2f y=%.2f VEL vx=%.2f vy=%.2f", player.x, player.y, vx, vy)

        # No death on falling; you can always climb back up

        # vertical camera follow (fixed width)
        target_cy = player.y - HEIGHT * 0.5
        camera_y += (target_cy - camera_y) * min(1.0, dt * 5)

        # render
        if current_board == "spades":
            # Medium blue-gray background, no parallax
            screen.fill((75, 95, 120))
        else:
            screen.fill((18, 18, 24))

            # parallax background bands
            for i, color in enumerate([(35, 35, 55), (28, 28, 44), (24, 24, 38)]):
                band_y = HEIGHT - 80 - i * 16
                pygame.draw.rect(screen, color, (0, band_y, WIDTH, HEIGHT - band_y))

        # draw level
        for s in solids:
            rect = pygame.Rect(int(s.x), int(s.y - camera_y), int(s.w), int(s.h))
            color = (80, 200, 120)
            if current_board == "spades":
                color = (60, 60, 70)  # dark gray platforms/walls/floor
            elif current_board == "diamond":
                # Color narrow platforms red; leave floor/walls green
                is_floor = (abs(s.y - (HEIGHT - 40)) < 0.5 and abs(s.w - WIDTH) < 0.5)
                is_platform_like = (s.h <= 30 and s.w <= 130 and s.y < HEIGHT - 60)
                if is_platform_like and not is_floor:
                    color = (200, 70, 70)
            pygame.draw.rect(screen, color, rect)

        # draw doors
        for d in doors:
            rect = pygame.Rect(int(d.rect.x), int(d.rect.y - camera_y), int(d.rect.w), int(d.rect.h))
            color = (220, 80, 80) if d.label == "♦" else (40, 40, 60)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (230, 230, 240), rect, 2)
            # Label
            label_surf = font_small.render(d.label, True, (240, 240, 255))
            lx = rect.x + rect.w // 2 - label_surf.get_width() // 2
            ly = rect.y + rect.h // 2 - label_surf.get_height() // 2
            screen.blit(label_surf, (lx, ly))

        # draw player
        prect = pygame.Rect(int(player.x), int(player.y - camera_y), int(player.w), int(player.h))
        pygame.draw.rect(screen, (240, 220, 90), prect)

        # HUD
        _draw_hud(screen, on_ground, gravity, jump_speed, player.y, base_y, top_y)
        _draw_progress_bar(screen, player.y, base_y, top_y)

        pygame.display.flip()

        if max_frames is not None:
            frames += 1
            if frames >= max_frames:
                running = False

    pygame.quit()
    return 0


def _draw_hud(
    screen, on_ground: bool, gravity: float, jump_speed: float, py: float, base_y: float, top_y: float
):
    # Default pygame font avoids 'fc-list' dependency
    font = pygame.font.Font(None, 16)
    # compute progress
    total = max(1.0, base_y - top_y)
    climbed = max(0.0, base_y - py)
    prog = max(0.0, min(1.0, climbed / total))
    lines = [
        "A/D or Left/Right: Move",
        "Space/W/Up: Jump",
        "PgUp/PgDn: Gravity +/-",
        "-/=: Jump strength -/+",
        "R: Reset, Esc: Quit",
        f"On ground: {'yes' if on_ground else 'no'}",
        f"Gravity: {gravity:.0f} px/s^2",
        f"Jump: {jump_speed:.0f} px/s",
        f"Height: {climbed:.0f} / {total:.0f} px ({prog*100:.0f}%)",
    ]
    for i, text in enumerate(lines):
        surf = font.render(text, True, (220, 220, 230))
        screen.blit(surf, (12, 10 + i * 18))


def _draw_progress_bar(screen, py: float, base_y: float, top_y: float):
    import pygame

    total = max(1.0, base_y - top_y)
    climbed = max(0.0, base_y - py)
    prog = max(0.0, min(1.0, climbed / total))

    # Bar geometry
    bar_w = 10
    margin = 16
    x = WIDTH - margin - bar_w
    y = 50
    h = HEIGHT - 100

    # Outline
    pygame.draw.rect(screen, (60, 60, 80), (x - 2, y - 2, bar_w + 4, h + 4), 2)
    # Background
    pygame.draw.rect(screen, (30, 30, 45), (x, y, bar_w, h))
    # Fill (top grows upward)
    fill_h = int(h * prog)
    pygame.draw.rect(screen, (120, 200, 255), (x, y + (h - fill_h), bar_w, fill_h))
    # Ticks every 10%
    for i in range(1, 10):
        ty = y + int(h * (1 - i / 10))
        pygame.draw.line(screen, (90, 90, 110), (x - 6, ty), (x, ty), 1)


if __name__ == "__main__":
    sys.exit(run())
