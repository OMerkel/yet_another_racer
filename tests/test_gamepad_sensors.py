"""Tests for controller motion-sensor access and smoothing."""

import unittest
from typing import Any
from unittest.mock import Mock

from src.racer.gamepad_sensors import (
    ACCELEROMETER,
    GYROSCOPE,
    SDLControllerSensors,
    SensorSmoother,
)


class GamepadSensorTests(unittest.TestCase):
    """Verify SDL motion sensor access for the gamepad visualizer."""

    def test_sdl_controller_sensors_are_enabled_and_read(self):
        """TST-015; FR-009.

        FEATURE: Raw gamepad diagnostic
        SCENARIO: Read motion sensors from a supported controller
        GIVEN SDL reports accelerometer and gyroscope sensors
        WHEN the visualizer reads the controller sensors
        THEN both three-axis values are available in their native units
        """
        sdl = Mock()
        sdl.SDL_GameControllerOpen.return_value = 23
        sdl.SDL_GameControllerHasSensor.return_value = 1
        sdl.SDL_GameControllerSetSensorEnabled.return_value = 0

        def fill_sensor_data(
            _handle: int, sensor_type: int, values: Any, count: int
        ) -> int:
            sample = (
                (1.0, 2.0, 3.0)
                if sensor_type == ACCELEROMETER
                else (
                    4.0,
                    5.0,
                    6.0,
                )
            )
            for index in range(count):
                values[index] = sample[index]
            return 0

        sdl.SDL_GameControllerGetSensorData.side_effect = fill_sensor_data
        sensors = SDLControllerSensors(sdl)

        controller = sensors.open(0)
        self.assertIsNotNone(controller)
        if controller is None:
            self.fail("SDL did not return a sensor-capable controller")

        self.assertEqual(
            sensors.read(controller, ACCELEROMETER), (1.0, 2.0, 3.0)
        )
        self.assertEqual(sensors.read(controller, GYROSCOPE), (4.0, 5.0, 6.0))
        self.assertEqual(sdl.SDL_GameControllerSetSensorEnabled.call_count, 2)

        sensors.close(controller)
        sdl.SDL_GameControllerClose.assert_called_once_with(23)

    def test_sensor_smoother_reduces_sample_jumps(self):
        """TST-016; FR-009.

        FEATURE: Raw gamepad diagnostic
        SCENARIO: Smooth motion sensor readouts
        GIVEN an existing sensor sample
        WHEN a new sample arrives
        THEN the displayed value moves gradually toward the new sample
        """
        smoother = SensorSmoother(alpha=0.25)

        self.assertEqual(
            smoother.update(1, ACCELEROMETER, (0.0, 0.0, 9.8)),
            (0.0, 0.0, 9.8),
        )
        self.assertEqual(
            smoother.update(1, ACCELEROMETER, (4.0, 0.0, 9.8)),
            (1.0, 0.0, 9.8),
        )
        self.assertIsNone(smoother.update(1, ACCELEROMETER, None))
        self.assertEqual(
            smoother.update(1, ACCELEROMETER, (4.0, 0.0, 9.8)),
            (4.0, 0.0, 9.8),
        )


if __name__ == "__main__":
    unittest.main()
