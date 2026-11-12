"""Tests for keyboard, gamepad, and options-screen input mappings."""

import unittest
from collections import defaultdict
from unittest.mock import Mock, patch

import pygame

from src.racer.input import (
    DriveInput,
    InputAction,
    InputHandler,
    action_for_event,
    combine_controls,
    gamepad_controls,
    keyboard_controls,
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
        self.assertEqual(
            gamepad_controls((0.25, 0.0, 0.0, 0.0, -1.0, -1.0)),
            DriveInput(steering=0.25),
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

    def test_input_handler_reads_left_stick_and_dpad_steering(self):
        """TST-037; FR-002.

        FEATURE: Gamepad driving input
        SCENARIO: Read steering from analog stick or digital pad
        GIVEN an initialized gamepad with six axes and a D-pad
        WHEN held controls are polled during a race
        THEN left-stick X and D-pad X both produce steering input
        """
        joystick = Mock()
        axes = [0.65, 0.0, 0.0, 0.0, -1.0, -1.0]
        joystick.get_numaxes.return_value = len(axes)

        def axis_value(index: int) -> float:
            return axes[index]

        joystick.get_axis.side_effect = axis_value
        joystick.get_numhats.return_value = 1
        joystick.get_hat.return_value = (0, 0)
        display_was_initialized = pygame.display.get_init()
        if not display_was_initialized:
            pygame.display.init()
        with (
            patch("pygame.joystick.get_count", return_value=1),
            patch("pygame.joystick.Joystick", return_value=joystick),
        ):
            handler = InputHandler()

        try:
            self.assertEqual(handler.read_controls().steering, 0.65)
            axes[0] = 0.0
            joystick.get_hat.return_value = (-1, 0)
            self.assertEqual(handler.read_controls().steering, -1.0)
        finally:
            handler.close()
            if not display_was_initialized:
                pygame.display.quit()

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
        previous_value = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT)
        next_value = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        start = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        gamepad_start_events = tuple(
            pygame.event.Event(pygame.JOYBUTTONDOWN, button=button)
            for button in (0, 1, 2, 3, 10)
        )
        unrelated_button = pygame.event.Event(pygame.JOYBUTTONDOWN, button=6)

        self.assertEqual(
            action_for_event(previous_value, False, selecting_car=True),
            InputAction.PREVIOUS_VALUE,
        )
        self.assertEqual(
            action_for_event(next_value, False, selecting_car=True),
            InputAction.NEXT_VALUE,
        )
        self.assertEqual(
            action_for_event(start, False, selecting_car=True),
            InputAction.START,
        )
        self.assertEqual(
            action_for_event(previous_value, False), InputAction.NONE
        )
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

    def test_gamepad_stick_changes_option_value_once_per_deflection(self):
        """TST-004; FR-004, FR-013.

        FEATURE: Race option navigation
        SCENARIO: Require a neutral stick before changing the option value again
        GIVEN the selection stick is deflected
        WHEN it remains deflected and then returns to neutral
        THEN only the first deflection changes the selected value
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
                InputAction.NEXT_VALUE,
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
                InputAction.PREVIOUS_VALUE,
            )
        finally:
            handler.close()

    def test_option_navigation_uses_arrows_stick_and_dpad(self):
        """TST-024; FR-004, FR-012, FR-013.

        FEATURE: Race option navigation
        SCENARIO: Navigate categories and values with directional controls
        GIVEN the pre-race options screen is active
        WHEN arrows, stick axes, or the D-pad are moved
        THEN vertical input changes the highlighted category
        AND horizontal input changes its value
        """
        events = (
            (
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP),
                InputAction.PREVIOUS_OPTION,
            ),
            (
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN),
                InputAction.NEXT_OPTION,
            ),
            (
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT),
                InputAction.PREVIOUS_VALUE,
            ),
            (
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT),
                InputAction.NEXT_VALUE,
            ),
            (
                pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=-0.8),
                InputAction.PREVIOUS_OPTION,
            ),
            (
                pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.8),
                InputAction.NEXT_OPTION,
            ),
            (
                pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.25),
                InputAction.NONE,
            ),
            (
                pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=-0.8),
                InputAction.PREVIOUS_VALUE,
            ),
            (
                pygame.event.Event(pygame.JOYAXISMOTION, axis=0, value=0.8),
                InputAction.NEXT_VALUE,
            ),
            (
                pygame.event.Event(pygame.JOYHATMOTION, value=(0, 1)),
                InputAction.PREVIOUS_OPTION,
            ),
            (
                pygame.event.Event(pygame.JOYHATMOTION, value=(0, -1)),
                InputAction.NEXT_OPTION,
            ),
            (
                pygame.event.Event(pygame.JOYHATMOTION, value=(-1, 0)),
                InputAction.PREVIOUS_VALUE,
            ),
            (
                pygame.event.Event(pygame.JOYHATMOTION, value=(1, 0)),
                InputAction.NEXT_VALUE,
            ),
        )
        for event, expected in events:
            self.assertEqual(
                action_for_event(event, False, selecting_car=True), expected
            )
            self.assertEqual(action_for_event(event, False), InputAction.NONE)

    def test_option_stick_selection_requires_a_neutral_return(self):
        """TST-025; FR-004, FR-012, FR-013.

        FEATURE: Race option navigation
        SCENARIO: Prevent held stick input from skipping option categories
        GIVEN the left stick's Y axis moves outside the deadzone
        WHEN it remains deflected and then returns to neutral
        THEN one category change is emitted per deflection
        """
        with patch("pygame.joystick.get_count", return_value=0):
            handler = InputHandler()
        down = pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.8)
        neutral = pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.0)
        drift = pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.25)
        deliberate = pygame.event.Event(pygame.JOYAXISMOTION, axis=1, value=0.4)

        try:
            self.assertEqual(
                handler.process_event(drift, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(drift, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(deliberate, False, selecting_car=True),
                InputAction.NEXT_OPTION,
            )
            self.assertEqual(
                handler.process_event(deliberate, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(down, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(neutral, False, selecting_car=True),
                InputAction.NONE,
            )
            self.assertEqual(
                handler.process_event(down, False, selecting_car=True),
                InputAction.NEXT_OPTION,
            )
        finally:
            handler.close()


if __name__ == "__main__":
    unittest.main()
