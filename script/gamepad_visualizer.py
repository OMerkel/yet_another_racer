#!/usr/bin/env python3
"""Display live gamepad input on a pygame controller silhouette.

Run from the repository root with:
    uv run python -m script.gamepad_visualizer

Escape closes the window; Tab switches between connected gamepads.
The silhouette uses a common raw joystick layout, not a device-specific
mapping. Numbered readouts show every axis, button, and hat on any device.
Device setup and raw input are shared with the game in gamepad.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import cos, pi, sin, sqrt

import pygame

from src.racer.gamepad import (
    LEFT_STICK_AXES,
    RIGHT_STICK_AXES,
    Gamepads,
    GamepadState,
)
from src.racer.gamepad_sensors import (
    ACCELEROMETER,
    GYROSCOPE,
    SensorSmoother,
)

BACKGROUND = (22, 25, 32)
BODY = (64, 71, 86)
IDLE = (36, 41, 52)
ACTIVE = (70, 220, 150)
TEXT = (235, 239, 245)
MUTED = (155, 166, 185)
GRID = (91, 101, 118)
GYRO_COLOR = (245, 180, 75)
DEADZONE = 0.15
WIDTH = 1000


def draw_text(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    position: tuple[int, int],
    color: tuple[int, int, int] = TEXT,
) -> None:
    """Draw a single line of text."""

    screen.blit(font.render(text, True, color), position)


def _sensor_readout_y(state: GamepadState) -> int:
    button_y = max(425, 130 + len(state.axes) * 30)
    button_rows = (len(state.buttons) + 19) // 20
    controls_end = button_y + 40 + button_rows * 32 + len(state.hats) * 26
    axes_end = 116 + len(state.axes) * 30
    return max(controls_end, axes_end) + 20


def _format_sensor(values: tuple[float, float, float] | None) -> str:
    if values is None:
        return "Unavailable"
    return f"X {values[0]:+.2f}  Y {values[1]:+.2f}  Z {values[2]:+.2f}"


@dataclass(frozen=True)
class SensorPanel:
    title: str
    values: tuple[float, float, float] | None
    color: tuple[int, int, int]
    full_scale: float


def _project_sphere_point(
    point: tuple[float, float, float],
    center: tuple[int, int],
    radius: int,
) -> tuple[int, int]:
    x_value, y_value, z_value = point
    return (
        round(center[0] + radius * (0.866 * x_value + 0.5 * y_value)),
        round(
            center[1]
            - radius * (0.25 * x_value - 0.433 * y_value - 0.866 * z_value)
        ),
    )


def _draw_sensor_sphere(
    screen: pygame.Surface,
    font: pygame.font.Font,
    center_x: int,
    top: int,
    panel: SensorPanel,
) -> None:
    center = (center_x, top + 155)
    radius = 80
    title = font.render(panel.title, True, TEXT)
    screen.blit(title, title.get_rect(center=(center_x, top + 12)))
    readout = font.render(_format_sensor(panel.values), True, MUTED)
    screen.blit(readout, readout.get_rect(center=(center_x, top + 40)))

    pygame.draw.circle(screen, IDLE, center, radius)
    for latitude in (-60, -30, 0, 30, 60):
        angle_y = latitude * pi / 180
        points = [
            _project_sphere_point(
                (
                    cos(angle_y) * cos(index * 2 * pi / 48),
                    cos(angle_y) * sin(index * 2 * pi / 48),
                    sin(angle_y),
                ),
                center,
                radius,
            )
            for index in range(49)
        ]
        pygame.draw.aalines(screen, GRID, True, points)

    for longitude in range(8):
        angle_x = longitude * pi / 8
        points = [
            _project_sphere_point(
                (
                    cos(index * pi / 32) * cos(angle_x),
                    cos(index * pi / 32) * sin(angle_x),
                    sin(index * pi / 32),
                ),
                center,
                radius,
            )
            for index in range(33)
        ]
        pygame.draw.aalines(screen, GRID, False, points)
    pygame.draw.circle(screen, BODY, center, radius, 1)

    if panel.values is None:
        return
    magnitude = sqrt(sum(value * value for value in panel.values))
    if magnitude == 0:
        return
    vector_scale = min(magnitude / panel.full_scale, 1.0) / magnitude
    vector = (
        panel.values[0] * vector_scale,
        panel.values[1] * vector_scale,
        panel.values[2] * vector_scale,
    )
    endpoint = _project_sphere_point(vector, center, radius)
    pygame.draw.line(screen, panel.color, center, endpoint, 3)
    pygame.draw.circle(screen, panel.color, endpoint, 7)


def draw_sensor_spheres(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: GamepadState,
    top: int,
) -> None:
    """Draw 3D direction and magnitude gauges for both IMU sensors."""

    _draw_sensor_sphere(
        screen,
        font,
        250,
        top,
        SensorPanel(
            "Accelerometer - 1 g full scale",
            state.accelerometer,
            ACTIVE,
            9.80665,
        ),
    )
    _draw_sensor_sphere(
        screen,
        font,
        750,
        top,
        SensorPanel(
            "Gyroscope - 6 rad/s full scale",
            state.gyroscope,
            GYRO_COLOR,
            6.0,
        ),
    )


def draw_stick(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: GamepadState,
    axis: int,
    center: tuple[int, int],
) -> None:
    """Draw a stick's displacement and click state."""

    button = (7, 8)[axis // 2]
    x_value, y_value = state.axis(axis), state.axis(axis + 1)
    active = max(abs(x_value), abs(y_value)) > DEADZONE or state.pressed(button)
    pygame.draw.circle(screen, IDLE, center, 43)
    pygame.draw.circle(
        screen,
        ACTIVE if active else MUTED,
        (center[0] + round(x_value * 22), center[1] + round(y_value * 22)),
        20,
    )
    draw_text(
        screen,
        font,
        f"A{axis}/{axis + 1} B{button}",
        (center[0] - 50, center[1] + 47),
    )


def draw_silhouette(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: GamepadState,
    resting_axes: list[float],
) -> None:
    """Draw a common raw joystick layout on a controller silhouette."""

    pygame.draw.polygon(
        screen,
        BODY,
        [
            (100, 145),
            (215, 110),
            (425, 110),
            (540, 145),
            (605, 340),
            (580, 390),
            (520, 390),
            (425, 310),
            (215, 310),
            (120, 390),
            (60, 390),
            (35, 340),
        ],
    )
    for index, position in (
        (0, (495, 252)),
        (1, (530, 217)),
        (2, (460, 217)),
        (3, (495, 182)),
        (9, (150, 125)),
        (10, (490, 125)),
        (4, (200, 145)),
        (6, (440, 145)),
        (15, (320, 165)),
        (5, (320, 280)),
    ):
        if index == 15:
            pygame.draw.rect(
                screen,
                ACTIVE if state.pressed(index) else IDLE,
                (position[0] - 90, position[1] - 45, 180, 90),
            )
        else:
            pygame.draw.circle(
                screen, ACTIVE if state.pressed(index) else IDLE, position, 19
            )
        label = font.render(f"B{index}", True, TEXT)
        screen.blit(label, label.get_rect(center=position))

    draw_stick(screen, font, state, LEFT_STICK_AXES[0], (235, 280))
    draw_stick(screen, font, state, RIGHT_STICK_AXES[0], (405, 280))

    hat_x, hat_y = state.hats[0] if state.hats else (0, 0)
    for dx, dy, button in ((0, 1, 11), (-1, 0, 13), (0, -1, 12), (1, 0, 14)):
        active = (
            (dx != 0 and dx == hat_x)
            or (dy != 0 and dy == hat_y)
            or state.pressed(button)
        )
        pygame.draw.rect(
            screen,
            ACTIVE if active else IDLE,
            (133 + dx * 23, 218 - dy * 23, 22, 22),
            border_radius=4,
        )
    draw_text(screen, font, "H0 / B11-14", (95, 275))

    for axis, x_position in ((4, 115), (5, 455)):
        active = (
            axis < len(state.axes)
            and abs(state.axes[axis] - resting_axes[axis]) > DEADZONE
        )
        pygame.draw.rect(
            screen,
            ACTIVE if active else IDLE,
            (x_position, 82, 70, 22),
            border_radius=8,
        )
        draw_text(screen, font, f"A{axis}", (x_position + 20, 84))


def draw_raw_controls(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: GamepadState,
    resting_axes: list[float],
) -> None:
    """Show every input, including controls outside the silhouette."""

    draw_text(screen, font, "Raw controls", (660, 82))
    for index, value in enumerate(state.axes):
        y_position = 116 + index * 30
        reference = resting_axes[index] if index >= 4 else 0.0
        active = abs(value - reference) > DEADZONE
        draw_text(
            screen,
            font,
            f"A{index}: {value:+.3f}",
            (660, y_position),
            ACTIVE if active else TEXT,
        )
        pygame.draw.rect(screen, BODY, (815, y_position + 5, 160, 12))
        pygame.draw.line(
            screen, MUTED, (895, y_position + 2), (895, y_position + 19)
        )
        pygame.draw.circle(
            screen,
            ACTIVE if active else MUTED,
            (895 + round(value * 77), y_position + 11),
            5,
        )

    button_y = max(425, 130 + len(state.axes) * 30)
    draw_text(screen, font, "Buttons", (24, button_y))
    for index, pressed in enumerate(state.buttons):
        x_position = 24 + index % 20 * 48
        y_position = button_y + 30 + index // 20 * 32
        pygame.draw.rect(
            screen,
            ACTIVE if pressed else IDLE,
            (x_position, y_position, 42, 26),
            border_radius=5,
        )
        draw_text(
            screen,
            font,
            str(index),
            (x_position + 7, y_position + 3),
            BACKGROUND if pressed else TEXT,
        )

    hat_y_position = button_y + 40 + ((len(state.buttons) + 19) // 20) * 32
    for index, hat in enumerate(state.hats):
        draw_text(
            screen,
            font,
            f"H{index}: {hat}",
            (24, hat_y_position + index * 26),
            ACTIVE if hat != (0, 0) else TEXT,
        )


def draw_gamepad(
    screen: pygame.Surface,
    font: pygame.font.Font,
    state: GamepadState,
    resting_axes: list[float],
) -> None:
    """Draw the silhouette and complete raw control readouts."""

    screen.fill(BACKGROUND)
    draw_text(screen, font, state.name, (24, 18))
    draw_text(screen, font, "Tab: next gamepad    Esc: quit", (24, 46), MUTED)
    draw_silhouette(screen, font, state, resting_axes)
    draw_raw_controls(screen, font, state, resting_axes)
    draw_sensor_spheres(screen, font, state, _sensor_readout_y(state))
    draw_text(
        screen,
        font,
        "Raw layout varies by device; A = axis, B = button, H = hat.",
        (24, screen.get_height() - 30),
        MUTED,
    )


def handle_event(
    event: pygame.event.Event,
    gamepads: Gamepads,
    selected: int | None,
) -> tuple[int | None, bool]:
    """Handle connection changes, selection, and window exit requests."""

    if event.type == pygame.QUIT:
        return selected, False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return selected, False
        if event.key == pygame.K_TAB and gamepads.devices:
            ids = list(gamepads.devices)
            selected = (
                ids[(ids.index(selected) + 1) % len(ids)]
                if selected is not None and selected in ids
                else ids[0]
            )
    gamepads.handle_event(event)
    return selected, True


def run_gamepad_visualizer(max_frames: int | None = None) -> None:
    """Run the visualizer, optionally limiting frames for automated tests."""

    pygame.init()
    gamepads = Gamepads()
    sensor_smoother = SensorSmoother()
    selected: int | None = None
    try:
        screen = pygame.display.set_mode((WIDTH, 620))
        pygame.display.set_caption("Gamepad Visualizer")
        font = pygame.font.Font(None, 24)
        clock = pygame.time.Clock()
        gamepads.open_connected()
        frame_count = 0
        running = True
        while running and (max_frames is None or frame_count < max_frames):
            for event in pygame.event.get():
                selected, running = handle_event(event, gamepads, selected)
                if not running:
                    break
            if not running:
                break
            if selected not in gamepads.devices:
                selected = next(iter(gamepads.devices), None)
            if selected is None:
                screen.fill(BACKGROUND)
                draw_silhouette(screen, font, GamepadState("", [], [], []), [])
                draw_text(screen, font, "Connect a gamepad to begin.", (24, 24))
                draw_text(screen, font, "Esc: quit", (24, 56), MUTED)
            else:
                state = gamepads.read_state(selected)
                state = replace(
                    state,
                    accelerometer=sensor_smoother.update(
                        selected, ACCELEROMETER, state.accelerometer
                    ),
                    gyroscope=sensor_smoother.update(
                        selected, GYROSCOPE, state.gyroscope
                    ),
                )
                height = max(620, _sensor_readout_y(state) + 300)
                if screen.get_height() != height:
                    screen = pygame.display.set_mode((WIDTH, height))
                draw_gamepad(
                    screen, font, state, gamepads.resting_axes[selected]
                )
            pygame.display.flip()
            clock.tick(60)
            frame_count += 1
    finally:
        gamepads.close()
        pygame.quit()


if __name__ == "__main__":
    run_gamepad_visualizer()
