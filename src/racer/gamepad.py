"""Shared joystick input, extracted from the reviewed gamepad visualizer."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from src.racer.gamepad_sensors import (
    ACCELEROMETER,
    GYROSCOPE,
    SDLControllerSensors,
    SensorController,
)

LEFT_STICK_AXES = (0, 1)
RIGHT_STICK_AXES = (2, 3)
LEFT_TRIGGER_AXIS = 4
RIGHT_TRIGGER_AXIS = 5


@dataclass
class GamepadState:
    """A snapshot of all raw controls on one device."""

    name: str
    axes: list[float]
    buttons: list[bool]
    hats: list[tuple[int, int]]
    accelerometer: tuple[float, float, float] | None = None
    gyroscope: tuple[float, float, float] | None = None

    @classmethod
    def read(
        cls,
        joystick: pygame.joystick.JoystickType,
        accelerometer: tuple[float, float, float] | None = None,
        gyroscope: tuple[float, float, float] | None = None,
    ) -> GamepadState:
        """Poll after pumping events so held controls remain highlighted."""

        return cls(
            joystick.get_name(),
            [
                joystick.get_axis(index)
                for index in range(joystick.get_numaxes())
            ],
            [
                bool(joystick.get_button(index))
                for index in range(joystick.get_numbuttons())
            ],
            [
                (int(x_value), int(y_value))
                for x_value, y_value in (
                    joystick.get_hat(index)
                    for index in range(joystick.get_numhats())
                )
            ],
            accelerometer,
            gyroscope,
        )

    def axis(self, index: int) -> float:
        """Return a centered value for controls absent on smaller devices."""

        return self.axes[index] if index < len(self.axes) else 0.0

    def pressed(self, index: int) -> bool:
        """Report whether a present button is held."""

        return index < len(self.buttons) and self.buttons[index]


@dataclass
class Gamepads:
    """Own open joysticks and track connection changes by instance ID."""

    devices: dict[int, pygame.joystick.JoystickType] = field(
        default_factory=dict[int, pygame.joystick.JoystickType]
    )
    resting_axes: dict[int, list[float]] = field(
        default_factory=dict[int, list[float]]
    )
    sensor_controllers: dict[int, SensorController] = field(
        default_factory=dict[int, SensorController]
    )
    sensor_reader: SDLControllerSensors = field(
        default_factory=SDLControllerSensors, repr=False
    )

    def open_connected(self) -> None:
        """Open devices already attached when the application starts."""

        for index in range(pygame.joystick.get_count()):
            self.add_device(index)

    def add_device(self, device_index: int) -> None:
        """Register a joystick using its stable connection instance ID."""

        joystick = pygame.joystick.Joystick(device_index)
        instance_id = joystick.get_instance_id()
        if instance_id in self.devices:
            return
        self.devices[instance_id] = joystick
        pygame.event.pump()
        self.resting_axes[instance_id] = GamepadState.read(joystick).axes
        sensor_controller = self.sensor_reader.open(device_index)
        if sensor_controller is not None:
            self.sensor_controllers[instance_id] = sensor_controller
        print(f"Connected: {joystick.get_name()} (ID {instance_id})")

    def read_state(self, instance_id: int) -> GamepadState:
        """Read raw controls and any available motion sensors."""

        joystick = self.devices[instance_id]
        controller = self.sensor_controllers.get(instance_id)
        return GamepadState.read(
            joystick,
            self.sensor_reader.read(controller, ACCELEROMETER),
            self.sensor_reader.read(controller, GYROSCOPE),
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        """Open newly attached controllers and close removed controllers."""

        if event.type == pygame.JOYDEVICEADDED:
            self.add_device(event.device_index)
        elif event.type == pygame.JOYDEVICEREMOVED:
            joystick = self.devices.pop(event.instance_id, None)
            if joystick is not None:
                print(f"Disconnected: ID {event.instance_id}")
                sensor_controller = self.sensor_controllers.pop(
                    event.instance_id, None
                )
                if sensor_controller is not None:
                    self.sensor_reader.close(sensor_controller)
                joystick.quit()
                del self.resting_axes[event.instance_id]

    def left_sticks(self) -> dict[int, list[float]]:
        """Poll current left-stick values, including holds and releases."""

        axes: dict[int, list[float]] = {}
        for instance_id, joystick in self.devices.items():
            snapshot = GamepadState.read(joystick)
            axes[instance_id] = [
                snapshot.axis(axis) for axis in LEFT_STICK_AXES
            ]
        return axes

    def close(self) -> None:
        """Release every open controller when either application exits."""

        for sensor_controller in self.sensor_controllers.values():
            self.sensor_reader.close(sensor_controller)
        self.sensor_controllers.clear()
        for joystick in self.devices.values():
            joystick.quit()
        self.devices.clear()
        self.resting_axes.clear()
