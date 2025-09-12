import math

from game.physics import Rect, resolve_collisions


def test_horizontal_collision_stops_at_wall():
    wall = Rect(100, 0, 20, 200)
    player = Rect(60, 50, 40, 40)
    pr, vx, vy, on_ground, on_ceiling = resolve_collisions(player, 10, 0, [wall])
    # Should end with player's right at wall.left
    assert math.isclose(pr.right, wall.left)
    assert vx == 0
    assert vy == 0
    assert on_ground is False
    assert on_ceiling is False


def test_vertical_collision_lands_on_platform():
    platform = Rect(0, 100, 200, 20)
    player = Rect(60, 60, 40, 40)
    # Move downward 50px; should land at y=60 (platform.top - h)
    pr, vx, vy, on_ground, on_ceiling = resolve_collisions(player, 0, 50, [platform])
    assert math.isclose(pr.bottom, platform.top)
    assert vy == 0
    assert on_ground is True
    assert on_ceiling is False


def test_no_collision_moves_freely():
    player = Rect(0, 0, 10, 10)
    pr, vx, vy, on_ground, on_ceiling = resolve_collisions(player, 5, 7, [])
    assert pr.x == 5 and pr.y == 7
    assert vx == 5 and vy == 7
    assert not on_ground and not on_ceiling
