"""Pygame drawing functions for the racing scene and HUD."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pygame

from .game_state import (
    CAR_TYPES,
    DEFAULT_LAP_COUNT,
    START_LIGHT_COUNT,
    START_LIGHTS_DURATION,
    CarType,
    GameState,
)
from .rendering_cars import DEFAULT_CAR_TYPE, draw_car as _draw_car
from .rendering_geometry import (
    CAMERA_BACK,
    FOCAL_LENGTH,
    HORIZON,
    NEAR_PLANE,
    ROAD,
    ROAD_DRAW_DISTANCE,
    SCREEN_HEIGHT,
    SCREEN_SIZE,
    SCREEN_WIDTH,
    START_LINE_BOX_COLUMNS,
    START_LINE_BOX_ROWS,
    camera_coordinates as _camera_coordinates,
    clip_near_plane as _clip_near_plane,
    draw_polygon as _polygon,
    project_camera_point as _project_camera_point,
    race_camera as _race_camera,
    world_track_point as _world_track_point,
    draw_road as _draw_road,
    draw_start_line as _draw_start_line,
    road_center,
    road_width,
)
from .track import DEFAULT_TRACK, ROAD_HALF_WIDTH, TRACKS, Track, sample_track

__all__ = [
    "CAMERA_BACK",
    "DEFAULT_CAR_TYPE",
    "FOCAL_LENGTH",
    "GOLD",
    "MAP_RECT",
    "NEAR_PLANE",
    "SCREEN_SIZE",
    "START_LINE_BOX_COLUMNS",
    "START_LINE_BOX_ROWS",
    "START_LIGHT_RED",
    "_background_parallax_offsets",
    "_camera_coordinates",
    "_clip_near_plane",
    "_draw_background",
    "_draw_car",
    "_draw_hud",
    "_draw_road",
    "_draw_start_lights",
    "_draw_start_line",
    "_draw_track_map",
    "_draw_traffic",
    "_polygon",
    "_project_camera_point",
    "_race_camera",
    "_track_map_position",
    "_track_map_subtitle",
    "_world_track_point",
    "create_fonts",
    "draw_car_selection",
    "draw_frame",
    "road_center",
    "road_width",
]

FPS = 60
START_LIGHT_RED = (235, 43, 47)
MAP_RECT = pygame.Rect(SCREEN_WIDTH - 230, 116, 212, 150)
SELECTION_MAP_RECT = pygame.Rect(585, 184, 346, 242)
CAR_OPTION_RECT = pygame.Rect(88, 118, 404, 408)
LAP_OPTION_RECT = pygame.Rect(204, 532, 180, 52)

SKY_TOP = (35, 71, 124)
SKY_BOTTOM = (239, 135, 102)
GRASS_A = (44, 126, 71)
GRASS_B = (50, 145, 74)
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


def create_fonts() -> Fonts:
    """Create the fonts used by the game HUD."""
    return Fonts(
        normal=pygame.font.SysFont("consolas", 20, bold=True),
        small=pygame.font.SysFont("consolas", 14, bold=True),
        large=pygame.font.SysFont("consolas", 46, bold=True),
    )


def _background_parallax_offsets(
    distance: float, track: Track = DEFAULT_TRACK
) -> tuple[int, int]:
    road_bend = max(
        -180.0,
        min(
            180.0,
            road_center(distance, 0.0, track) - SCREEN_WIDTH / 2,
        ),
    )
    return round(-road_bend * 0.14), round(-road_bend * 0.30)


def _draw_parallax_polygon(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[tuple[int, int]],
    offset: int,
) -> None:
    shifted_points = [(x + offset if y < HORIZON else x, y) for x, y in points]
    _polygon(surface, color, shifted_points)


def _draw_background(
    surface: pygame.Surface,
    distance: float = 0.0,
    track: Track = DEFAULT_TRACK,
) -> None:
    far_offset, near_offset = _background_parallax_offsets(distance, track)
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


def _draw_traffic(
    surface: pygame.Surface, state: GameState, car_type: CarType
) -> None:
    camera = _race_camera(state.distance, state.track, state.lateral)
    visible = []
    for car in state.traffic:
        gap = car.distance - state.distance
        if gap < 0 or gap > ROAD_DRAW_DISTANCE:
            continue
        position = _camera_coordinates(
            camera,
            _world_track_point(
                car.distance, car.lane * ROAD_HALF_WIDTH, state.track
            ),
        )
        if position[2] >= NEAR_PLANE:
            visible.append((position[2], position, car))
    for depth, position, car in sorted(
        visible, key=lambda item: item[0], reverse=True
    ):
        x, y = _project_camera_point(position)
        _draw_car(
            surface,
            x,
            y,
            1.8 * FOCAL_LENGTH / depth,
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
    lap = max(
        1,
        min(
            state.lap_count,
            int(state.distance // state.track.length) + 1,
        ),
    )
    _draw_text(
        surface,
        f"LAP {lap:02d}/{state.lap_count:02d}",
        (SCREEN_WIDTH - 187, 79),
        (242, 241, 221),
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


def _track_map_position(
    x: float,
    z: float,
    track: Track = DEFAULT_TRACK,
    rect: pygame.Rect = MAP_RECT,
) -> tuple[int, int]:
    left = rect.left + 12
    top = rect.top + 44
    width = rect.width - 24
    height = rect.height - 54
    min_x, max_x, min_z, max_z = track.bounds
    scale = min(width / (max_x - min_x), height / (max_z - min_z))
    map_width = (max_x - min_x) * scale
    map_height = (max_z - min_z) * scale
    offset_x = left + (width - map_width) / 2
    offset_y = top + (height - map_height) / 2
    return (
        round(offset_x + (x - min_x) * scale),
        round(offset_y + (max_z - z) * scale),
    )


def _track_map_subtitle(
    track: Track, distance: float, lap_count: int = DEFAULT_LAP_COUNT
) -> str:
    lap = max(1, min(lap_count, int(distance // track.length) + 1))
    sector = sample_track(distance, track).sector.upper()
    if sector == "MICHAEL-SCHUMACHER-S":
        sector = "SCHUMACHER"
    elif sector == "HATZENBACH-BOGEN":
        sector = "HATZENBACH"
    elif sector == "VEEDOL-SCHIKANE":
        sector = "VEEDOL"
    elif sector == "COCA-COLA-KURVE":
        sector = "COCA-COLA"
    return f"LAP {lap:02d}/{lap_count:02d} {sector}"


def _draw_start_lights(surface: pygame.Surface, state: GameState) -> None:
    """Display five red lights, extinguishing one per countdown second."""
    if state.countdown <= 0:
        return

    panel = pygame.Rect(SCREEN_WIDTH // 2 - 104, 18, 208, 48)
    pygame.draw.rect(surface, INK, panel, border_radius=8)
    pygame.draw.rect(surface, CREAM, panel, width=1, border_radius=8)
    lit_count = min(
        START_LIGHT_COUNT,
        math.ceil(state.countdown / START_LIGHTS_DURATION * START_LIGHT_COUNT),
    )
    for index in range(START_LIGHT_COUNT):
        center = (panel.left + 24 + index * 40, panel.centery)
        color = START_LIGHT_RED if index < lit_count else (75, 29, 34)
        pygame.draw.circle(surface, color, center, 11)
        pygame.draw.circle(surface, CREAM, center, 11, width=1)


def _draw_track_map(
    surface: pygame.Surface,
    track: Track,
    distance: float,
    subtitle: str,
    fonts: Fonts,
    rect: pygame.Rect = MAP_RECT,
    lateral: float = 0.0,
    highlighted: bool = True,
) -> None:
    pygame.draw.rect(surface, INK, rect, border_radius=4)
    border = GOLD if highlighted else (100, 112, 124)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=4)
    _draw_text(
        surface,
        track.name,
        (rect.left + 10, rect.top + 7),
        GOLD,
        fonts.small,
    )
    _draw_text(
        surface,
        subtitle,
        (rect.left + 10, rect.top + 25),
        CREAM,
        fonts.small,
    )

    for index, segment in enumerate(track.segments):
        next_segment = track.segments[(index + 1) % len(track.segments)]
        start = _track_map_position(segment.x, segment.z, track, rect)
        end = _track_map_position(next_segment.x, next_segment.z, track, rect)
        curb_color = CURB_RED if int(segment.distance // 24) % 2 else CREAM
        pygame.draw.line(surface, curb_color, start, end, 5)
        pygame.draw.line(surface, ROAD, start, end, 3)

    player_world = _world_track_point(
        distance, lateral * ROAD_HALF_WIDTH, track
    )
    player_position = _track_map_position(
        player_world[0], player_world[2], track, rect
    )
    pygame.draw.circle(surface, GOLD, player_position, 4)


def _draw_game_over(
    surface: pygame.Surface, state: GameState, fonts: Fonts
) -> None:
    shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
    shade.fill((12, 19, 33, 190))
    surface.blit(shade, (0, 0))
    _draw_text(
        surface,
        "RACE COMPLETE",
        (SCREEN_WIDTH // 2, 224),
        GOLD,
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        f"{state.lap_count} LAPS  FINAL SCORE  {state.score:06d}",
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
    surface: pygame.Surface,
    fonts: Fonts,
    car_type: CarType,
    track: Track = DEFAULT_TRACK,
    track_index: int = 0,
    lap_count: int = DEFAULT_LAP_COUNT,
    active_option: int = 0,
) -> None:
    """Draw the pre-race car and circuit options with a track preview."""
    _draw_background(surface, distance=0.0, track=track)
    _draw_road(surface, 0.0, track)
    shade = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
    shade.fill((12, 19, 33, 135))
    surface.blit(shade, (0, 0))
    if active_option == 0:
        pygame.draw.rect(
            surface, GOLD, CAR_OPTION_RECT, width=2, border_radius=4
        )
    elif active_option == 2:
        pygame.draw.rect(
            surface, GOLD, LAP_OPTION_RECT, width=2, border_radius=4
        )

    _draw_text(
        surface,
        "RACE OPTIONS",
        (SCREEN_WIDTH // 2, 42),
        GOLD,
        fonts.large,
        centered=True,
    )
    selected_index = CAR_TYPES.index(car_type)
    _draw_text(surface, "CAR", (294, 130), GOLD, fonts.normal, centered=True)
    _draw_text(
        surface,
        "<",
        (112, 320),
        CREAM,
        fonts.large,
        centered=True,
    )
    _draw_car(
        surface,
        294,
        420,
        190,
        (255, 205, 83),
        player=True,
        car_type=car_type,
    )
    _draw_text(
        surface,
        car_type.name,
        (294, 458),
        (242, 241, 221),
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        f"{selected_index + 1:02d} / {len(CAR_TYPES):02d}",
        (294, 504),
        GOLD,
        fonts.normal,
        centered=True,
    )
    _draw_text(
        surface,
        "LAPS TO RACE",
        (294, 540),
        GOLD,
        fonts.small,
        centered=True,
    )
    _draw_text(
        surface,
        f"<  {lap_count:02d} LAPS  >",
        (294, 562),
        (242, 241, 221),
        fonts.normal,
        centered=True,
    )
    _draw_text(
        surface,
        ">",
        (474, 320),
        CREAM,
        fonts.large,
        centered=True,
    )
    _draw_text(
        surface,
        "UP/DOWN OPTION  LEFT/RIGHT VALUE  ARROWS / D-PAD  ENTER START",
        (SCREEN_WIDTH // 2, 612),
        CREAM,
        fonts.small,
        centered=True,
    )
    _draw_track_map(
        surface,
        track,
        0.0,
        f"TRACK {track_index + 1:02d} / {len(TRACKS):02d}",
        fonts,
        SELECTION_MAP_RECT,
        highlighted=active_option == 1,
    )


def draw_frame(
    surface: pygame.Surface,
    state: GameState,
    fonts: Fonts,
    car_type: CarType = DEFAULT_CAR_TYPE,
) -> None:
    """Draw one complete frame onto a surface without presenting it."""
    _draw_background(surface, state.distance, state.track)
    _draw_road(surface, state.distance, state.track, state.lateral)
    _draw_start_line(surface, state.distance, state.track, state.lateral)
    _draw_traffic(surface, state, car_type)

    player_coordinates = _camera_coordinates(
        _race_camera(state.distance, state.track, state.lateral),
        _world_track_point(
            state.distance, state.lateral * ROAD_HALF_WIDTH, state.track
        ),
    )
    player_x, player_y = _project_camera_point(player_coordinates)
    player_color = (255, 205, 83) if state.crash_time <= 0 else (255, 116, 89)
    _draw_car(
        surface,
        player_x,
        player_y,
        1.8 * FOCAL_LENGTH / player_coordinates[2],
        player_color,
        player=True,
        car_type=car_type,
    )
    _draw_hud(surface, state, fonts)
    _draw_start_lights(surface, state)
    _draw_track_map(
        surface,
        state.track,
        state.distance,
        _track_map_subtitle(state.track, state.distance, state.lap_count),
        fonts,
        lateral=state.lateral,
    )
    if state.game_over:
        _draw_game_over(surface, state, fonts)
