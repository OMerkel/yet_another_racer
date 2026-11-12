"""Application entry point and game-loop orchestration."""

import sys

import pygame

from racer.game_state import (
    CAR_TYPES,
    DEFAULT_LAP_COUNT,
    LAP_OPTIONS,
    new_game,
    step_game,
)
from racer.input import InputAction, InputHandler
from racer.rendering import (
    FPS,
    SCREEN_SIZE,
    create_fonts,
    draw_car_selection,
    draw_frame,
)
from racer.track import TRACKS


def run_game() -> int:
    """Initialize Pygame and orchestrate input, state, and rendering."""
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Yet Another Racer")
    clock = pygame.time.Clock()
    fonts = create_fonts()
    input_handler = InputHandler()
    selected_car = 0
    selected_track = 0
    selected_laps = LAP_OPTIONS.index(DEFAULT_LAP_COUNT)
    selected_option = 0
    state = new_game(
        track=TRACKS[selected_track], lap_count=LAP_OPTIONS[selected_laps]
    )
    selecting_car = True
    running = True

    try:
        while running:
            delta_time = min(clock.tick(FPS) / 1000, 0.05)
            for event in pygame.event.get():
                action = input_handler.process_event(
                    event, state.game_over, selecting_car
                )
                if action is InputAction.QUIT:
                    running = False
                elif action is InputAction.PREVIOUS_OPTION:
                    selected_option = (selected_option - 1) % 3
                elif action is InputAction.NEXT_OPTION:
                    selected_option = (selected_option + 1) % 3
                elif action in (
                    InputAction.PREVIOUS_VALUE,
                    InputAction.NEXT_VALUE,
                ):
                    direction = (
                        -1 if action is InputAction.PREVIOUS_VALUE else 1
                    )
                    if selected_option == 0:
                        selected_car = (selected_car + direction) % len(
                            CAR_TYPES
                        )
                    elif selected_option == 1:
                        selected_track = (selected_track + direction) % len(
                            TRACKS
                        )
                    else:
                        selected_laps = (selected_laps + direction) % len(
                            LAP_OPTIONS
                        )
                elif action is InputAction.START:
                    state = new_game(
                        track=TRACKS[selected_track],
                        lap_count=LAP_OPTIONS[selected_laps],
                    )
                    selecting_car = False
                elif action is InputAction.RESTART:
                    selecting_car = True

            if running:
                if selecting_car:
                    draw_car_selection(
                        screen,
                        fonts,
                        CAR_TYPES[selected_car],
                        track=TRACKS[selected_track],
                        track_index=selected_track,
                        lap_count=LAP_OPTIONS[selected_laps],
                        active_option=selected_option,
                    )
                else:
                    controls = input_handler.read_controls()
                    state = step_game(
                        state,
                        controls,
                        delta_time,
                        car_type=CAR_TYPES[selected_car],
                    )
                    draw_frame(
                        screen,
                        state,
                        fonts,
                        car_type=CAR_TYPES[selected_car],
                    )
                pygame.display.flip()
    finally:
        input_handler.close()
        pygame.quit()

    return 0


def main() -> int:
    """Launch the game application."""
    return run_game()


if __name__ == "__main__":
    sys.exit(main())
