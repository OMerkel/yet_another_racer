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
| [`src/racer/track.py`](../src/racer/track.py) | Defines deterministic, closed Hockenheim and Nürburgring GP centerlines as named segments with curvature and elevation data. |
| [`src/racer/rendering.py`](../src/racer/rendering.py) | Composes scene rendering, HUD, car selection, and game-over display; provides the renderer facade. |
| [`src/racer/rendering_geometry.py`](../src/racer/rendering_geometry.py) | Projects camera and track geometry, road strips, and the start line into the scene. |
| [`src/racer/rendering_cars.py`](../src/racer/rendering_cars.py) | Draws the selectable Formula and Classic car silhouettes. |
| [`script/gamepad_visualizer.py`](../script/gamepad_visualizer.py) | Optional standalone controller visualizer showing a controller silhouette, live raw axes/buttons/hats, and available accelerometer and gyroscope values. |
| [`tests/test_input.py`](../tests/test_input.py) | `unittest` cases for keyboard, gamepad, and options input. |
| [`tests/test_track_geometry.py`](../tests/test_track_geometry.py) | `unittest` cases for circuit geometry, sectors, and lap boundaries. |
| [`tests/test_game_state.py`](../tests/test_game_state.py) | `unittest` cases for race transitions, lap completion, and vehicle physics. |
| [`tests/test_gamepad_sensors.py`](../tests/test_gamepad_sensors.py) | `unittest` cases for controller motion-sensor access and smoothing. |
| [`tests/test_rendering.py`](../tests/test_rendering.py) | `unittest` cases for road projection, track maps, and rendering. |

The main runtime flow is `racer.py` -> `input.py` -> `game_state.py` ->
`rendering.py`; the renderer delegates camera and road work to
`rendering_geometry.py` and vehicle silhouettes to `rendering_cars.py`.
`rendering_geometry.py` samples geometry from `track.py`.
`game_state.py` consumes the `DriveInput` contract from `input.py`; rendering
reads state and track data but does not advance the simulation. The standalone
visualizer uses `gamepad.py` to inspect raw device input.

## 3. Conventions and verification

* **FR** identifies a functional requirement; **NFR** identifies a
  non-functional requirement.
* Each requirement has one or more verification case IDs. **TST** cases are
  automated Python tests in `tests/`; **AT** cases are manual
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

**Verification:** TST-002 and TST-037.

