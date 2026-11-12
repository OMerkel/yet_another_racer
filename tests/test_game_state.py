"""Tests for deterministic state transitions and vehicle physics."""

import math
import unittest
from dataclasses import replace

from src.racer.game_state import (
    CAR_TYPES,
    DEFAULT_LAP_COUNT,
    GRID_START_DISTANCE,
    LAP_OPTIONS,
    MAX_SPEED,
    START_LIGHTS_DURATION,
    START_SPEED,
    new_game,
    step_game,
)
from src.racer.input import DriveInput
from src.racer.track import HOCKENHEIM, TRACKS, Track, sample_track


class GameStateTests(unittest.TestCase):
    """Verify pure state transitions for race progression."""

    def setUp(self):
        segment = HOCKENHEIM.segments[0]
        segments = tuple(
            replace(
                segment,
                distance=index * 1000.0,
                length=1000.0,
                x=0.0,
                z=index * 1000.0,
                heading=0.0,
                curvature=0.0,
                elevation=0.0,
                grade=0.0,
            )
            for index in range(2)
        )
        self.straight_track = replace(
            HOCKENHEIM,
            length=2000.0,
            segments=segments,
            segment_starts=(0.0, 1000.0),
            bounds=(0.0, 0.0, 0.0, 1000.0),
        )

    def active_state(
        self,
        track: Track | None = None,
        lap_count: int = DEFAULT_LAP_COUNT,
        distance: float = 0.0,
        speed: float = START_SPEED,
        lateral: float = 0.0,
    ):
        """Build a countdown-free state on the straight test track."""
        selected_track = self.straight_track if track is None else track
        return replace(
            new_game(selected_track, lap_count),
            countdown=0.0,
            distance=distance,
            speed=speed,
            lateral=lateral,
        )

    def test_step_returns_new_state_and_preserves_previous_state(self):
        """TST-005; NFR-002.

        FEATURE: Simulation determinism
        SCENARIO: Advance a race without mutating its input snapshot
        GIVEN an immutable initial race state
        WHEN one simulation step is evaluated
        THEN a replacement state is returned and the input remains unchanged
        AND repeating the same step produces the same result
        """
        initial = self.active_state(speed=120.0)
        updated = step_game(initial, DriveInput(accelerate=1.0), 1.0)

        self.assertEqual(initial.speed, 120.0)
        self.assertEqual(initial.distance, 0.0)
        self.assertEqual(updated.speed, 154.0)
        self.assertGreater(updated.distance, initial.distance)
        self.assertEqual(
            updated, step_game(initial, DriveInput(accelerate=1.0), 1.0)
        )

    def test_top_speed_advances_in_meters_per_second(
        self,
    ):
        """TST-006; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Convert displayed km/h into world meters per second
        GIVEN a race at maximum vehicle speed
        WHEN one second of simulation elapses
        THEN distance advances by speed divided by 3.6
        AND vehicle speed remains capped at the maximum
        """
        initial = self.active_state(speed=MAX_SPEED)
        updated = step_game(initial, DriveInput(accelerate=1.0), 1.0)

        self.assertAlmostEqual(updated.distance, MAX_SPEED / 3.6)
        self.assertEqual(updated.speed, MAX_SPEED)

    def test_acceleration_is_linear_and_scaled_by_car_model(self):
        """TST-007; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Scale acceleration by throttle and selected car
        GIVEN an active race and Formula or Classic car
        WHEN half or full throttle is applied
        THEN acceleration is linear and car-specific
        """
        initial = self.active_state(speed=120.0)
        half_throttle = step_game(initial, DriveInput(accelerate=0.5), 1.0)
        f1_full_throttle = step_game(initial, DriveInput(accelerate=1.0), 1.0)
        simple_full_throttle = step_game(
            initial,
            DriveInput(accelerate=1.0),
            1.0,
            car_type=CAR_TYPES[1],
        )

        self.assertEqual(CAR_TYPES[0].acceleration, 1.0)
        self.assertEqual(CAR_TYPES[1].acceleration, 0.7)
        self.assertEqual(half_throttle.speed, 133.0)
        self.assertEqual(f1_full_throttle.speed, 154.0)
        self.assertEqual(simple_full_throttle.speed, 141.4)

    def test_brake_strength_scales_deceleration(self):
        """TST-008; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Scale braking deceleration by input and selected car
        GIVEN a moving race car
        WHEN half or full braking is applied
        THEN deceleration reflects brake input and the car's braking factor
        AND speed cannot fall below zero
        """
        initial = self.active_state(speed=200.0)
        half_brake = step_game(initial, DriveInput(brake=0.5), 1.0)
        full_brake = step_game(initial, DriveInput(brake=1.0), 1.0)
        simple_brake = step_game(
            initial,
            DriveInput(brake=1.0),
            1.0,
            car_type=CAR_TYPES[1],
        )

        self.assertEqual(CAR_TYPES[0].braking, 1.0)
        self.assertEqual(CAR_TYPES[1].braking, 0.8)
        self.assertEqual(half_brake.speed, 142.0)
        self.assertEqual(full_brake.speed, 92.0)
        self.assertEqual(simple_brake.speed, 112.0)
        self.assertEqual(
            step_game(
                self.active_state(speed=10.0),
                DriveInput(brake=1.0),
                1.0,
            ).speed,
            0.0,
        )

    def test_steering_strength_scales_with_speed(self):
        """TST-009; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Scale steering response with vehicle speed
        GIVEN stationary, moderate-speed, and maximum-speed states
        WHEN the same steering input is applied
        THEN the stationary car does not move laterally
        AND lateral steering response increases with speed
        AND extreme steering remains within the road-position bounds
        """
        stationary = self.active_state(speed=0.0)
        moderate_speed = self.active_state(speed=150.0)
        full_speed = self.active_state(speed=MAX_SPEED)

        stopped_turn = step_game(stationary, DriveInput(steering=1.0), 0.1)
        moderate_turn = step_game(moderate_speed, DriveInput(steering=1.0), 0.1)
        fast_turn = step_game(full_speed, DriveInput(steering=1.0), 0.1)
        bounded_turn = step_game(full_speed, DriveInput(steering=1.0), 10.0)

        self.assertEqual(stopped_turn.lateral, 0.0)
        self.assertGreater(moderate_turn.lateral, 0.0)
        self.assertGreater(fast_turn.lateral, moderate_turn.lateral)
        self.assertLess(fast_turn.lateral, 0.2)
        self.assertEqual(bounded_turn.lateral, 1.12)

    def test_lap_limit_ends_race_at_the_finish_line(self):
        """TST-010; FR-007, NFR-002.

        FEATURE: Lap race completion
        SCENARIO: End a race exactly at the selected lap target
        GIVEN races at each supported lap count one meter from the finish
        WHEN the car advances past the finish distance
        THEN each distance is clamped to its selected lap target
        AND the race ends
        AND subsequent steps leave the completed state unchanged
        """
        for lap_count in LAP_OPTIONS:
            finish_distance = self.straight_track.length * lap_count
            initial = self.active_state(
                lap_count=lap_count,
                distance=finish_distance - 1,
                speed=60.0,
            )
            updated = step_game(initial, DriveInput(), 1.0)

            self.assertTrue(updated.game_over)
            self.assertEqual(updated.distance, finish_distance)
            self.assertIs(
                step_game(updated, DriveInput(), 0.1),
                updated,
            )

    def test_default_lap_count_is_an_available_option(self):
        """TST-033; FR-013.

        FEATURE: Lap-count race options
        SCENARIO: Start with a supported default number of laps
        GIVEN the default race configuration
        WHEN a new game is created
        THEN the selected lap count is available in the options list
        """
        self.assertEqual(DEFAULT_LAP_COUNT, 3)
        self.assertIn(DEFAULT_LAP_COUNT, LAP_OPTIONS)
        state = new_game()
        self.assertEqual(state.lap_count, DEFAULT_LAP_COUNT)
        self.assertEqual(state.speed, 0.0)
        self.assertEqual(state.distance, -GRID_START_DISTANCE)
        self.assertEqual(state.countdown, START_LIGHTS_DURATION)

    def test_grid_start_holds_controls_until_countdown_finishes(self):
        """TST-040; FR-007.

        FEATURE: Race start lights
        SCENARIO: Keep the grid car stationary during the red-light sequence
        GIVEN a new race with the car positioned before the start line
        WHEN throttle and steering are held during the countdown
        THEN speed, distance, lateral position and heading remain unchanged
        AND movement begins on the first frame after the countdown
        """
        state = new_game(self.straight_track)
        start_distance = state.distance
        controls = DriveInput(accelerate=1.0, steering=1.0)

        for _ in range(50):
            state = step_game(state, controls, 0.1)

        self.assertEqual(state.countdown, 0.0)
        self.assertEqual(state.speed, 0.0)
        self.assertEqual(state.distance, start_distance)
        self.assertEqual(state.lateral, 0.0)
        self.assertEqual(state.heading_error, 0.0)

        state = step_game(state, controls, 0.1)
        self.assertGreater(state.speed, 0.0)
        self.assertGreater(state.distance, start_distance)

    def test_curbs_are_drivable_and_grass_has_moderate_drag(self):
        """TST-034; FR-005.

        FEATURE: Road-surface handling
        SCENARIO: Distinguish curbs from grass off the circuit
        GIVEN otherwise identical cars on the road, curb, and grass
        WHEN neutral throttle physics is applied briefly
        THEN curb position preserves road speed
        AND grass reduces speed without forcing a stop
        """
        on_road = self.active_state(speed=120.0)
        curb = replace(on_road, lateral=1.05)
        grass = replace(on_road, lateral=1.12)
        road_result = step_game(on_road, DriveInput(), 0.1)
        curb_result = step_game(curb, DriveInput(), 0.1)
        grass_result = step_game(grass, DriveInput(), 0.1)

        self.assertEqual(curb_result.speed, road_result.speed)
        self.assertLess(grass_result.speed, curb_result.speed)
        self.assertGreater(grass_result.speed, 0)

    def test_full_throttle_can_recover_from_grass_at_rest(self):
        """TST-036; FR-005.

        FEATURE: Off-road recovery
        SCENARIO: Accelerate and steer back from a stopped grass position
        GIVEN a car stopped just beyond the grass boundary on either circuit
        WHEN full throttle and inward steering are applied
        THEN the car gains speed and returns inside the road boundary
          within two seconds
        """
        for track in TRACKS:
            state = self.active_state(track=track, speed=0.0, lateral=1.12)
            controls = DriveInput(accelerate=1.0, steering=-1.0)
            for _ in range(40):
                state = step_game(state, controls, 0.05)
                if state.lateral <= 1.1:
                    break

            self.assertGreater(state.speed, 0.0)
            self.assertLessEqual(state.lateral, 1.1)

    def test_neutral_controls_do_not_drift_on_a_straight(self):
        """TST-029; FR-005.

        FEATURE: Geometry-based handling
        SCENARIO: Drive straight without synthetic sideways forces
        GIVEN a moving car aligned with a straight road
        WHEN neutral steering is held across multiple frames
        THEN no lateral or heading error accumulates
        """
        state = self.active_state()
        for _ in range(60):
            state = step_game(state, DriveInput(), 1 / 60)
        self.assertAlmostEqual(state.lateral, 0.0)
        self.assertAlmostEqual(state.heading_error, 0.0)
        stopped_offroad = replace(state, speed=0.0, lateral=1.0)
        self.assertEqual(
            step_game(stopped_offroad, DriveInput(), 0.1).speed, 0.0
        )

    def test_cornering_responds_to_the_selected_track(self):
        """TST-030; FR-005.

        FEATURE: Geometry-based handling
        SCENARIO: Resist a bend using steering rather than sine-wave drift
        GIVEN an aligned moving car in a curved segment of either circuit
        WHEN the car advances without steering
        THEN its heading error opposes the actual road's heading change
        """
        for track in TRACKS:
            segment = max(track.segments, key=lambda item: abs(item.curvature))
            state = self.active_state(
                track=track, distance=segment.distance, speed=60
            )
            updated = step_game(state, DriveInput(), 0.01)
            before = sample_track(state.distance, track)
            after = sample_track(updated.distance, track)
            road_turn = math.atan2(
                math.sin(after.heading - before.heading),
                math.cos(after.heading - before.heading),
            )
            self.assertAlmostEqual(updated.heading_error, -road_turn)

    def test_steering_can_hold_a_typical_tight_turn_at_low_speed(self):
        """TST-038; FR-005.

        FEATURE: Controllable cornering
        SCENARIO: Hold the centerline through a representative tight bend
        GIVEN an aligned car at 30 km/h on either circuit's 95th-percentile bend
        WHEN maximum steering is applied into the curve for half a second
        THEN heading error remains bounded and the car stays near the centerline
        """
        for track in TRACKS:
            segments = sorted(
                track.segments, key=lambda segment: abs(segment.curvature)
            )
            segment = segments[int(0.95 * (len(segments) - 1))]
            steering = 1.0 if segment.curvature > 0 else -1.0
            state = self.active_state(
                track=track, distance=segment.distance, speed=30.0
            )

            for _ in range(10):
                state = step_game(state, DriveInput(steering=steering), 0.05)

            self.assertLess(abs(state.heading_error), 0.15)
            self.assertLess(abs(state.lateral), 0.25)


if __name__ == "__main__":
    unittest.main()
