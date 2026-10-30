"""Tests for pure game-state transitions and input mappings."""

import unittest
from collections import defaultdict
from dataclasses import replace
from unittest.mock import patch

import pygame

from src.racer.game_state import (
    CAR_TYPES,
    MAX_SPEED,
    RACE_SECONDS,
    START_SPEED,
    new_game,
    step_game,
)
from src.racer.input import (
    DriveInput,
    InputAction,
    InputHandler,
    action_for_event,
    combine_controls,
    gamepad_controls,
    keyboard_controls,
)
from src.racer.rendering import (
    SCREEN_SIZE,
    _background_parallax_offsets,
    _draw_background,
    _draw_traffic,
)


class InputContractTests(unittest.TestCase):
    """Verify that key and gamepad values map to the input contract."""

    def test_keyboard_controls_map_to_drive_contract(self):
        """TST-001; FR-001.

        FEATURE: Keyboard driving input
        SCENARIO: Map keyboard controls into the driving contract
        GIVEN held keyboard acceleration and steering keys
        WHEN the keyboard state is translated
        THEN controls contain normalized acceleration and steering
        """
        keys = defaultdict(bool, {pygame.K_w: True, pygame.K_d: True})

        self.assertEqual(
            keyboard_controls(keys),
            DriveInput(accelerate=True, steering=1.0),
        )

    def test_gamepad_axes_respect_deadzone_and_drive_directions(self):
        """TST-002; FR-002.

        FEATURE: Gamepad driving input
        SCENARIO: Map stick and trigger axes into normalized controls
        GIVEN gamepad axes at neutral, deadzone, and trigger positions
        WHEN the axes are translated
        THEN steering respects the deadzone and triggers map to 0..1
        """
        self.assertEqual(gamepad_controls(()), DriveInput())

        self.assertEqual(
            gamepad_controls((0.1, -0.8, 0.0, 0.0, -1.0, -1.0)),
            DriveInput(),
        )
        self.assertEqual(
            gamepad_controls((-0.7, 0.9, 0.0, 0.0, -1.0, -1.0)),
            DriveInput(steering=-0.7),
        )
        self.assertAlmostEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, -1.0, -0.83)).accelerate,
            0.085,
        )
        self.assertEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, -1.0, 0.0)),
            DriveInput(accelerate=0.5),
        )
        self.assertEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, -1.0, 1.0)),
            DriveInput(accelerate=1.0),
        )
        self.assertEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, -1.0, -1.0)),
            DriveInput(),
        )
        self.assertEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, 0.0, -1.0)),
            DriveInput(brake=0.5),
        )
        self.assertEqual(
            gamepad_controls((0.0, 0.0, 0.0, 0.0, 1.0, -1.0)),
            DriveInput(brake=1.0),
        )

    def test_keyboard_and_gamepad_controls_are_combined(self):
        """TST-014; FR-003.

        FEATURE: Combined driving input
        SCENARIO: Combine active keyboard and gamepad controls
        GIVEN both input sources provide driving controls
        WHEN their controls are combined
        THEN throttle and brake use their maximum values
        AND steering is summed and clamped to -1..1
        """
        self.assertEqual(
            combine_controls(
                DriveInput(accelerate=1.0, steering=0.8),
                DriveInput(brake=0.5, steering=0.6),
            ),
            DriveInput(accelerate=1.0, brake=0.5, steering=1.0),
        )

    def test_car_selection_actions_are_only_active_before_race(self):
        """TST-003; FR-004.

        FEATURE: Car selection and race actions
        SCENARIO: Map selection, start, and restart events
        GIVEN keyboard and gamepad events in selection or game-over mode
        WHEN each event is mapped to an action
        THEN only supported events produce the corresponding action
        """
        previous = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        next_car = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
        start = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        gamepad_start_events = tuple(
            pygame.event.Event(pygame.JOYBUTTONDOWN, button=button)
            for button in (0, 1, 2, 3, 10)
        )
        unrelated_button = pygame.event.Event(pygame.JOYBUTTONDOWN, button=4)

        self.assertEqual(
            action_for_event(previous, False, selecting_car=True),
            InputAction.PREVIOUS_CAR,
        )
        self.assertEqual(
            action_for_event(next_car, False, selecting_car=True),
            InputAction.NEXT_CAR,
        )
        self.assertEqual(
            action_for_event(start, False, selecting_car=True),
            InputAction.START,
        )
        self.assertEqual(action_for_event(previous, False), InputAction.NONE)
        for event in gamepad_start_events:
            self.assertEqual(
                action_for_event(event, False, selecting_car=True),
                InputAction.START,
            )
        self.assertEqual(
            action_for_event(unrelated_button, False, selecting_car=True),
            InputAction.NONE,
        )
        self.assertEqual(
            action_for_event(gamepad_start_events[0], False),
            InputAction.NONE,
        )
        for event in gamepad_start_events:
            self.assertEqual(action_for_event(event, True), InputAction.RESTART)

    def test_gamepad_stick_changes_car_once_per_deflection(self):
        """TST-004; FR-004.

        FEATURE: Car selection and race actions
        SCENARIO: Require neutral stick input before another selection step
        GIVEN the selection stick is deflected
        WHEN it remains deflected and then returns to neutral
        THEN only the first deflection changes the selected car
        AND a new deflection after neutral changes it again
        """
        with patch("pygame.joystick.get_count", return_value=0):
            handler = InputHandler()
        move_right = pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=0.8)
        neutral = pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=0.0)
        move_left = pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=-0.8)

        try:
            self.assertEqual(
                handler.process_event(move_right, False, selecting_car=True),
                InputAction.NEXT_CAR,
            )
            self.assertEqual(
                handler.process_event(move_right, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(neutral, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(move_left, False, selecting_car=True),
                InputAction.PREVIOUS_CAR,
            )
        finally:
            handler.close()


class GameStateTests(unittest.TestCase):
    """Verify pure state transitions for race progression."""

    def test_step_returns_new_state_and_preserves_previous_state(self):
        """TST-005; NFR-002.

        FEATURE: Simulation determinism
        SCENARIO: Advance a race without mutating its input snapshot
        GIVEN an immutable initial race state
        WHEN one simulation step is evaluated
        THEN a replacement state is returned and the input remains unchanged
        AND repeating the same step produces the same result
        """
        initial = new_game()
        updated = step_game(initial, DriveInput(accelerate=1.0), 1.0)

        self.assertEqual(initial.speed, START_SPEED)
        self.assertEqual(initial.distance, 0.0)
        self.assertEqual(updated.speed, 246.0)
        self.assertGreater(updated.distance, initial.distance)
        self.assertEqual(
            updated, step_game(initial, DriveInput(accelerate=1.0), 1.0)
        )

    def test_top_speed_advances_world_twice_as_fast_but_timer_stays_real_time(
        self,
    ):
        """TST-006; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Apply the top-speed world factor and real-time timer
        GIVEN a race at maximum vehicle speed
        WHEN one second of simulation elapses
        THEN distance advances at the maximum world-speed factor
        AND vehicle speed remains capped at the maximum
        AND the timer decreases by exactly one second
        """
        initial = replace(new_game(), speed=MAX_SPEED)
        updated = step_game(initial, DriveInput(accelerate=1.0), 1.0)

        self.assertAlmostEqual(updated.distance, 268.224)
        self.assertEqual(updated.speed, MAX_SPEED)
        self.assertEqual(updated.time_left, RACE_SECONDS - 1)

    def test_acceleration_is_linear_and_scaled_by_car_model(self):
        """TST-007; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Scale acceleration by throttle and selected car
        GIVEN an active race and Formula or Classic car
        WHEN half or full throttle is applied
        THEN acceleration is linear and car-specific
        """
        initial = new_game()
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
        self.assertEqual(half_throttle.speed, 176.0)
        self.assertEqual(f1_full_throttle.speed, 246.0)
        self.assertEqual(simple_full_throttle.speed, 204.0)

    def test_brake_strength_scales_deceleration(self):
        """TST-008; FR-005, NFR-002.

        FEATURE: Race simulation
        SCENARIO: Scale braking deceleration by input and selected car
        GIVEN a moving race car
        WHEN half or full braking is applied
        THEN deceleration reflects brake input and the car's braking factor
        AND speed cannot fall below zero
        """
        initial = replace(new_game(), speed=200.0)
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
        self.assertEqual(half_brake.speed, 96.0)
        self.assertEqual(full_brake.speed, 6.0)
        self.assertEqual(simple_brake.speed, 42.0)
        self.assertEqual(
            step_game(
                replace(new_game(), speed=10.0),
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
        stationary = replace(new_game(), speed=0.0)
        moderate_speed = replace(new_game(), speed=150.0)
        full_speed = replace(new_game(), speed=MAX_SPEED)

        stopped_turn = step_game(stationary, DriveInput(steering=1.0), 0.1)
        moderate_turn = step_game(moderate_speed, DriveInput(steering=1.0), 0.1)
        fast_turn = step_game(full_speed, DriveInput(steering=1.0), 0.1)
        bounded_turn = step_game(full_speed, DriveInput(steering=1.0), 10.0)

        self.assertEqual(stopped_turn.lateral, 0.0)
        self.assertGreater(moderate_turn.lateral, 0.0)
        self.assertGreater(fast_turn.lateral, moderate_turn.lateral)
        self.assertLess(fast_turn.lateral, 0.2)
        self.assertEqual(bounded_turn.lateral, 1.12)

    def test_timer_ends_race(self):
        """TST-010; FR-007, NFR-002.

        FEATURE: Race duration and completion
        SCENARIO: Mark a race complete when its timer expires
        GIVEN a race with less than one frame of time remaining
        WHEN a longer frame is simulated
        THEN time is clamped to zero and the race is marked game over
        AND subsequent steps leave the completed state unchanged
        """
        initial = replace(new_game(), time_left=0.1)
        updated = step_game(initial, DriveInput(), 0.2)

        self.assertTrue(updated.game_over)
        self.assertEqual(updated.time_left, 0.0)
        self.assertIs(
            step_game(updated, DriveInput(), 0.1),
            updated,
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

        self.assertEqual(surface.get_at((790, 140))[:3], (79, 98, 125))

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

    def test_background_parallax_opposes_road_bend_by_depth(self):
        """TST-013; FR-008.

        FEATURE: Game presentation
        SCENARIO: Offset near and distant scenery against the road bend
        GIVEN a positive road bend
        WHEN background parallax offsets are calculated
        THEN both layers move opposite the bend
        AND the near layer moves more than the far layer
        """
        far_offset, near_offset = _background_parallax_offsets(0.0)

        self.assertLess(far_offset, 0)
        self.assertLess(near_offset, far_offset)


if __name__ == "__main__":
    unittest.main()
