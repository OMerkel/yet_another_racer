# Software Requirements Specification

## 1. Purpose and scope

This document records the requirements evidenced by the project README,
software architecture, current implementation, existing tests, and configured
runtime. It describes the behavior of Yet Another Racer as it exists today; it is
not a roadmap or a claim that untested behavior has automated coverage.

The scope includes the playable arcade racer and the optional raw-gamepad
visualizer. Network services, saved progress, and persistent user data are not
part of the documented product scope.

## 2. System context and modules

The application is a single-process Pygame game. The racer is composed of
these modules and responsibilities:

| Module | Responsibility |
| --- | --- |
| [`src/racer.py`](../src/racer.py) | Initializes Pygame and coordinates car selection, the frame loop, input, simulation, rendering, and shutdown. |
| [`src/racer/input.py`](../src/racer/input.py) | Defines `DriveInput` and `InputAction`; translates keyboard/gamepad controls and handles gameplay joystick lifecycle. |
| [`src/racer/gamepad.py`](../src/racer/gamepad.py) | Defines shared joystick axis constants and raw controller snapshots/device management used by the diagnostic. |
| [`src/racer/game_state.py`](../src/racer/game_state.py) | Defines immutable race data and car types; creates races and computes pure state transitions. |
| [`src/racer/rendering.py`](../src/racer/rendering.py) | Draws the car-selection screen, road, scenery, traffic, HUD, and game-over display from supplied state. |
| [`script/gamepad_test.py`](../script/gamepad_test.py) | Optional standalone controller diagnostic showing a controller silhouette and live raw axes, buttons, and hats. |
| [`tests/test_gameplay.py`](../tests/test_gameplay.py) | `unittest` cases for input mapping, simulation transitions, and rendering behavior. |

The main runtime flow is `racer.py` -> `input.py` -> `game_state.py` ->
`rendering.py`. `game_state.py` consumes the `DriveInput` contract from
`input.py`; `rendering.py` reads state and car data but does not advance the
simulation. The standalone visualizer uses `gamepad.py` to inspect raw device
input.

## 3. Conventions and verification

* **FR** identifies a functional requirement; **NFR** identifies a
  non-functional requirement.
* Each requirement has one or more verification case IDs. **TST** cases are
  automated Python tests in `tests/test_gameplay.py`; **AT** cases are manual
  acceptance checks described in Section 6.
* The requirement's Gherkin scenario is its acceptance statement. Keywords
  (`FEATURE`, `SCENARIO`, `GIVEN`, `WHEN`, `THEN`, `AND`) are uppercase.
* A requirement is considered covered by a TST only to the extent of the
  assertions in that test. AT coverage is manual and is not represented as an
  automated test.

## 4. Functional requirements

### FR-001 — Keyboard driving controls

**Verification:** TST-001.

```gherkin
FEATURE: Keyboard driving input
SCENARIO: Translate held keyboard keys into normalized driving controls
GIVEN the player holds an acceleration, braking, or steering key
WHEN the keyboard state is sampled
THEN acceleration and braking are 0.0 or 1.0
AND steering is -1.0, 0.0, or 1.0
AND arrow keys and WASD provide equivalent directions
```

### FR-002 — Gamepad driving controls

**Verification:** TST-002.

```gherkin
FEATURE: Gamepad driving input
SCENARIO: Map gameplay joystick axes to driving controls
GIVEN a gamepad exposes left-stick X and trigger axes
WHEN the controls are sampled
THEN left-stick X steers and values within the 0.18 deadzone produce no steering
AND axis 4 maps linearly from -1..1 to braking 0..1
AND axis 5 maps linearly from -1..1 to acceleration 0..1
AND a missing trigger axis produces zero input
```

### FR-003 — Combining control sources

**Verification:** TST-014 and AT-001.

