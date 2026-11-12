"""Camera projection and world-space road rendering helpers."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pygame

from .track import DEFAULT_TRACK, ROAD_HALF_WIDTH, Track, sample_track

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
HORIZON = 205
ROAD_LOOKAHEAD = 1050.0
CAMERA_HEIGHT = 4.5
CAMERA_BACK = 8.0
FOCAL_LENGTH = 700.0
NEAR_PLANE = 1.0
ROAD_DRAW_DISTANCE = 450.0
ROAD_SLICE_LENGTH = 3.0
START_LINE_BOX_COLUMNS = 24
START_LINE_BOX_ROWS = 2
START_LINE_BOX_DEPTH = 0.75
_ROAD_OFFSETS = (
    -ROAD_HALF_WIDTH - 0.6,
    -ROAD_HALF_WIDTH,
    -ROAD_HALF_WIDTH + 0.15,
    -0.07,
    0.0,
    0.07,
    ROAD_HALF_WIDTH - 0.15,
    ROAD_HALF_WIDTH,
    ROAD_HALF_WIDTH + 0.6,
)

ROAD = (66, 70, 77)
ROAD_DARK = (48, 51, 59)
CURB_RED = (222, 67, 57)
CREAM = (244, 224, 177)


@dataclass(frozen=True)
class Camera:
    """World-space chase camera with a level horizon."""

    x: float
    elevation: float
    z: float
    heading: float


def race_camera(distance: float, track: Track, lateral: float = 0.0) -> Camera:
    """Position the chase camera relative to the sampled race position."""
    position = sample_track(distance, track)
    offset = lateral * ROAD_HALF_WIDTH
    return Camera(
        x=position.x
        - math.sin(position.heading) * CAMERA_BACK
        + math.cos(position.heading) * offset,
        elevation=position.elevation + CAMERA_HEIGHT,
        z=position.z
        - math.cos(position.heading) * CAMERA_BACK
        - math.sin(position.heading) * offset,
        heading=position.heading,
    )


def camera_coordinates(
    camera: Camera, position: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Transform a world-space point into the camera's coordinate frame."""
    delta_x = position[0] - camera.x
    delta_z = position[2] - camera.z
    return (
        delta_x * math.cos(camera.heading) - delta_z * math.sin(camera.heading),
        position[1] - camera.elevation,
        delta_x * math.sin(camera.heading) + delta_z * math.cos(camera.heading),
    )


def project_camera_point(
    position: tuple[float, float, float],
) -> tuple[float, float]:
    """Project a camera-space point onto the screen."""
    scale = FOCAL_LENGTH / position[2]
    return SCREEN_WIDTH / 2 + position[0] * scale, HORIZON - position[1] * scale


def world_track_point(
    distance: float, offset: float, track: Track
) -> tuple[float, float, float]:
    """Return a centerline position shifted laterally by ``offset`` meters."""
    position = sample_track(distance, track)
    return (
        position.x + math.cos(position.heading) * offset,
        position.elevation,
        position.z - math.sin(position.heading) * offset,
    )