```gherkin
FEATURE: Gamepad driving input
SCENARIO: Map gamepad stick, D-pad and trigger controls to driving
GIVEN a gamepad exposes left-stick X, an optional D-pad and trigger axes
WHEN the controls are sampled
THEN left-stick X steers and values within the 0.18 deadzone produce no steering
AND D-pad horizontal steers digitally when available
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

**Verification:** TST-003, TST-004, TST-024, TST-025, and AT-001.

```gherkin
FEATURE: Car selection and race actions
SCENARIO: Select race options, start, and return to options after a race
GIVEN the pre-race options screen is showing
WHEN the player navigates Up/Down, D-pad vertical, or left-stick Y
THEN the highlight wraps among car, track, and lap-count options
WHEN the player navigates Left/Right, D-pad horizontal, or left-stick X
THEN the highlighted value changes and wraps where applicable
AND one stick deflection changes an option only once until it returns to neutral
AND the track option displays its bird's-eye preview
WHEN the player presses Enter, Space, or a supported gamepad start button
THEN a fresh race begins with the selected car, track, and lap count
WHEN the race is over and the player presses R or a supported gamepad button
THEN race options resume and the selected car, track, and lap count are retained
```

### FR-005 — Race simulation and car handling

**Verification:** TST-005 through TST-009, TST-029, TST-030, TST-034,
TST-036, TST-038, and AT-002.

```gherkin
FEATURE: Race simulation
SCENARIO: Advance race state in response to driving controls
GIVEN an active race, a selected car, and a frame duration
WHEN the simulation applies acceleration, braking, and steering
THEN speed remains between 0 and 300
AND acceleration and braking are scaled by the selected car's factors
AND steering has no effect at rest and increases with speed
AND lateral position remains within -1.12..1.12
AND speed in km/h is converted to meters per second by dividing by 3.6
AND forward progress accounts for heading error and the inside/outside bend
AND steering changes vehicle heading relative to the selected track tangent
AND neutral steering on a straight creates no synthetic lateral drift
AND steering can hold a representative tight bend at low speed
```

The Formula car uses acceleration/braking factors `1.0`/`1.0`; the Classic car
uses `0.7`/`0.8`. Grass reduces acceleration and adds speed-dependent drag, but
full throttle can recover a car from rest. Curbs do not apply the grass penalty.

### FR-006 — Traffic, collisions, and score

**Verification:** TST-044, TST-045, and AT-002.

```gherkin
FEATURE: Traffic and scoring
SCENARIO: Encounter traffic, leave the road, and pass opponent cars
GIVEN an active race with deterministic traffic
WHEN the player overlaps a traffic car on the track
THEN the player's speed is reduced and a crash timer is started
AND overlap uses the selected car type's width and length in meters
AND separated cars and footprints that only touch do not trigger contact
AND the crash timer prevents repeated speed penalties for 0.9 seconds
AND the contact indicator reports a recent hit, not necessarily current overlap
WHEN the player passes traffic
THEN the score increases by 250 points per car
AND traffic behind the player is removed
AND additional traffic is generated as the remaining traffic runs out
WHEN the player drives outside the road boundary
THEN the player's speed is reduced
```

### FR-007 — Lap-limited race completion

**Verification:** TST-010, TST-033, TST-040, and AT-001.

```gherkin
FEATURE: Lap-limited race completion
SCENARIO: End a race at the selected lap count
GIVEN a race with a configured lap count and a circuit length
WHEN the player crosses the start/finish line for the final lap
THEN distance is clamped to the exact finish distance
AND the state is marked game over
AND subsequent simulation steps leave the completed state unchanged
```

### FR-008 — Race and selection rendering

**Verification:** TST-011 through TST-013, TST-021, TST-027, TST-031,
TST-032, TST-041–TST-043, TST-046 through TST-049, and AT-001.

```gherkin
FEATURE: Game presentation
SCENARIO: Render the selected car, road, traffic, scenery, and race status
GIVEN a selection or race state and its selected car
WHEN the application draws a frame
THEN the selection screen previews the selected car
AND the race frame presents perspective road, traffic, scenery, and HUD
AND the race frame presents an overview map for the selected circuit
AND fixed world-space road edges are projected using camera-space depth
AND road width, markings, player, traffic, and map use the same meter scale
AND geometry behind the camera is clipped before perspective projection
AND traffic uses the selected car shape
AND player and traffic sprite widths use the selected car type's width
AND mountains cover the sun where their shapes overlap
AND background parallax scrolls opposite camera turns, with the sun moving
  slower than the far mountain range and the near mountain range fastest
AND background layers repeat seamlessly at screen edges and lap boundaries
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
AND displays accelerometer and gyroscope values when supported by the controller
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
AND, with the repository root on `PYTHONPATH`, the game can be launched with
  `uv run python src/racer.py`
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

### FR-011 — Hockenheim circuit geometry and overview map

**Verification:** TST-017–TST-021 and AT-007.

```gherkin
FEATURE: Hockenheim GP circuit
SCENARIO: Render a closed, named circuit in the race view and overview map
GIVEN the modern GP layout is represented by sampled track segments
WHEN the race distance advances around the circuit
THEN the segment array includes start/finish, northern curve, Parabolika,
  hairpin, Motodrom, and southern curve sectors
AND segments store length, curvature, elevation, and grade
AND track samples wrap smoothly at the 4574-meter start/finish boundary
AND the 3D road, curbs, markings, and minimap use the same centerline data
AND the minimap marks the current position, lap, and sector
```

### FR-012 — Nürburgring GP and track selection

