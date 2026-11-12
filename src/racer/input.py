"""Keyboard and gamepad input contracts and adapters."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol, Sequence

import pygame

from .gamepad import LEFT_STICK_AXES, LEFT_TRIGGER_AXIS, RIGHT_TRIGGER_AXIS

MENU_STICK_DEADZONE = 0.35
CAR_SELECTION_BUTTONS = (0, 1, 2, 3, 10)


@dataclass(frozen=True)
class DriveInput:
    """Normalized controls consumed by the game-state transition."""

    accelerate: float = 0.0
    brake: float = 0.0
    steering: float = 0.0


class InputAction(Enum):
    """Discrete actions emitted by window and keyboard events."""

    NONE = auto()
    QUIT = auto()
    RESTART = auto()
    PREVIOUS_OPTION = auto()
    NEXT_OPTION = auto()
    PREVIOUS_VALUE = auto()
    NEXT_VALUE = auto()
    START = auto()


class KeyState(Protocol):
    """Indexed boolean key state supplied by Pygame or a test."""

    def __getitem__(self, key: int, /) -> bool: ...


def keyboard_controls(keys: KeyState) -> DriveInput:
    """Translate a Pygame key-state snapshot into normalized controls."""
    accelerate = float(keys[pygame.K_UP] or keys[pygame.K_w])
    brake = float(keys[pygame.K_DOWN] or keys[pygame.K_s])
    steering = float(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - float(
        keys[pygame.K_LEFT] or keys[pygame.K_a]
    )
    return DriveInput(accelerate, brake, steering)


def _axis_value(
    axes: Sequence[float], axis_index: int, default: float = 0.0
) -> float:
    """Return an axis value or neutral input when the device lacks it."""
    return axes[axis_index] if axis_index < len(axes) else default


def gamepad_controls(axes: Sequence[float]) -> DriveInput:
    """Map left-stick steering and trigger axes to normalized controls."""
    steering = _axis_value(axes, LEFT_STICK_AXES[0])
    brake_axis = _axis_value(axes, LEFT_TRIGGER_AXIS, default=-1.0)
    trigger_axis = _axis_value(axes, RIGHT_TRIGGER_AXIS, default=-1.0)
    brake = max(0.0, min(1.0, (brake_axis + 1.0) / 2.0))
    accelerate = max(0.0, min(1.0, (trigger_axis + 1.0) / 2.0))
    return DriveInput(accelerate=accelerate, brake=brake, steering=steering)


def combine_controls(*controls: DriveInput) -> DriveInput:
    """Combine control sources, clamping steering to its normalized range."""
    return DriveInput(
        accelerate=max(
            (control.accelerate for control in controls), default=0.0
        ),
        brake=max((control.brake for control in controls), default=0.0),
        steering=max(
            -1.0,
            min(1.0, sum(control.steering for control in controls)),
        ),
    )


def action_for_event(
    event: pygame.event.Event, game_over: bool, selecting_car: bool = False
) -> InputAction:
    """Map a window or keyboard event to a discrete game action."""
    if event.type == pygame.QUIT:
        return InputAction.QUIT
    if (
        event.type == pygame.JOYBUTTONDOWN
        and event.button in CAR_SELECTION_BUTTONS
    ):
        if selecting_car:
            return InputAction.START
        if game_over:
            return InputAction.RESTART
    if selecting_car and event.type == pygame.JOYHATMOTION:
        horizontal, vertical = event.value
        if vertical:
            return (
                InputAction.PREVIOUS_OPTION
                if vertical > 0
                else InputAction.NEXT_OPTION
            )
        if horizontal:
            return (
                InputAction.NEXT_VALUE
                if horizontal > 0
                else InputAction.PREVIOUS_VALUE
            )
    if (
        selecting_car
        and event.type == pygame.JOYAXISMOTION
        and event.axis in LEFT_STICK_AXES[:2]
    ):
        if abs(event.value) <= MENU_STICK_DEADZONE:
            return InputAction.NONE
        if event.axis == LEFT_STICK_AXES[0]:
            return (
                InputAction.NEXT_VALUE
                if event.value > 0
                else InputAction.PREVIOUS_VALUE
            )
        return (
            InputAction.NEXT_OPTION
            if event.value > 0
            else InputAction.PREVIOUS_OPTION
        )
    if event.type != pygame.KEYDOWN:
        return InputAction.NONE
    if event.key == pygame.K_ESCAPE:
        return InputAction.QUIT
    if selecting_car:
        if event.key == pygame.K_LEFT:
            return InputAction.PREVIOUS_VALUE
        if event.key == pygame.K_RIGHT:
            return InputAction.NEXT_VALUE
        if event.key == pygame.K_UP:
            return InputAction.PREVIOUS_OPTION
        if event.key == pygame.K_DOWN:
            return InputAction.NEXT_OPTION
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return InputAction.START
        return InputAction.NONE
    if event.key == pygame.K_r and game_over:
        return InputAction.RESTART
    return InputAction.NONE


class InputHandler:
    """Own gamepad lifecycle and poll/normalize keyboard and stick input."""

    def __init__(self):
        pygame.joystick.init()
        self._joystick = None
        self._selection_stick_engaged: set[int] = set()
        self._connect_first_available()

    def process_event(
        self,
        event: pygame.event.Event,
        game_over: bool,
        selecting_car: bool = False,
    ) -> InputAction:
        """Handle input-related events and return any discrete action."""
        action = action_for_event(event, game_over, selecting_car)
        if (
            event.type == pygame.JOYAXISMOTION
            and event.axis in LEFT_STICK_AXES[:2]
        ):
            if abs(event.value) <= MENU_STICK_DEADZONE:
                self._selection_stick_engaged.discard(event.axis)
            elif selecting_car and event.axis in self._selection_stick_engaged:
                action = InputAction.NONE
            else:
                self._selection_stick_engaged.add(event.axis)
        if event.type == pygame.JOYDEVICEADDED and self._joystick is None:
            self._connect(event.device_index)
        elif (
            event.type == pygame.JOYDEVICEREMOVED
            and self._joystick is not None
            and event.instance_id == self._joystick.get_instance_id()
        ):
            self._joystick = None
            self._connect_first_available()
        return action

    def read_controls(self) -> DriveInput:
        """Read and combine current keyboard and gamepad controls."""
        keyboard = keyboard_controls(pygame.key.get_pressed())
        if self._joystick is None:
            return keyboard

        axes = tuple(
            self._joystick.get_axis(index)
            for index in range(self._joystick.get_numaxes())
        )
        gamepad = gamepad_controls(axes)
        if self._joystick.get_numhats() > 0:
            horizontal_hat, _ = self._joystick.get_hat(0)
            if horizontal_hat:
                gamepad = combine_controls(
                    gamepad, DriveInput(steering=float(horizontal_hat))
                )
        return combine_controls(keyboard, gamepad)

    def close(self):
        """Release joystick resources owned by this handler."""
        if self._joystick is not None:
            self._joystick.quit()
            self._joystick = None
        pygame.joystick.quit()

    def _connect_first_available(self):
        if pygame.joystick.get_count() > 0:
            self._connect(0)

    def _connect(self, device_index: int):
        joystick = pygame.joystick.Joystick(device_index)
        self._joystick = joystick