def clip_near_plane(
    points: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Clip a camera-space polygon to the visible side of the near plane."""
    clipped: list[tuple[float, float, float]] = []
    previous = points[-1]
    for current in points:
        if (previous[2] >= NEAR_PLANE) != (current[2] >= NEAR_PLANE):
            fraction = (NEAR_PLANE - previous[2]) / (current[2] - previous[2])
            clipped.append(
                (
                    previous[0] + fraction * (current[0] - previous[0]),
                    previous[1] + fraction * (current[1] - previous[1]),
                    NEAR_PLANE,
                )
            )
        if current[2] >= NEAR_PLANE:
            clipped.append(current)
        previous = current
    return clipped


def road_width(progress: float) -> float:
    """Return the projected road width at a perspective depth."""
    return (
        2
        * ROAD_HALF_WIDTH
        * FOCAL_LENGTH
        / (CAMERA_BACK + (1 - progress) * ROAD_LOOKAHEAD)
    )


def project_track_point(
    distance: float, progress: float, track: Track = DEFAULT_TRACK
) -> tuple[float, float, float]:
    """Project a point ahead on the track and return its track distance."""
    target_distance = distance + (1 - progress) * ROAD_LOOKAHEAD
    coordinates = camera_coordinates(
        race_camera(distance, track),
        world_track_point(target_distance, 0.0, track),
    )
    if coordinates[2] < NEAR_PLANE:
        return SCREEN_WIDTH / 2, HORIZON, target_distance
    screen_x, screen_y = project_camera_point(coordinates)
    return screen_x, screen_y, target_distance


def road_center(
    distance: float, progress: float, track: Track = DEFAULT_TRACK
) -> float:
    """Return the screen-space road center at a perspective depth."""
    return project_track_point(distance, progress, track)[0]


def draw_polygon(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    points: Sequence[tuple[float, float]],
) -> None:
    """Draw a polygon from floating-point screen coordinates."""
    pygame.draw.polygon(
        surface, color, [(round(x), round(y)) for x, y in points]
    )


def _draw_track_strip(
    surface: pygame.Surface,
    rows: dict[float, dict[float, tuple[float, float, float]]],
    distances: tuple[float, float],
    offsets: tuple[float, float],
    color: tuple[int, int, int],
) -> None:
    start, end = distances
    left, right = offsets
    points = [
        rows[along][offset]
        for along, offset in (
            (start, left),
            (start, right),
            (end, right),
            (end, left),
        )
    ]
    clipped = clip_near_plane(points)
    if len(clipped) >= 3:
        draw_polygon(
            surface, color, [project_camera_point(point) for point in clipped]
        )


def draw_road(
    surface: pygame.Surface,
    distance: float,
    track: Track = DEFAULT_TRACK,
    lateral: float = 0.0,
) -> None:
    """Render the road surface and edge markings around the player."""
    camera = race_camera(distance, track, lateral)
    first = math.floor((distance - CAMERA_BACK) / ROAD_SLICE_LENGTH)
    last = math.ceil((distance + ROAD_DRAW_DISTANCE) / ROAD_SLICE_LENGTH)
    rows: dict[float, dict[float, tuple[float, float, float]]] = {}
    for index in range(first, last + 1):
        along = index * ROAD_SLICE_LENGTH
        sample = sample_track(along, track)
        normal_x = math.cos(sample.heading)
        normal_z = -math.sin(sample.heading)
        rows[along] = {
            offset: camera_coordinates(
                camera,
                (
                    sample.x + normal_x * offset,
                    sample.elevation,
                    sample.z + normal_z * offset,
                ),
            )
            for offset in _ROAD_OFFSETS
        }
    slices: list[tuple[float, float, float]] = []
    for index in range(first, last):
        start = index * ROAD_SLICE_LENGTH
        end = start + ROAD_SLICE_LENGTH
        depth = (rows[start][0.0][2] + rows[end][0.0][2]) / 2
        if depth > NEAR_PLANE:
            slices.append((depth, start, end))
    for _, start, end in sorted(slices, reverse=True):
        distances = (start, end)
        stripe = int((start % track.length) // 36) % 2
        _draw_track_strip(
            surface,
            rows,
            distances,
            (-ROAD_HALF_WIDTH, ROAD_HALF_WIDTH),
            ROAD if stripe else ROAD_DARK,
        )
        curb = CURB_RED if int((start % track.length) // 3) % 2 else CREAM
        for side in (-1, 1):
            edge = side * ROAD_HALF_WIDTH
            _draw_track_strip(
                surface,
                rows,
                distances,
                (edge, edge + side * 0.6),
                curb,
            )
            _draw_track_strip(
                surface,
                rows,
                distances,
                (edge - side * 0.15, edge),
                CREAM,
            )
        if int((start % track.length) // 6) % 2 == 0:
            _draw_track_strip(surface, rows, distances, (-0.07, 0.07), CREAM)


def draw_start_line(
    surface: pygame.Surface,
    distance: float,
    track: Track,
    lateral: float = 0.0,
) -> None:
    """Draw a world-anchored checker grid at the next start line."""
    line_distance = math.ceil(distance / track.length) * track.length
    if line_distance - distance > ROAD_DRAW_DISTANCE:
        return

    camera = race_camera(distance, track, lateral)
    box_width = 2 * ROAD_HALF_WIDTH / START_LINE_BOX_COLUMNS
    box_depth = START_LINE_BOX_DEPTH / START_LINE_BOX_ROWS
    for row in range(START_LINE_BOX_ROWS):
        near_distance = line_distance - START_LINE_BOX_DEPTH + row * box_depth
        far_distance = near_distance + box_depth
        for column in range(START_LINE_BOX_COLUMNS):
            left = -ROAD_HALF_WIDTH + column * box_width
            right = left + box_width
            world_points = (
                world_track_point(near_distance, left, track),
                world_track_point(near_distance, right, track),
                world_track_point(far_distance, right, track),
                world_track_point(far_distance, left, track),
            )
            camera_points = [
                camera_coordinates(camera, point) for point in world_points
            ]
            clipped = clip_near_plane(camera_points)
            if len(clipped) >= 3:
                color = (
                    (245, 244, 235) if (row + column) % 2 == 0 else (20, 23, 26)
                )
                draw_polygon(
                    surface,
                    color,
                    [project_camera_point(point) for point in clipped],
                )
