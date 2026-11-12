"""Car sprite drawing primitives shared by traffic and the player vehicle."""

import pygame

from .game_state import CAR_TYPES, CarType
from .rendering_geometry import draw_polygon

DEFAULT_CAR_TYPE = CAR_TYPES[0]


def draw_car(
    surface: pygame.Surface,
    x: float,
    bottom: float,
    width: float,
    color: tuple[int, int, int],
    player: bool = False,
    car_type: CarType = DEFAULT_CAR_TYPE,
) -> None:
    """Draw a car using the shape configured by its car type."""
    if car_type.shape == "f1":
        renderer = _draw_f1_car
    elif car_type.shape == "simple":
        renderer = _draw_simple_car
    else:
        raise ValueError(f"Unsupported car shape: {car_type.shape!r}")
    renderer(surface, x, bottom, width, color, player)


def _draw_f1_car(
    surface: pygame.Surface,
    x: float,
    bottom: float,
    width: float,
    color: tuple[int, int, int],
    player: bool = False,
) -> None:
    height = width * (0.58 if player else 0.62)
    x = round(x)
    bottom = round(bottom)
    left = x - width / 2
    top = bottom - height

    front_tire_width = max(4, round(width * 0.19))
    front_tire_height = max(5, round(height * 0.30))
    for offset in (0.20, 0.61):
        pygame.draw.rect(
            surface,
            (17, 20, 25),
            (
                round(left + width * offset),
                round(top + height * 0.20),
                front_tire_width,
                front_tire_height,
            ),
            border_radius=max(1, round(width * 0.025)),
        )

    pygame.draw.ellipse(
        surface,
        (24, 31, 38),
        (
            round(left - width * 0.08),
            round(bottom - height * 0.17),
            round(width * 1.16),
            round(height * 0.23),
        ),
    )
    draw_polygon(
        surface,
        (35, 40, 47),
        [
            (left + width * 0.06, top + height * 0.14),
            (left + width * 0.94, top + height * 0.14),
            (left + width * 0.88, top + height * 0.20),
            (left + width * 0.12, top + height * 0.20),
        ],
    )
    draw_polygon(
        surface,
        (35, 40, 47),
        [
            (left + width * 0.08, top + height * 0.83),
            (left + width * 0.92, top + height * 0.83),
            (left + width * 0.98, top + height * 0.94),
            (left + width * 0.02, top + height * 0.94),
        ],
    )
    draw_polygon(
        surface,
        color,
        [
            (x, top + height * 0.03),
            (left + width * 0.57, top + height * 0.24),
            (left + width * 0.70, top + height * 0.43),
            (left + width * 0.77, top + height * 0.70),
            (left + width * 0.64, top + height * 0.82),
            (left + width * 0.36, top + height * 0.82),
            (left + width * 0.23, top + height * 0.70),
            (left + width * 0.30, top + height * 0.43),
            (left + width * 0.43, top + height * 0.24),
        ],
    )
    for side in (-1, 1):
        draw_polygon(
            surface,
            (
                max(0, color[0] - 28),
                max(0, color[1] - 28),
                max(0, color[2] - 28),
            ),
            [
                (x + side * width * 0.15, top + height * 0.43),
                (x + side * width * 0.34, top + height * 0.40),
                (x + side * width * 0.39, top + height * 0.68),
                (x + side * width * 0.27, top + height * 0.73),
            ],
        )
    draw_polygon(
        surface,
        (31, 51, 67),
        [
            (x - width * 0.14, top + height * 0.31),
            (x - width * 0.10, top + height * 0.24),
            (x + width * 0.10, top + height * 0.24),
            (x + width * 0.14, top + height * 0.31),
            (x + width * 0.11, top + height * 0.47),
            (x - width * 0.11, top + height * 0.47),
        ],
    )
    pygame.draw.line(
        surface,
        (176, 190, 195),
        (round(x), round(top + height * 0.24)),
        (round(x), round(top + height * 0.34)),
        max(1, round(width * 0.025)),
    )
    rear_tire_width = max(4, round(width * 0.25))
    rear_tire_height = max(5, round(height * 0.36))
    for offset in (0.02, 0.73):
        pygame.draw.rect(
            surface,
            (17, 20, 25),
            (
                round(left + width * offset),
                round(top + height * 0.58),
                rear_tire_width,
                rear_tire_height,
            ),
            border_radius=max(1, round(width * 0.025)),
        )


def _draw_simple_car(
    surface: pygame.Surface,
    x: float,
    bottom: float,
    width: float,
    color: tuple[int, int, int],
    player: bool = False,
) -> None:
    height = width * (0.56 if player else 0.62)
    x = round(x)
    bottom = round(bottom)
    left = x - width / 2
    top = bottom - height

    pygame.draw.ellipse(
        surface,
        (24, 31, 38),
        (
            round(left - width * 0.08),
            round(bottom - height * 0.17),
            round(width * 1.16),
            round(height * 0.23),
        ),
    )
    draw_polygon(
        surface,
        color,
        [
            (left + width * 0.08, bottom - height * 0.25),
            (left + width * 0.19, top + height * 0.30),
            (left + width * 0.35, top + height * 0.05),
            (left + width * 0.68, top + height * 0.05),
            (left + width * 0.86, top + height * 0.33),
            (left + width * 0.96, bottom - height * 0.25),
            (left + width * 0.89, bottom),
            (left + width * 0.12, bottom),
        ],
    )
    draw_polygon(
        surface,
        (31, 51, 67),
        [
            (left + width * 0.31, top + height * 0.30),
            (left + width * 0.40, top + height * 0.11),
            (left + width * 0.64, top + height * 0.11),
            (left + width * 0.76, top + height * 0.32),
        ],
    )
    pygame.draw.line(
        surface,
        (126, 201, 211),
        (round(left + width * 0.51), round(top + height * 0.12)),
        (round(left + width * 0.51), round(top + height * 0.30)),
        max(1, round(width * 0.025)),
    )
    wheel_width = max(3, round(width * 0.13))
    wheel_height = max(4, round(height * 0.30))
    for wheel_x in (left + width * 0.13, left + width * 0.78):
        pygame.draw.rect(
            surface,
            (18, 21, 27),
            (
                round(wheel_x),
                round(bottom - wheel_height * 0.72),
                wheel_width,
                wheel_height,
            ),
            border_radius=max(1, round(width * 0.025)),
        )

    lamp_color = (255, 243, 183) if player else (255, 90, 77)
    for lamp_x in (left + width * 0.18, left + width * 0.77):
        pygame.draw.rect(
            surface,
            lamp_color,
            (
                round(lamp_x),
                round(bottom - height * 0.30),
                max(2, round(width * 0.09)),
                max(2, round(height * 0.07)),
            ),
        )