**Verification:** TST-022 through TST-027 and AT-008.

```gherkin
FEATURE: Selectable GP circuits
SCENARIO: Select and race the Nürburgring GP circuit
GIVEN the pre-race options screen is active
WHEN the player changes the track selection
THEN Hockenheim and Nürburgring GP wrap as selectable options
AND each option displays its own bird's-eye centerline preview
AND starting the race stores the selected track and its lap length
AND the road projection and race map use the selected circuit geometry
```

### FR-013 — Configurable lap count

**Verification:** TST-010, TST-024–TST-027, TST-033, and AT-009.

```gherkin
FEATURE: Lap-count race options
SCENARIO: Select the number of laps before starting
GIVEN the pre-race options screen is active
WHEN the player focuses lap count and changes its value horizontally
THEN the lap count wraps between 1, 3, and 5 laps
AND keyboard arrows, D-pad, and left stick use the same navigation model
AND the selected lap count is shown in options and in the race HUD
AND the race finishes exactly at track length multiplied by lap count
```

### FR-014 — Stationary grid start and start lights

**Verification:** TST-040 through TST-043 and AT-010.

```gherkin
FEATURE: Race start sequence
SCENARIO: Hold the grid until the five red lights go out
GIVEN a new race with the car stationary before the start/finish line
WHEN the five-light countdown is active
THEN throttle and steering do not move the car
AND the 3D road shows a painted checkered grid line across its width
AND five red lights extinguish in sequence during the countdown
WHEN all lights go out
THEN car movement begins
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

Automated cases are organized by responsibility in the test modules under
[`tests/`](../tests/). Each test docstring records its requirement ID and
Gherkin feature/scenario.

| Case | Python test | Requirement(s) |
| --- | --- | --- |
| TST-001 | `InputContractTests.test_keyboard_controls_map_to_drive_contract` | FR-001, FR-003 |
| TST-002 | `InputContractTests.test_gamepad_axes_respect_deadzone_and_drive_directions` | FR-002, FR-003 |
| TST-003 | `InputContractTests.test_car_selection_actions_are_only_active_before_race` | FR-004 |
| TST-004 | `InputContractTests.test_gamepad_stick_changes_option_value_once_per_deflection` | FR-004 |
| TST-005 | `GameStateTests.test_step_returns_new_state_and_preserves_previous_state` | NFR-002 |
| TST-006 | `GameStateTests.test_top_speed_advances_in_meters_per_second` | FR-005, NFR-002 |
| TST-007 | `GameStateTests.test_acceleration_is_linear_and_scaled_by_car_model` | FR-005, NFR-002 |
| TST-008 | `GameStateTests.test_brake_strength_scales_deceleration` | FR-005, NFR-002 |
| TST-009 | `GameStateTests.test_steering_strength_scales_with_speed` | FR-005, NFR-002 |
| TST-010 | `GameStateTests.test_lap_limit_ends_race_at_the_finish_line` | FR-007, FR-013, NFR-002 |
| TST-011 | `RenderingTests.test_mountains_are_drawn_in_front_of_the_sun` | FR-008 |
| TST-012 | `RenderingTests.test_traffic_uses_selected_car_shape` | FR-008 |
| TST-013 | `RenderingTests.test_background_parallax_opposes_road_bend_by_depth` | FR-008 |
| TST-014 | `InputContractTests.test_keyboard_and_gamepad_controls_are_combined` | FR-003 |
| TST-015 | `GamepadSensorTests.test_sdl_controller_sensors_are_enabled_and_read` | FR-009 |
| TST-016 | `GamepadSensorTests.test_sensor_smoother_reduces_sample_jumps` | FR-009 |
| TST-017 | `TrackGeometryTests.test_track_contains_all_named_sectors_and_matches_lap_length` | FR-011 |
| TST-018 | `TrackGeometryTests.test_track_sampling_is_continuous_across_the_start_finish_line` | FR-011 |
| TST-019 | `TrackGeometryTests.test_track_segments_store_curve_and_grade_data` | FR-011 |
| TST-020 | `RenderingTests.test_track_map_draws_the_circuit_and_current_position` | FR-011 |
| TST-021 | `RenderingTests.test_near_road_segment_is_drawn_over_distant_grass` | FR-008, FR-011 |
| TST-022 | `TrackGeometryTests.test_nurburgring_track_has_named_sectors_and_wraps` | FR-012 |
| TST-023 | `TrackGeometryTests.test_new_game_retains_the_selected_track` | FR-012 |
| TST-024 | `InputContractTests.test_option_navigation_uses_arrows_stick_and_dpad` | FR-004, FR-012, FR-013 |
| TST-025 | `InputContractTests.test_option_stick_selection_requires_a_neutral_return` | FR-004, FR-012, FR-013 |
| TST-026 | `RenderingTests.test_car_selection_draws_the_selected_track_preview` | FR-012, FR-013 |
| TST-027 | `RenderingTests.test_race_map_sector_labels_fit_the_map_panel` | FR-008, FR-012, FR-013 |
| TST-028 | `TrackGeometryTests.test_sample_heading_matches_centerline_and_is_continuous` | FR-011, FR-012 |
| TST-029 | `GameStateTests.test_neutral_controls_do_not_drift_on_a_straight` | FR-005 |
| TST-030 | `GameStateTests.test_cornering_responds_to_the_selected_track` | FR-005 |
| TST-031 | `RenderingTests.test_road_edges_are_fixed_world_geometry` | FR-008, FR-011, FR-012 |
| TST-032 | `RenderingTests.test_road_polygons_are_clipped_before_projection` | FR-008 |
| TST-033 | `GameStateTests.test_default_lap_count_is_an_available_option` | FR-007, FR-013 |
| TST-034 | `GameStateTests.test_curbs_are_drivable_and_grass_has_moderate_drag` | FR-005 |
| TST-036 | `GameStateTests.test_full_throttle_can_recover_from_grass_at_rest` | FR-005 |
| TST-037 | `InputContractTests.test_input_handler_reads_left_stick_and_dpad_steering` | FR-002 |
| TST-038 | `GameStateTests.test_steering_can_hold_a_typical_tight_turn_at_low_speed` | FR-005 |
| TST-040 | `GameStateTests.test_grid_start_holds_controls_until_countdown_finishes` | FR-007, FR-014 |
| TST-041 | `RenderingTests.test_start_line_draws_alternating_grid_tiles` | FR-008, FR-014 |
| TST-042 | `RenderingTests.test_start_lights_extinguish_during_grid_countdown` | FR-008, FR-014 |
| TST-043 | `RenderingTests.test_grid_hud_starts_on_lap_one_before_start_line` | FR-008, FR-014 |
| TST-044 | `GameStateTests.test_collision_uses_selected_car_dimensions_in_meters` | FR-006 |
| TST-045 | `GameStateTests.test_collision_cooldown_prevents_repeated_speed_penalties` | FR-006 |
| TST-046 | `RenderingTests.test_player_and_traffic_render_with_selected_car_width` | FR-008 |
| TST-047 | `RenderingTests.test_background_scrolls_as_the_camera_turns` | FR-008 |
| TST-048 | `RenderingTests.test_background_tiles_cover_edges_and_wrap_without_gaps` | FR-008 |
| TST-049 | `RenderingTests.test_background_is_continuous_at_heading_and_lap_boundaries` | FR-008 |

### 6.2 Manual acceptance checks

| Case | Procedure and expected result | Requirement(s) |
| --- | --- | --- |
| AT-001 | Launch the game. Move the highlight through car, track, and lap options with keyboard and gamepad; change each highlighted value horizontally and confirm wraparound, preview updates, and one menu step per stick deflection. Start a race, complete it, and confirm R/gamepad returns to options. Check Escape and window-close exit. | FR-003, FR-004, FR-007, FR-008, FR-012, FR-013 |
| AT-002 | Drive off-road, collide with traffic, and pass traffic during a race. Confirm speed penalties, crash indication, traffic replenishment, and 250 points per passed car. | FR-005, FR-006 |
| AT-003 | Run `uv run python -m script.gamepad_visualizer`. Connect controllers and exercise axes, buttons, and hats. Confirm live readouts/highlights, dynamic display for device control counts, available accelerometer/gyroscope values, Tab device cycling, and Escape/window-close exit. | FR-009 |
| AT-004 | While the racer and diagnostic are running, connect/disconnect a controller and exit each application normally. Confirm the racer attempts reconnection and no joystick remains owned after exit. | FR-010, NFR-005 |
| AT-005 | On Python 3.10 or newer, run `uv sync`, set `$env:PYTHONPATH = (Get-Location).Path`, then launch with `uv run python src/racer.py`. Confirm setup succeeds with the declared pygame-ce constraint. | NFR-001, NFR-006 |
| AT-006 | Inspect the loop and module boundaries against the architecture overview; confirm frame delta is capped at 0.05 seconds, simulation does not draw, and rendering does not mutate/advance state. Confirm each Python test header carries a requirement ID and Gherkin feature/scenario. Run the documented unit and Ruff checks when the tools are installed. | NFR-003, NFR-004, NFR-006 |
| AT-007 | Drive through one lap. Compare the road's broad sequence and sector order with a modern Hockenheim GP reference map. Confirm the map marker advances around the same route, sector labels change, road markings stay fixed to the circuit, and the start/finish join has no visible jump. | FR-011 |
| AT-008 | Select Nürburgring GP. Compare its preview and race view with a modern GP reference map; drive through the Mercedes Arena, western turns, and eastern final section. Confirm the in-race map marker follows the chosen layout and wraps at its lap length. | FR-012 |
| AT-009 | Choose 1, 3, and 5 laps on both tracks. Confirm the selected count appears in options and HUD, finish occurs at the matching start/finish crossing, and distance does not exceed the target. Compare acceleration, braking, curb and grass response, and steering through corners. | FR-005, FR-007, FR-013 |
| AT-010 | Start either circuit. Confirm the car is stationary just before the checkered start/finish line, the HUD shows lap 1, and five red lights extinguish in order. Apply throttle/steering during the countdown and confirm the car remains on the grid; confirm it moves after the final light goes out. | FR-007, FR-008, FR-014 |

## 7. Requirement traceability index

| Requirement | Verification cases |
| --- | --- |
| FR-001 | TST-001 |
| FR-002 | TST-002, TST-037 |
| FR-003 | TST-014, AT-001 |
| FR-004 | TST-003, TST-004, TST-024, TST-025, AT-001 |
| FR-005 | TST-006–TST-009, TST-029, TST-030, TST-034, TST-036, TST-038, AT-002, AT-009 |
| FR-006 | AT-002 |
| FR-007 | TST-010, TST-033, TST-040, AT-001, AT-009, AT-010 |
| FR-008 | TST-011–TST-013, TST-021, TST-027, TST-031, TST-032, TST-041–TST-043, AT-001, AT-010 |
| FR-009 | TST-015, TST-016, AT-003 |
| FR-010 | AT-004 |
| FR-011 | TST-017–TST-021, TST-028, TST-031, AT-007 |
| FR-012 | TST-022–TST-028, TST-031, AT-001, AT-008 |
| FR-013 | TST-010, TST-024–TST-027, TST-033, AT-001, AT-009 |
| FR-014 | TST-040–TST-043, AT-010 |
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
$env:PYTHONPATH = (Get-Location).Path
uv run python -m unittest discover -s tests
uv run ruff check .
uv run ruff format --check .
```

Ruff is not declared as a project dependency; the Ruff checks require it to be
available in the environment. With the repository root on `PYTHONPATH`, launch
the game with `uv run python src/racer.py` and the optional visualizer with
`uv run python -m script.gamepad_visualizer`.
