"""Application entry point and game-loop orchestration."""

import sys

import pygame

from racer.game_state import CAR_TYPES, new_game, step_game
from racer.input import InputAction, InputHandler
from racer.rendering import (
    FPS,
    SCREEN_SIZE,
    create_fonts,
    draw_car_selection,
    draw_frame,
)


def run_game() -> int:
    """Initialize Pygame and orchestrate input, state, and rendering."""
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Yet Another Racer")
    clock = pygame.time.Clock()
    fonts = create_fonts()
    input_handler = InputHandler()
    state = new_game()
    selected_car = 0
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
                elif action is InputAction.PREVIOUS_CAR:
                    selected_car = (selected_car - 1) % len(CAR_TYPES)
                elif action is InputAction.NEXT_CAR:
                    selected_car = (selected_car + 1) % len(CAR_TYPES)
                elif action is InputAction.START:
                    state = new_game()
                    selecting_car = False
                elif action is InputAction.RESTART:
                    selecting_car = True

            if running:
                if selecting_car:
                    draw_car_selection(screen, fonts, CAR_TYPES[selected_car])
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