```gherkin
FEATURE: Combined driving input
SCENARIO: Combine simultaneously active keyboard and gamepad controls
GIVEN keyboard and gamepad controls are both available
WHEN the gameplay input handler reads the controls
THEN the greater acceleration and braking values are used
AND steering values are summed and clamped to the range -1..1
```

### FR-004 — Car selection and race actions

**Verification:** TST-003, TST-004, and AT-001.

```gherkin
FEATURE: Car selection and race actions
SCENARIO: Select a car, start a race, and return to selection after a race
GIVEN the game is showing the car-selection screen
WHEN the player navigates with Left/Right, A/D, or a left-stick deflection
THEN the preview changes by one car and wraps at either end of the list
AND one stick deflection changes the preview only once until the stick returns
  to the deadzone
WHEN the player presses Enter, Space, or a supported gamepad start button
THEN a fresh race begins with the selected car
WHEN the race is over and the player presses R or a supported gamepad button
THEN car selection resumes and the selected car is retained
```

### FR-005 — Race simulation and car handling

**Verification:** TST-005, TST-006, TST-007, TST-008, TST-009, and AT-002.

```gherkin
FEATURE: Race simulation
SCENARIO: Advance race state in response to driving controls
GIVEN an active race, a selected car, and a frame duration
WHEN the simulation applies acceleration, braking, and steering
THEN speed remains between 0 and 300
AND acceleration and braking are scaled by the selected car's factors
AND steering has no effect at rest and increases with speed
AND lateral position remains within -1.12..1.12
AND the race distance advances using vehicle speed and the world-speed factor
```

The Formula car uses acceleration/braking factors `1.0`/`1.0`; the Classic car
uses `0.7`/`0.8`. Driving off-road reduces speed.

### FR-006 — Traffic, collisions, and score

**Verification:** AT-002.

```gherkin
FEATURE: Traffic and scoring
SCENARIO: Encounter traffic, leave the road, and pass opponent cars
GIVEN an active race with deterministic traffic
WHEN the player overlaps a traffic car on the track
THEN the player's speed is reduced and a crash timer is started
WHEN the player passes traffic
THEN the score increases by 250 points per car
AND traffic behind the player is removed
AND additional traffic is generated as the remaining traffic runs out
WHEN the player drives outside the road boundary
THEN the player's speed is reduced
```

### FR-007 — Race timer and game-over state

**Verification:** TST-010 and AT-001.

```gherkin
FEATURE: Race duration and completion
SCENARIO: End a race when its 90-second timer expires
GIVEN a race with time remaining
WHEN real frame time reduces the timer to zero
THEN the timer is clamped at zero
AND the state is marked game over
AND subsequent simulation steps leave the completed state unchanged
```

### FR-008 — Race and selection rendering

**Verification:** TST-011, TST-012, TST-013, and AT-001.

```gherkin
FEATURE: Game presentation
SCENARIO: Render the selected car, road, traffic, scenery, and race status
GIVEN a selection or race state and its selected car
WHEN the application draws a frame
THEN the selection screen previews the selected car
AND the race frame presents perspective road, traffic, scenery, and HUD
AND traffic uses the selected car shape
AND mountains cover the sun where their shapes overlap
AND background parallax moves opposite the road bend, with near scenery
  moving more than distant scenery
AND a completed race displays a game-over overlay
```

### FR-009 — Raw gamepad diagnostic

**Verification:** AT-003.

```gherkin
FEATURE: Raw gamepad diagnostic
SCENARIO: Inspect live raw controls for connected gamepads
GIVEN the standalone diagnostic is running
WHEN a controller is connected and its controls are changed
THEN the diagnostic displays live axis, button, and hat values
AND the controller silhouette highlights active controls
WHEN multiple controllers are connected
THEN Tab switches the displayed controller
AND Escape or a window-close event exits the diagnostic
```

### FR-010 — Device lifecycle and application exit

**Verification:** AT-004.

