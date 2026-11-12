# pyright: reportPrivateUsage=false
"""Rendering tests that exercise internal geometry and drawing helpers."""

import math
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

import pygame

from src.racer.game_state import (
    CAR_TYPES,
    LAP_OPTIONS,
    START_LIGHT_COUNT,
    START_LIGHTS_DURATION,
    new_game,
)
from src.racer.rendering import (
    CAMERA_BACK,
    FOCAL_LENGTH,
    GOLD,
    MAP_RECT,
    NEAR_PLANE,
    SCREEN_SIZE,
    START_LINE_BOX_COLUMNS,
    START_LINE_BOX_ROWS,
    START_LIGHT_RED,
    _background_parallax_offsets,
    _camera_coordinates,
    _clip_near_plane,
    _draw_background,
    _draw_hud,
    _draw_road,
    _draw_start_lights,
    _draw_start_line,
    _draw_track_map,
    _draw_traffic,
    _project_camera_point,
    _race_camera,
    _track_map_position,
    _track_map_subtitle,
    _world_track_point,
    create_fonts,
    draw_car_selection,
    draw_frame,
)
from src.racer.rendering_geometry import ROAD_DRAW_DISTANCE
from src.racer.track import (
    HOCKENHEIM,
    NURBURGRING_GP,
    ROAD_HALF_WIDTH,
    TRACKS,
    sample_track,
)


