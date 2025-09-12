from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def move(self, dx: float, dy: float) -> "Rect":
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.right <= other.left
            or self.left >= other.right
            or self.bottom <= other.top
            or self.top >= other.bottom
        )


def resolve_collisions(
    rect: Rect, vx: float, vy: float, solids: Iterable[Rect]
) -> Tuple[Rect, float, float, bool, bool]:
    """
    Move rect by (vx, vy) resolving collisions against solids.

    Returns (new_rect, resolved_vx, resolved_vy, on_ground, on_ceiling)
    """
    on_ground = False
    on_ceiling = False

    # Horizontal move first
    new_rect = rect.move(vx, 0)
    if vx != 0:
        collided = _first_collision(new_rect, solids)
        if collided is not None:
            if vx > 0:
                # place right next to the left side of solid
                new_rect = Rect(collided.left - rect.w, rect.y, rect.w, rect.h)
            else:
                # place left next to the right side of solid
                new_rect = Rect(collided.right, rect.y, rect.w, rect.h)
            vx = 0.0

    # Vertical move
    new_rect = new_rect.move(0, vy)
    if vy != 0:
        collided = _first_collision(new_rect, solids)
        if collided is not None:
            if vy > 0:
                # landed on top
                new_rect = Rect(new_rect.x, collided.top - rect.h, rect.w, rect.h)
                on_ground = True
            else:
                # hit ceiling
                new_rect = Rect(new_rect.x, collided.bottom, rect.w, rect.h)
                on_ceiling = True
            vy = 0.0

    return new_rect, vx, vy, on_ground, on_ceiling


def _first_collision(rect: Rect, solids: Iterable[Rect]):
    for s in solids:
        if rect.intersects(s):
            return s
    return None