```gherkin
FEATURE: Input-device lifecycle
SCENARIO: Handle controller connection changes and close the game cleanly
GIVEN the game or diagnostic is running
WHEN a controller is attached or removed
THEN connected devices can be opened and removed devices are released
AND the gameplay handler attempts to reconnect an available controller
WHEN Escape or a window-close event is received by the game
THEN the game loop ends and Pygame input/display resources are released
```

## 5. Non-functional requirements

### NFR-001 — Runtime compatibility and reproducible setup

**Verification:** AT-005.

```gherkin
FEATURE: Runtime compatibility
SCENARIO: Set up and launch the application using declared dependencies
GIVEN a supported Python 3.10-or-newer environment and uv
WHEN project dependencies are synchronized from pyproject.toml
THEN pygame-ce in the declared range >=2.5.3 and <3 is installed
AND the game can be launched with `uv run python src/racer.py`
```

### NFR-002 — Immutable, deterministic simulation

**Verification:** TST-005, TST-006, TST-007, TST-008, TST-009, and TST-010.

```gherkin
FEATURE: Simulation determinism
SCENARIO: Calculate a race transition without mutating its input
GIVEN the same immutable race state, controls, delta time, and car type
WHEN a simulation step is evaluated
THEN a new state represents the transition
AND the original state remains unchanged
AND deterministic traffic setup and generation produce repeatable results
```

### NFR-003 — Bounded frame-time input

**Verification:** AT-006.

```gherkin
FEATURE: Frame-time stability
SCENARIO: Prevent a long frame from advancing the simulation excessively
GIVEN the game loop has measured a frame duration
WHEN it advances the race
THEN the duration passed to the simulation is capped at 0.05 seconds
AND the loop targets the configured rendering frame rate
```

### NFR-004 — Separation of responsibilities

**Verification:** AT-006 and the architecture overview in
[`software_architecture.md`](./software_architecture.md).

```gherkin
FEATURE: Module boundaries
SCENARIO: Keep simulation, input, rendering, and orchestration responsibilities
  separate
GIVEN a race frame is processed
WHEN the application reads controls, advances state, and draws
THEN racer.py coordinates the operations
AND input.py adapts device state to the driving contract
AND game_state.py computes state transitions without drawing
AND rendering.py draws supplied state without advancing it
```

### NFR-005 — Resource cleanup

**Verification:** AT-004.

```gherkin
FEATURE: Resource lifecycle
SCENARIO: Release Pygame and joystick resources on normal exit
GIVEN the game or diagnostic has initialized Pygame and input devices
WHEN its run loop exits
THEN open joystick resources are closed
AND the Pygame subsystems are shut down
```

### NFR-006 — Maintainable and verifiable changes

**Verification:** AT-005 and AT-006.

```gherkin
FEATURE: Project quality checks
SCENARIO: Validate behavior and formatting with repository tooling
GIVEN a project change is ready for validation
WHEN the documented checks are run
THEN unittest discovery can run from the project root
AND Ruff lint and format checks can be run when Ruff is available
AND each Python test identifies its requirement and Gherkin scenario
```

## 6. Verification case catalog

### 6.1 Automated Python tests

All automated cases are in [`tests/test_gameplay.py`](../tests/test_gameplay.py).
The requirement IDs and Gherkin feature/scenario are repeated in each test
function's docstring so the trace is navigable from either direction.

