# Yet Another Racer

A small retro arcade racer built with Pygame. Steer a car along a curving road,
avoid traffic, and pass cars to build your score before the selected lap count
is complete. Choose between closed, stylized Hockenheim and Nurburgring GP
circuits, each with a live overview map.

## Gameplay

### Race Start

![The car on the grid with three start lights illuminated](doc/gameplay-start-lights.png)

### On Track

![Racing through Hockenheim's Parabolika](doc/gameplay-hockenheim-parabolika.png)

### Final Approach

![1.3 meters before the Nürburgring GP finish line and 1.5 meters left of center](doc/gameplay-nurburgring-finish.png)

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.10 or newer

## Bring Up

From the project directory, sync the dependencies and launch the game:

```powershell
uv sync
$env:PYTHONPATH = (Get-Location).Path
uv run python src/racer.py
```

`uv sync` creates or updates `.venv` and installs the Pygame-compatible
`pygame-ce` dependency declared in `pyproject.toml`. The repository root must
be on `PYTHONPATH` because the entry point imports modules through both `racer`
and `src.racer`.

## Controls

Before a race, use Up/Down to highlight car, track, or lap count; Left/Right
changes the highlighted value. The options screen shows the track's bird's-eye
preview. Press Enter or Space to start.

The car waits stationary on the grid before the start/finish line while five
red lights count down. Driving starts when they go out.

| Input | Action |
| --- | --- |
| Up/Down, D-pad vertical, or left stick Y before race | Select option |
| Left/Right, D-pad horizontal, or left stick X before race | Change selected value |
| Enter or Space before race | Start race |
| Up arrow or W; right shoulder trigger | Accelerate |
| Down arrow or S; left shoulder trigger | Brake |
| Left arrow or A; left stick or D-pad left | Steer left |
| Right arrow or D; left stick or D-pad right | Steer right |
| R | Return to options after race completion |
| Esc | Quit |

The left stick's horizontal axis 0 or the D-pad steers. The right shoulder trigger uses
axis 5 for linear acceleration: -1 is zero, 0 is half, and +1 is full throttle.
The left shoulder trigger uses axis 4 for linear braking: -1 is no brake, 0 is
half, and +1 is hard braking.
The Simple car has 70% of F1 acceleration and 80% of F1 braking strength.
Each car has a centered steering-response deadzone: Formula uses -0.12 to
+0.12 and Classic uses -0.18 to +0.18, including the boundaries. Small stick
values remain available as nonzero input, but the car applies neutral steering
within its interval. This holds its current direction, not the road center.
Before a race, D-pad and left-stick directions follow the same navigation:
vertical selects an option and horizontal changes its value. The default race
is three laps.

Collisions and driving off the road reduce speed. Collision bounds use the
selected car's physical width and length. `CONTACT!` indicates a recent hit
and remains visible for 0.9 seconds, even after the cars separate. Passing
traffic earns points.

Two mountain ranges scroll at different parallax speeds as the camera turns.
The sun stays due south in the world and appears only when that direction is
in view; it is not marked on the overview map.

## Gamepad Visualizer

Run the live raw-input visualizer with `uv run python -m script.gamepad_visualizer`.
It also visualizes accelerometer and gyroscope vectors on 3D-style spheres and
smooths the readouts when a connected controller exposes motion sensors. The
screenshot shows a sample active input state.

![Gamepad visualizer showing sample stick, trigger, button, and hat input](doc/gamepad-visualizer.png)

## Structure

- [src/racer.py](src/racer.py) manages startup, the game loop, and shutdown.
- [src/racer/input.py](src/racer/input.py) translates keyboard and gamepad input
  into driving controls and menu actions.
- [src/racer/game_state.py](src/racer/game_state.py) defines car types and
  immutable race state, and simulates driving, collisions, and race progress.
- [src/racer/track.py](src/racer/track.py) provides the Hockenheim and
  Nurburgring GP circuit geometry shared by simulation, rendering, and maps.
- [src/racer/rendering.py](src/racer/rendering.py) composes scenery, cars, and
  the HUD without modifying race state.
- [src/racer/rendering_geometry.py](src/racer/rendering_geometry.py) handles
  camera projection, road geometry, and the checkered start line.
- [src/racer/rendering_cars.py](src/racer/rendering_cars.py) draws the Formula
  and Classic car silhouettes.
- [Software Architecture](doc/software_architecture.md) describes the application modules and runtime flow.
- [Software Requirements Specification](doc/requirements.md) records functional requirements and verification cases.
