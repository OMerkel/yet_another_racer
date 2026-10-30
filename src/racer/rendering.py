"""Pygame drawing functions for the racing scene and HUD."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pygame

from .game_state import CAR_TYPES, CarType, GameState

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
FPS = 60
HORIZON = 205
ROAD_LOOKAHEAD = 1050.0
DEFAULT_CAR_TYPE = CAR_TYPES[0]

SKY_TOP = (35, 71, 124)
SKY_BOTTOM = (239, 135, 102)
GRASS_A = (44, 126, 71)
GRASS_B = (50, 145, 74)
ROAD = (66, 70, 77)
ROAD_DARK = (48, 51, 59)
CURB_RED = (222, 67, 57)
CREAM = (244, 224, 177)
INK = (20, 27, 39)
GOLD = (255, 210, 92)


@dataclass(frozen=True)
class Fonts:
    """Font set shared by the scene renderer."""

    normal: pygame.font.Font
    small: pygame.font.Font
    large: pygame.font.Font


@dataclass(frozen=True)
class RoadSegment:
    """Projected near and far edges of one road segment."""

    near_progress: float
    far_progress: float
    near_y: float
    far_y: float
    near_center: float
    far_center: float
    near_width: float
    far_width: float


def create_fonts() -> Fonts:
    """Create the fonts used by the game HUD."""
    return Fonts(
        normal=pygame.font.SysFont("consolas", 20, bold=True),
        small=pygame.font.SysFont("consolas", 14, bold=True),
        large=pygame.font.SysFont("consolas", 46, bold=True),
    )


def road_curve(distance: float) -> float:
    """Return the horizontal curve offset at a track distance."""
    return 115 * math.sin(distance * 0.0016) + 52 * math.sin(
        distance * 0.0041 + 1.2
    )


def road_width(progress: float) -> float:
    """Return the projected road width at a perspective depth."""
    return 92 + 565 * progress**1.12


def road_center(distance: float, progress: float) -> float:
    """Return the screen-space road center at a perspective depth."""
    ahead = (1 - progress) * ROAD_LOOKAHEAD
    return (
        SCREEN_WIDTH / 2 + road_curve(distance + ahead) - road_curve(distance)
    )


def _polygon(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[tuple[float, float]],
) -> None:
    pygame.draw.polygon(
        surface, color, [(round(x), round(y)) for x, y in points]
    )


def _draw_car(
    surface: pygame.Surface,
    x: float,
    bottom: float,
    width: float,
    color: tuple[int, int, int],
    player: bool = False,
    car_type: CarType = DEFAULT_CAR_TYPE,
) -> None:
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
    _polygon(
        surface,
        (35, 40, 47),
        [
            (left + width * 0.06, top + height * 0.14),
            (left + width * 0.94, top + height * 0.14),
            (left + width * 0.88, top + height * 0.20),
            (left + width * 0.12, top + height * 0.20),
        ],
    )
    _polygon(
        surface,
        (35, 40, 47),
        [
            (left + width * 0.08, top + height * 0.83),
            (left + width * 0.92, top + height * 0.83),
            (left + width * 0.98, top + height * 0.94),
            (left + width * 0.02, top + height * 0.94),
        ],
    )
    _polygon(
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
        _polygon(
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
    _polygon(
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
    _polygon(
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
    _polygon(
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


def _background_parallax_offsets(distance: float) -> tuple[int, int]:
    road_bend = road_center(distance, 0.0) - SCREEN_WIDTH / 2
    return round(-road_bend * 0.14), round(-road_bend * 0.30)


def _draw_parallax_polygon(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[tuple[int, int]],
    offset: int,
) -> None:
    shifted_points = [(x + offset if y < HORIZON else x, y) for x, y in points]
    _polygon(surface, color, shifted_points)


def _draw_background(surface: pygame.Surface, distance: float = 0.0) -> None:
    far_offset, near_offset = _background_parallax_offsets(distance)
    for y in range(0, HORIZON + 1, 3):
        amount = y / HORIZON
        color = tuple(
            round(SKY_TOP[index] * (1 - amount) + SKY_BOTTOM[index] * amount)
            for index in range(3)
        )
        pygame.draw.rect(surface, color, (0, y, SCREEN_WIDTH, 3))

    pygame.draw.circle(surface, (255, 206, 119), (790 + far_offset, 118), 35)
    _draw_parallax_polygon(
        surface,
        (79, 98, 125),
        [
            (0, 181),
            (105, 103),
            (184, 172),
            (284, 90),
            (394, 183),
            (500, 118),
            (610, 180),
            (724, 94),
            (849, 174),
            (925, 119),
            (960, 146),
            (960, 215),
            (0, 215),
        ],
        far_offset,
    )
    _draw_parallax_polygon(
        surface,
        (54, 83, 92),
        [
            (0, 194),
            (126, 139),
            (218, 192),
            (354, 128),
            (471, 198),
            (605, 139),
            (738, 195),
            (857, 130),
            (960, 179),
            (960, 218),
            (0, 218),
        ],
        near_offset,
    )
    pygame.draw.rect(
        surface, GRASS_A, (0, HORIZON, SCREEN_WIDTH, SCREEN_HEIGHT - HORIZON)
    )


def _project_road_segment(distance: float, index: int) -> RoadSegment:
    segment_count = 76
    near_progress = index / (segment_count - 1)
    far_progress = (index + 1) / (segment_count - 1)
    return RoadSegment(
        near_progress=near_progress,
        far_progress=far_progress,
        near_y=HORIZON + near_progress**2 * (SCREEN_HEIGHT - HORIZON),
        far_y=HORIZON + far_progress**2 * (SCREEN_HEIGHT - HORIZON),
        near_center=road_center(distance, near_progress),
        far_center=road_center(distance, far_progress),
        near_width=road_width(near_progress),
        far_width=road_width(far_progress),
    )


def _draw_road_surface(
    surface: pygame.Surface, segment: RoadSegment, stripe: int
) -> None:
    pygame.draw.rect(
        surface,
        GRASS_B if stripe else GRASS_A,
        (
            0,
            round(segment.far_y),
            SCREEN_WIDTH,
            max(1, round(segment.near_y - segment.far_y + 1)),
        ),
    )
    _polygon(
        surface,
        ROAD if stripe else ROAD_DARK,
        [
            (segment.far_center - segment.far_width / 2, segment.far_y),
            (segment.far_center + segment.far_width / 2, segment.far_y),
            (segment.near_center + segment.near_width / 2, segment.near_y),
            (segment.near_center - segment.near_width / 2, segment.near_y),
        ],
    )


def _draw_road_curbs(
    surface: pygame.Surface, index: int, segment: RoadSegment
) -> None:
    curb_color = CURB_RED if (index // 3) % 2 else CREAM
    for side in (-1, 1):
        _polygon(
            surface,
            curb_color,
            [
                (
                    segment.far_center + side * segment.far_width / 2,
                    segment.far_y,
                ),
                (
                    segment.far_center
                    + side
                    * (segment.far_width / 2 + 7 + 10 * segment.far_progress),
                    segment.far_y,
                ),
                (
                    segment.near_center
                    + side
                    * (segment.near_width / 2 + 7 + 10 * segment.near_progress),
                    segment.near_y,
                ),
                (
                    segment.near_center + side * segment.near_width / 2,
                    segment.near_y,
                ),
            ],
        )


def _draw_lane_markings(
    surface: pygame.Surface, distance: float, index: int, segment: RoadSegment
) -> None:
    if (int(distance * 0.04) + index // 3) % 2 != 0:
        return

    near_mark = 2 + segment.near_progress * 3
    far_mark = 2 + segment.far_progress * 3
    for lane_position in (-1 / 3, 1 / 3):
        _polygon(
            surface,
            CREAM,
            [
                (
                    segment.far_center
                    + lane_position * segment.far_width
                    - far_mark,
                    segment.far_y,
                ),
                (
                    segment.far_center
                    + lane_position * segment.far_width
                    + far_mark,
                    segment.far_y,
                ),
                (
                    segment.near_center
                    + lane_position * segment.near_width
                    + near_mark,
                    segment.near_y,
                ),
                (
                    segment.near_center
                    + lane_position * segment.near_width
                    - near_mark,
                    segment.near_y,
                ),
            ],
        )


def _draw_road(surface: pygame.Surface, distance: float) -> None:
    segment_count = 76
    for index in range(segment_count - 1, -1, -1):
        segment = _project_road_segment(distance, index)
        stripe = (int(distance * 0.055) + index // 3) % 2
        _draw_road_surface(surface, segment, stripe)
        if index % 3 == 0:
            _draw_road_curbs(surface, index, segment)
            _draw_lane_markings(surface, distance, index, segment)


def _draw_traffic(
    surface: pygame.Surface, state: GameState, car_type: CarType
) -> None:
    for car in sorted(
        state.traffic, key=lambda item: item.distance, reverse=True
    ):
        gap = car.distance - state.distance
        if gap < 0 or gap > ROAD_LOOKAHEAD:
            continue
        progress = 1 - gap / ROAD_LOOKAHEAD
        center = road_center(state.distance, progress)
        width = road_width(progress)
        x = center + car.lane * width * 0.34
        y = HORIZON + progress**2 * (SCREEN_HEIGHT - HORIZON)
        _draw_car(
            surface,
            x,
            y,
            16 + 69 * progress,
            car.color,
            car_type=car_type,
        )


def _draw_text(
    surface: pygame.Surface,
    text: str,
    position: tuple[float, float],
    color: tuple[int, int, int],
    font: pygame.font.Font,
    centered: bool = False,
) -> None:
    image = font.render(text, True, color)
    x, y = position
    if centered:
        x -= image.get_width() // 2
    surface.blit(image, (round(x), round(y)))


def _draw_hud(surface: pygame.Surface, state: GameState, fonts: Fonts) -> None:
    pygame.draw.rect(surface, INK, (18, 16, 250, 90), border_radius=5)
    pygame.draw.rect(surface, GOLD, (18, 16, 5, 90))
    _draw_text(surface, "YET ANOTHER RACER", (34, 24), GOLD, fonts.normal)
    _draw_text(
        surface,
        f"SCORE {state.score:06d}",
        (34, 54),
        (242, 241, 221),
        fonts.small,
    )
    _draw_text(
        surface,
        f"DIST {state.distance / 1000:05.2f} KM",
        (34, 76),
        (242, 241, 221),
        fonts.small,
    )

    pygame.draw.rect(
        surface, INK, (SCREEN_WIDTH - 204, 16, 186, 90), border_radius=5
    )
    _draw_text(
        surface,
        f"{int(state.speed):03d}",
        (SCREEN_WIDTH - 187, 22),
        GOLD,
        fonts.large,
    )
    _draw_text(
        surface,
        "KM/H",
        (SCREEN_WIDTH - 102, 54),
        (242, 241, 221),
        fonts.small,
    )
    time_color = (255, 105, 92) if state.time_left < 16 else (242, 241, 221)
    _draw_text(
        surface,
        f"TIME {math.ceil(state.time_left):02d}",
        (SCREEN_WIDTH - 187, 79),
        time_color,
        fonts.small,
    )
    _draw_text(
        surface,
        "ARROWS / WASD OR GAMEPAD  ESC QUIT",
        (22, SCREEN_HEIGHT - 27),
        (249, 235, 190),
        fonts.small,
    )
    if state.crash_time > 0:
        _draw_text(
            surface,
            "CONTACT!",
            (SCREEN_WIDTH // 2, 32),
            (255, 105, 92),
            fonts.normal,
            centered=True,
        )


def _draw_game_over(
    surface: pygame.Surface, state: GameState, fonts: Fonts
) -> None:
    shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
    shade.fill((12, 19, 33, 190))
    surface.blit(shade, (0, 0))
    _draw_text(
        surface,
        "TIME UP",
        (SCREEN_WIDTH // 2, 224),
        GOLD,
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        f"FINAL SCORE  {state.score:06d}",
        (SCREEN_WIDTH // 2, 292),
        (242, 241, 221),
        fonts.normal,
        centered=True,
    )
    _draw_text(
        surface,
        "PRESS R TO RACE AGAIN",
        (SCREEN_WIDTH // 2, 350),
        (255, 151, 110),
        fonts.normal,
        centered=True,
    )


def draw_car_selection(
    surface: pygame.Surface, fonts: Fonts, car_type: CarType
) -> None:
    """Draw the pre-race car picker and a preview of the selected model."""
    _draw_background(surface, distance=0.0)
    _draw_road(surface, 0.0)
    shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
    shade.fill((12, 19, 33, 135))
    surface.blit(shade, (0, 0))

    _draw_text(
        surface,
        "CHOOSE YOUR CAR",
        (SCREEN_WIDTH // 2, 54),
        GOLD,
        fonts.large,
        centered=True,
    )
    pygame.draw.line(surface, CREAM, (230, 122), (730, 122), 2)

    selected_index = CAR_TYPES.index(car_type)
    _draw_text(
        surface,
        "<",
        (218, 304),
        CREAM,
        fonts.large,
        centered=True,
    )
    _draw_car(
        surface,
        SCREEN_WIDTH / 2,
        430,
        230,
        (255, 205, 83),
        player=True,
        car_type=car_type,
    )
    _draw_text(
        surface,
        car_type.name,
        (SCREEN_WIDTH // 2, 465),
        (242, 241, 221),
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        f"{selected_index + 1:02d} / {len(CAR_TYPES):02d}",
        (SCREEN_WIDTH // 2, 520),
        GOLD,
        fonts.normal,
        centered=True,
    )
    _draw_text(
        surface,
        ">",
        (742, 304),
        CREAM,
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        "LEFT / RIGHT  SELECT     ENTER  START",
        (SCREEN_WIDTH // 2, 574),
        CREAM,
        fonts.small,
        centered=True,
    )


def draw_frame(
    surface: pygame.Surface,
    state: GameState,
    fonts: Fonts,
    car_type: CarType = DEFAULT_CAR_TYPE,
) -> None:
    """Draw one complete frame onto a surface without presenting it."""
    _draw_background(surface, state.distance)
    _draw_road(surface, state.distance)
    _draw_traffic(surface, state, car_type)

    player_x = (
        road_center(state.distance, 1.0)
        + state.lateral * road_width(1.0) * 0.34
    )
    player_color = (255, 205, 83) if state.crash_time <= 0 else (255, 116, 89)
    _draw_car(
        surface,
        player_x,
        SCREEN_HEIGHT - 26,
        100,
        player_color,
        player=True,
        car_type=car_type,
    )
    _draw_hud(surface, state, fonts)
    if state.game_over:
        _draw_game_over(surface, state, fonts)