| Case | Python test | Requirement(s) |
| --- | --- | --- |
| TST-001 | `InputContractTests.test_keyboard_controls_map_to_drive_contract` | FR-001, FR-003 |
| TST-002 | `InputContractTests.test_gamepad_axes_respect_deadzone_and_drive_directions` | FR-002, FR-003 |
| TST-003 | `InputContractTests.test_car_selection_actions_are_only_active_before_race` | FR-004 |
| TST-004 | `InputContractTests.test_gamepad_stick_changes_car_once_per_deflection` | FR-004 |
| TST-005 | `GameStateTests.test_step_returns_new_state_and_preserves_previous_state` | NFR-002 |
| TST-006 | `GameStateTests.test_top_speed_advances_world_twice_as_fast_but_timer_stays_real_time` | FR-005, NFR-002 |
| TST-007 | `GameStateTests.test_acceleration_is_linear_and_scaled_by_car_model` | FR-005, NFR-002 |
| TST-008 | `GameStateTests.test_brake_strength_scales_deceleration` | FR-005, NFR-002 |
| TST-009 | `GameStateTests.test_steering_strength_scales_with_speed` | FR-005, NFR-002 |
| TST-010 | `GameStateTests.test_timer_ends_race` | FR-007, NFR-002 |
| TST-011 | `RenderingTests.test_mountains_are_drawn_in_front_of_the_sun` | FR-008 |
| TST-012 | `RenderingTests.test_traffic_uses_selected_car_shape` | FR-008 |
| TST-013 | `RenderingTests.test_background_parallax_opposes_road_bend_by_depth` | FR-008 |
| TST-014 | `InputContractTests.test_keyboard_and_gamepad_controls_are_combined` | FR-003 |

### 6.2 Manual acceptance checks

| Case | Procedure and expected result | Requirement(s) |
| --- | --- | --- |
| AT-001 | Launch the game. Navigate both directions through the car list with keyboard and gamepad; confirm wraparound and retained selection. Confirm one menu step per joystick deflection. Start a race and confirm the race scene/HUD; complete it and confirm the game-over overlay and that R/gamepad returns to selection. Check Escape and window-close exit. | FR-003, FR-004, FR-007, FR-008 |
| AT-002 | Drive off-road, collide with traffic, and pass traffic during a race. Confirm speed penalties, crash indication, traffic replenishment, and 250 points per passed car. | FR-005, FR-006 |
| AT-003 | Run `uv run python -m script.gamepad_test`. Connect controllers and exercise axes, buttons, and hats. Confirm live readouts/highlights, dynamic display for device control counts, Tab device cycling, and Escape/window-close exit. | FR-009 |
| AT-004 | While the racer and diagnostic are running, connect/disconnect a controller and exit each application normally. Confirm the racer attempts reconnection and no joystick remains owned after exit. | FR-010, NFR-005 |
| AT-005 | On Python 3.10 or newer, run `uv sync`, then launch with `uv run python src/racer.py`. Confirm setup succeeds with the declared pygame-ce constraint. | NFR-001, NFR-006 |
| AT-006 | Inspect the loop and module boundaries against the architecture overview; confirm frame delta is capped at 0.05 seconds, simulation does not draw, and rendering does not mutate/advance state. Confirm each Python test header carries a requirement ID and Gherkin feature/scenario. Run the documented unit and Ruff checks when the tools are installed. | NFR-003, NFR-004, NFR-006 |

## 7. Requirement traceability index

| Requirement | Verification cases |
| --- | --- |
| FR-001 | TST-001 |
| FR-002 | TST-002 |
| FR-003 | TST-014, AT-001 |
| FR-004 | TST-003, TST-004, AT-001 |
| FR-005 | TST-006–TST-009, AT-002 |
| FR-006 | AT-002 |
| FR-007 | TST-010, AT-001 |
| FR-008 | TST-011–TST-013, AT-001 |
| FR-009 | AT-003 |
| FR-010 | AT-004 |
| NFR-001 | AT-005 |
| NFR-002 | TST-005–TST-010 |
| NFR-003 | AT-006 |
| NFR-004 | AT-006 |
| NFR-005 | AT-004 |
| NFR-006 | AT-005, AT-006 |

## 8. Project verification commands

From the repository root:

```powershell
uv sync
uv run python -m unittest discover -s tests
uv run ruff check .
uv run ruff format --check .
```

Ruff is not declared as a project dependency; the Ruff checks require it to be
available in the environment. Launch the game with `uv run python src/racer.py`
and the optional visualizer with `uv run python -m script.gamepad_test`.