class RenderingTests(unittest.TestCase):
    """Verify selected car visuals and road-responsive scenery."""

    def test_mountains_are_drawn_in_front_of_the_sun(self):
        """TST-011; FR-008.

        FEATURE: Game presentation
        SCENARIO: Draw mountain silhouettes over the sun
        GIVEN a surface on which the background is drawn
        WHEN a pixel where the sun and mountains overlap is inspected
        THEN the pixel has the mountain color
        """
        surface = pygame.Surface(SCREEN_SIZE)
        _draw_background(surface)

        self.assertEqual(
            surface.get_at((790, 140))[:3], (79, 98, 125)
        )

    def test_traffic_uses_selected_car_shape(self):
        """TST-012; FR-008.

        FEATURE: Game presentation
        SCENARIO: Draw traffic using the selected car shape
        GIVEN a race state and the Classic car selection
        WHEN traffic is drawn
        THEN every opponent car uses the selected car type
        """
        surface = pygame.Surface((960, 640))
        with patch("src.racer.rendering._draw_car") as draw_car:
            _draw_traffic(surface, new_game(), CAR_TYPES[1])

        self.assertTrue(draw_car.call_args_list)
        self.assertTrue(
            all(
                call.kwargs["car_type"] == CAR_TYPES[1]
                for call in draw_car.call_args_list
            )
        )

    def test_player_and_traffic_render_with_selected_car_width(self):
        """Both sprites use the same physical width as collision detection."""
        pygame.font.init()
        surface = pygame.Surface(SCREEN_SIZE)
        state = new_game()
        car_type = replace(CAR_TYPES[0], width=2.4)
        camera = _race_camera(state.distance, state.track, state.lateral)
        expected_widths = []
        for car in state.traffic:
            gap = car.distance - state.distance
            coordinates = _camera_coordinates(
                camera,
                _world_track_point(
                    car.distance, car.lane * ROAD_HALF_WIDTH, state.track
                ),
            )
            if 0 <= gap <= ROAD_DRAW_DISTANCE and coordinates[2] >= NEAR_PLANE:
                expected_widths.append(
                    car_type.width * FOCAL_LENGTH / coordinates[2]
                )
        player_coordinates = _camera_coordinates(
            camera,
            _world_track_point(
                state.distance, state.lateral * ROAD_HALF_WIDTH, state.track
            ),
        )
        expected_widths.append(
            car_type.width * FOCAL_LENGTH / player_coordinates[2]
        )
        with patch("src.racer.rendering._draw_car") as draw_car:
            draw_frame(surface, state, create_fonts(), car_type)

        self.assertGreater(len(expected_widths), 1)
        self.assertCountEqual(
            [call.args[3] for call in draw_car.call_args_list], expected_widths
        )

    def test_background_parallax_opposes_road_bend_by_depth(self):
        """TST-013; FR-008.

        FEATURE: Game presentation
        SCENARIO: Offset near and distant scenery against the road bend
        GIVEN a camera turning in either direction
        WHEN background parallax offsets are calculated
        THEN all three layers move opposite the turn
        AND the sun moves less than the far mountains
        AND the near layer moves more than the far layer
        """
        start = sample_track(0.0, HOCKENHEIM)
        for turn in (-0.5, 0.5):
            with patch(
                "src.racer.rendering.sample_track",
                return_value=replace(start, heading=start.heading + turn),
            ):
                sun, far, near = _background_parallax_offsets(0.0, HOCKENHEIM)

            self.assertLess(sun * turn, 0)
            self.assertLess(abs(sun), abs(far))
            self.assertLess(abs(far), abs(near))

    def test_background_scrolls_as_the_camera_turns(self):
        """Scenery scrolls through turns and repeats after a complete lap."""
        for track in TRACKS:
            start = _background_parallax_offsets(0.0, track)
            offsets = [
                _background_parallax_offsets(segment.distance, track)
                for segment in track.segments
            ]
            for layer in range(3):
                self.assertGreater(
                    max(offset[layer] for offset in offsets)
                    - min(offset[layer] for offset in offsets),
                    SCREEN_SIZE[0] // 2,
                )
            self.assertEqual(
                start, _background_parallax_offsets(track.length, track)
            )

    def test_background_tiles_cover_edges_and_wrap_without_gaps(self):
        """Repeating background tiles cover screen edges without gaps."""
        width, height = SCREEN_SIZE
        for offsets in ((0, 0, 0), (165, -437, 529), (-790, 170, -230)):
            surface = pygame.Surface(SCREEN_SIZE)
            repeated = pygame.Surface(SCREEN_SIZE)
            with patch(
                "src.racer.rendering._background_parallax_offsets",
                return_value=offsets,
            ):
                _draw_background(surface)
            with patch(
                "src.racer.rendering._background_parallax_offsets",
                return_value=tuple(offset + width for offset in offsets),
            ):
                _draw_background(repeated)

            self.assertEqual(
                pygame.image.tobytes(surface, "RGB"),
                pygame.image.tobytes(repeated, "RGB"),
            )
            for horizontal in range(width):
                self.assertEqual(
                    surface.get_at((horizontal, 200))[:3], (54, 83, 92)
                )
            self.assertEqual(
                surface.get_at((0, height - 1))[:3], (44, 126, 71)
            )
        self.assertEqual(surface.get_at((0, 100))[:3], (255, 206, 119))

    def test_background_is_continuous_at_heading_and_lap_boundaries(self):
        """Parallax stays continuous across wrapped headings and lap ends."""
        for track in TRACKS:
            distances = [-0.01, track.length - 0.01]
            distances.extend(
                following.distance - 0.01
                for segment, following in zip(
                    track.segments, track.segments[1:]
                )
                if abs(following.heading - segment.heading) > math.pi
            )
            for distance in distances:
                before = _background_parallax_offsets(distance, track)
                after = _background_parallax_offsets(distance + 0.02, track)
                for first, second in zip(before, after):
                    wrapped_delta = (
                        (second - first + SCREEN_SIZE[0] / 2) % SCREEN_SIZE[0]
                        - SCREEN_SIZE[0] / 2
                    )
                    self.assertLessEqual(abs(wrapped_delta), 1)

    def test_track_map_draws_the_circuit_and_current_position(self):
        """TST-020; FR-011.

        FEATURE: Circuit overview map
        SCENARIO: Draw the Hockenheim route and the player's position
        GIVEN a race state at the start/finish line
        WHEN the overview map is drawn
        THEN the route occupies its map area
        AND the player's position is highlighted
        """
        surface = pygame.Surface(SCREEN_SIZE)
        start = sample_track(0, HOCKENHEIM)
        marker = _track_map_position(start.x, start.z, HOCKENHEIM)
        with patch("src.racer.rendering._draw_text"):
            _draw_track_map(
                surface,
                HOCKENHEIM,
                0.0,
                "LAP 01  START/FINISH",
                Mock(),
            )

        self.assertEqual(surface.get_at(marker)[:3], GOLD)
        self.assertNotEqual(
            surface.get_at((MAP_RECT.centerx, MAP_RECT.centery))[:3],
            (0, 0, 0),
        )
        for track in TRACKS:
            for lateral in (-0.5, 0.5):
                world = _world_track_point(0, lateral * ROAD_HALF_WIDTH, track)
                marker = _track_map_position(world[0], world[2], track)
                with patch("src.racer.rendering._draw_text"):
                    _draw_track_map(
                        surface, track, 0.0, "LAP 01", Mock(), lateral=lateral
                    )
                self.assertEqual(surface.get_at(marker)[:3], GOLD)

    def test_car_selection_draws_the_selected_track_preview(self):
        """TST-026; FR-012.

        FEATURE: Pre-race track options
        SCENARIO: Preview the selected Nürburgring GP before the race
        GIVEN the Nürburgring is the second track option
        WHEN the car and track options screen is drawn
        THEN its minimap receives the Nürburgring geometry and option number
        """
        surface = pygame.Surface(SCREEN_SIZE)
        with (
            patch("src.racer.rendering._draw_text") as draw_text,
            patch("src.racer.rendering._draw_track_map") as draw_track_map,
        ):
            draw_car_selection(
                surface,
                Mock(),
                CAR_TYPES[0],
                NURBURGRING_GP,
                1,
                5,
            )

        self.assertEqual(draw_track_map.call_args.args[1], NURBURGRING_GP)
        self.assertEqual(draw_track_map.call_args.args[3], "TRACK 02 / 02")
        self.assertIn(
            "<  05 LAPS  >",
            [call.args[1] for call in draw_text.call_args_list],
        )

    def test_start_line_draws_alternating_grid_tiles(self):
        """TST-041; FR-008, FR-014.

        FEATURE: Race start line
        SCENARIO: Draw a checkered line across the road in 3D perspective
        GIVEN the camera approaches Hockenheim's start line
        WHEN the start-line grid is drawn
        THEN two rows of black and white tiles span the road width
        """
        surface = pygame.Surface(SCREEN_SIZE)
        with patch("src.racer.rendering_geometry.draw_polygon") as draw_polygon:
            _draw_start_line(surface, -18.0, HOCKENHEIM)

        self.assertEqual(
            draw_polygon.call_count,
            START_LINE_BOX_COLUMNS * START_LINE_BOX_ROWS,
        )
        colors = {call.args[1] for call in draw_polygon.call_args_list}
        self.assertEqual(colors, {(245, 244, 235), (20, 23, 26)})

    def test_start_lights_extinguish_during_grid_countdown(self):
        """TST-042; FR-008, FR-014.

        FEATURE: Race start lights
        SCENARIO: Count down five red lights before releasing the car
        GIVEN a new race with a five-second countdown
        WHEN the lights are drawn at five, three, and zero seconds
        THEN five, three, and zero lights are illuminated
        """
        surface = pygame.Surface(SCREEN_SIZE)
        state = new_game(HOCKENHEIM)
        for remaining, expected in (
            (START_LIGHTS_DURATION, START_LIGHT_COUNT),
            (2.1, 3),
            (0.0, 0),
        ):
            with patch("pygame.draw.circle") as draw_circle:
                _draw_start_lights(surface, replace(state, countdown=remaining))
            lit_count = sum(
                call.args[1] == START_LIGHT_RED
                for call in draw_circle.call_args_list
            )
            self.assertEqual(lit_count, expected)

    def test_grid_hud_starts_on_lap_one_before_start_line(self):
        """TST-043; FR-008, FR-014.

        FEATURE: Grid start HUD
        SCENARIO: Show lap one while the car waits before the line
        GIVEN a new race with negative pre-start distance
        WHEN the race HUD is drawn
        THEN its lap counter starts at one, not zero
        """
        surface = pygame.Surface(SCREEN_SIZE)
        with patch("src.racer.rendering._draw_text") as draw_text:
            _draw_hud(surface, new_game(HOCKENHEIM), Mock())

        self.assertIn(
            "LAP 01/03",
            [call.args[1] for call in draw_text.call_args_list],
        )

    def test_race_map_sector_labels_fit_the_map_panel(self):
        """TST-027; FR-008, FR-012.

        FEATURE: Race map labels
        SCENARIO: Fit every selected circuit's sector caption
        GIVEN the race map's available subtitle width
        WHEN each track sector label is measured
        THEN every lap and sector caption fits inside the map panel
        """
        pygame.font.init()
        font = pygame.font.SysFont("consolas", 14, bold=True)
        max_width = MAP_RECT.width - 20

        for track in TRACKS:
            for lap_count in LAP_OPTIONS:
                for segment in track.segments:
                    subtitle = _track_map_subtitle(
                        track, segment.distance, lap_count
                    )
                    self.assertLessEqual(font.size(subtitle)[0], max_width)

    def test_near_road_segment_is_drawn_over_distant_grass(self):
        """TST-021; FR-008, FR-011.

        FEATURE: Perspective road rendering
        SCENARIO: Composite the road from the horizon toward the car
        GIVEN a frame with nearby road inside the screen bounds
        WHEN road segments are drawn
        THEN the near road surface remains visible over distant segments
        """
        surface = pygame.Surface(SCREEN_SIZE)
        _draw_background(surface)
        _draw_road(surface, 0)

        self.assertIn(
            surface.get_at((200, 638))[:3], {(66, 70, 77), (48, 51, 59)}
        )

    def test_road_edges_are_fixed_world_geometry(self):
        """TST-031; FR-008, FR-011, FR-012.

        FEATURE: Rigid road projection
        SCENARIO: Project fixed-width road edges through a moving camera
        GIVEN world-space edges sampled from both circuits
        WHEN the chase camera moves along those circuits
        THEN road width stays constant and perspective divides by forward depth
        AND the camera's player anchor stays at its fixed chase distance
        """
        for track in TRACKS:
            for segment in track.segments[::20]:
                distance = segment.distance
                left = _world_track_point(distance, -ROAD_HALF_WIDTH, track)
                right = _world_track_point(distance, ROAD_HALF_WIDTH, track)
                self.assertAlmostEqual(
                    math.dist(left, right), 2 * ROAD_HALF_WIDTH
                )
                camera = _race_camera(distance, track)
                anchor = _camera_coordinates(
                    camera, _world_track_point(distance, 0, track)
                )
                self.assertAlmostEqual(anchor[0], 0)
                self.assertAlmostEqual(anchor[2], CAMERA_BACK)
                self.assertAlmostEqual(_project_camera_point(anchor)[0], 480)
                fixed = _world_track_point(
                    distance + 30, ROAD_HALF_WIDTH, track
                )
                for movement in (0.0, 0.1, 1.0):
                    moved_camera = _race_camera(distance + movement, track)
                    local = _camera_coordinates(moved_camera, fixed)
                    if local[2] < NEAR_PLANE:
                        continue
                    screen_x, screen_y = _project_camera_point(local)
                    local_x = (screen_x - 480) * local[2] / FOCAL_LENGTH
                    local_y = (205 - screen_y) * local[2] / FOCAL_LENGTH
                    recovered_x = (
                        moved_camera.x
                        + math.cos(moved_camera.heading) * local_x
                        + math.sin(moved_camera.heading) * local[2]
                    )
                    recovered_z = (
                        moved_camera.z
                        - math.sin(moved_camera.heading) * local_x
                        + math.cos(moved_camera.heading) * local[2]
                    )
                    self.assertAlmostEqual(recovered_x, fixed[0])
                    self.assertAlmostEqual(recovered_z, fixed[2])
                    self.assertAlmostEqual(
                        moved_camera.elevation + local_y, fixed[1]
                    )
        near = _project_camera_point((1, 0, 10))
        far = _project_camera_point((1, 0, 20))
        self.assertAlmostEqual(near[0] - 480, FOCAL_LENGTH / 10)
        self.assertAlmostEqual(near[0] - 480, 2 * (far[0] - 480))

    def test_road_polygons_are_clipped_before_projection(self):
        """TST-032; FR-008.

        FEATURE: Rigid road projection
        SCENARIO: Clip a road polygon that crosses behind the camera
        GIVEN a polygon straddling the near plane
        WHEN the polygon is clipped
        THEN all remaining vertices have a safe positive forward depth
        """
        clipped = _clip_near_plane(
            [(-1, 0, -2), (1, 0, -2), (1, 0, 5), (-1, 0, 5)]
        )
        self.assertEqual(len(clipped), 4)
        self.assertTrue(all(point[2] >= NEAR_PLANE for point in clipped))

    def test_start_line_draws_alternating_world_space_grid_boxes(self):
        """TST-041; FR-008, FR-014.

        FEATURE: Race start line
        SCENARIO: Draw the checkered start line in 3D perspective
        GIVEN the player is 18 meters before the start line
        WHEN the start line is rendered
        THEN two rows of alternating black and white boxes cross the road
        """
        surface = pygame.Surface(SCREEN_SIZE)
        with patch("src.racer.rendering_geometry.draw_polygon") as draw_polygon:
            _draw_start_line(surface, -18.0, HOCKENHEIM)

        self.assertEqual(
            draw_polygon.call_count,
            START_LINE_BOX_COLUMNS * START_LINE_BOX_ROWS,
        )
        colors = {call.args[1] for call in draw_polygon.call_args_list}
        self.assertEqual(colors, {(245, 244, 235), (20, 23, 26)})

    def test_start_lights_count_down_from_five_to_zero(self):
        """TST-042; FR-008, FR-014.

        FEATURE: Race start lights
        SCENARIO: Extinguish five red lights during the stationary countdown
        GIVEN a new race before the start
        WHEN the countdown reaches five, three, and zero seconds
        THEN five, three, and zero red lights are shown respectively
        """
        surface = pygame.Surface(SCREEN_SIZE)
        state = new_game(HOCKENHEIM)
        for remaining, expected in (
            (START_LIGHTS_DURATION, START_LIGHT_COUNT),
            (2.1, 3),
            (0.0, 0),
        ):
            with patch("pygame.draw.circle") as draw_circle:
                _draw_start_lights(surface, replace(state, countdown=remaining))
            lit_count = sum(
                call.args[1] == START_LIGHT_RED
                for call in draw_circle.call_args_list
            )
            self.assertEqual(lit_count, expected)
