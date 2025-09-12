import sys
import os
import math
import logging
from pathlib import Path
from typing import List

import pygame

from .physics import Rect, resolve_collisions


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


def build_level() -> List[Rect]:
    # Vertical climb layout: fixed width with side walls and many ascending platforms
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

    return solids


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
    solids = build_level()
    player = Rect(64, HEIGHT - 200, 40, 50)
    vx, vy = 0.0, 0.0
    on_ground = False
    gravity = GRAVITY
    jump_speed = JUMP_SPEED
    coyote_timer = 0.0
    jump_buffer = 0.0
    jump_held = False

    camera_y = 0.0

    # Level bounds for progress: base is floor, top is highest platform
    base_y = HEIGHT - 40
    top_y = min(
        (s.y for s in solids if 0 <= s.x < WIDTH and s.w >= 100),
        default=base_y - 1,
    )

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
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    player = Rect(64, HEIGHT - 200, 40, 50)
                    vx, vy = 0.0, 0.0
                    on_ground = False
                    camera_x = 0.0
                    gravity = GRAVITY
                    jump_speed = JUMP_SPEED
                if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
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
        screen.fill((18, 18, 24))

        # parallax background bands
        for i, color in enumerate([(35, 35, 55), (28, 28, 44), (24, 24, 38)]):
            band_y = HEIGHT - 80 - i * 16
            pygame.draw.rect(screen, color, (0, band_y, WIDTH, HEIGHT - band_y))

        # draw level
        for s in solids:
            rect = pygame.Rect(int(s.x), int(s.y - camera_y), int(s.w), int(s.h))
            pygame.draw.rect(screen, (80, 200, 120), rect)

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
    font = pygame.font.SysFont("consolas", 16)
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
