"""Immutable game state and pure race simulation functions."""

import math
from dataclasses import dataclass, replace

from .input import DriveInput
from .track import DEFAULT_TRACK, ROAD_HALF_WIDTH, Track, sample_track

START_SPEED = 0.0
MAX_SPEED = 300.0
WHEELBASE = 2.7
MAX_STEERING_ANGLE = 0.8
MAX_HEADING_ERROR = 0.10
GRID_START_DISTANCE = 18.0
START_LIGHTS_DURATION = 5.0
START_LIGHT_COUNT = 5
ACCELERATION_RATE = 42.0
COAST_DECELERATION = 8.0
BRAKE_DECELERATION = 100.0
OFFROAD_THRESHOLD = 1.1
OFFROAD_ACCELERATION_SCALE = 0.65
OFFROAD_SPEED_DRAG = 0.18
LAP_OPTIONS = (1, 3, 5)
DEFAULT_LAP_COUNT = 3

LANES = (-0.66, 0.0, 0.66)
TRAFFIC_COLORS = (
    (238, 91, 67),
    (80, 188, 207),
    (238, 193, 72),
    (187, 110, 187),
)


@dataclass(frozen=True)
class CarType:
    """Visual model, dimensions in meters, and relative driving performance."""

    shape: str
    name: str
    acceleration: float
    braking: float
    width: float
    length: float


CAR_TYPES = (
    CarType(
        shape="f1",
        name="FORMULA",
        acceleration=1.0,
        braking=1.0,
        width=1.8,
        length=5.5,
    ),
    CarType(
        shape="simple",
        name="CLASSIC",
        acceleration=0.7,
        braking=0.8,
        width=1.8,
        length=4.2,
    ),
)


@dataclass(frozen=True)
class TrafficCar:
    """Traffic vehicle data expressed in track coordinates."""

    distance: float
    lane: float
    color: tuple[int, int, int]


@dataclass(frozen=True)
class GameState:
    """Complete immutable state for one race."""

    distance: float
    speed: float
    lateral: float
    score: int
    crash_time: float
    game_over: bool
    traffic: tuple[TrafficCar, ...]
    next_traffic_id: int
    track: Track
    lap_count: int
    countdown: float
    heading_error: float = 0.0


def _traffic_car(distance: float, identifier: int) -> TrafficCar:
    lane = LANES[(identifier * 2 + 1) % len(LANES)]
    color = TRAFFIC_COLORS[(identifier * 3) % len(TRAFFIC_COLORS)]
    return TrafficCar(distance, lane, color)


def new_game(
    track: Track = DEFAULT_TRACK, lap_count: int = DEFAULT_LAP_COUNT
) -> GameState:
    """Return a deterministic fresh race state."""
    if lap_count < 1:
        raise ValueError("lap_count must be positive")
    traffic = tuple(
        _traffic_car(290 + index * 235, index) for index in range(10)
    )
    return GameState(
        distance=-GRID_START_DISTANCE,
        speed=START_SPEED,
        lateral=0.0,
        score=0,
        crash_time=0.0,
        game_over=False,
        traffic=traffic,
        next_traffic_id=len(traffic),
        track=track,
        lap_count=lap_count,
        countdown=START_LIGHTS_DURATION,
    )


def _has_collision(
    traffic: tuple[TrafficCar, ...],
    distance: float,
    lateral: float,
    car_type: CarType = CAR_TYPES[0],
) -> bool:
    return any(
        abs(car.distance - distance) < car_type.length
        and abs(car.lane - lateral) * ROAD_HALF_WIDTH < car_type.width
        for car in traffic
    )


def _advance_traffic(
    traffic: tuple[TrafficCar, ...], distance: float, next_traffic_id: int
) -> tuple[tuple[TrafficCar, ...], int, int]:
    remaining = tuple(car for car in traffic if car.distance >= distance - 12)
    passed_count = len(traffic) - len(remaining)
    if (
        not remaining
        or max(car.distance for car in remaining) < distance + 1500
    ):
        spawn_gap = 1800 + (next_traffic_id * 173 % 501)
        remaining += (_traffic_car(distance + spawn_gap, next_traffic_id),)
        next_traffic_id += 1
    return remaining, next_traffic_id, passed_count


def step_game(
    state: GameState,
    controls: DriveInput,
    delta_time: float,
    car_type: CarType = CAR_TYPES[0],
) -> GameState:
    """Return the next race state without mutating the input state."""
    if state.game_over:
        return state
    if state.countdown > 0:
        countdown = max(0.0, state.countdown - delta_time)
        if countdown < 1e-9:
            countdown = 0.0
        return replace(
            state,
            countdown=countdown,
        )

    speed = state.speed
    throttle = max(0.0, min(1.0, controls.accelerate))
    brake = max(0.0, min(1.0, controls.brake))
    offroad = abs(state.lateral) > OFFROAD_THRESHOLD
    acceleration = ACCELERATION_RATE * throttle * car_type.acceleration
    if offroad:
        acceleration *= OFFROAD_ACCELERATION_SCALE
    speed += (acceleration - COAST_DECELERATION) * delta_time
    speed -= BRAKE_DECELERATION * brake * car_type.braking * delta_time
    speed = max(0.0, min(MAX_SPEED, speed))

    velocity = speed / 3.6
    steering = max(-1.0, min(1.0, controls.steering))
    steering_angle = steering * MAX_STEERING_ANGLE / (1 + velocity / 60)
    yaw_rate = velocity * math.tan(steering_angle) / WHEELBASE
    current_track = sample_track(state.distance, state.track)
    path_scale = max(
        0.5,
        1 - current_track.curvature * state.lateral * ROAD_HALF_WIDTH,
    )
    distance = state.distance + (
        velocity * math.cos(state.heading_error) / path_scale * delta_time
    )
    finish_distance = state.track.length * state.lap_count
    distance = min(distance, finish_distance)
    next_track = sample_track(distance, state.track)
    road_turn = math.atan2(
        math.sin(next_track.heading - current_track.heading),
        math.cos(next_track.heading - current_track.heading),
    )
    heading_error = max(
        -MAX_HEADING_ERROR,
        min(
            MAX_HEADING_ERROR,
            state.heading_error + yaw_rate * delta_time - road_turn,
        ),
    )
    lateral = state.lateral + (
        velocity
        * math.sin((state.heading_error + heading_error) / 2)
        * delta_time
        / ROAD_HALF_WIDTH
    )
    lateral = max(-1.12, min(1.12, lateral))

    crash_time = max(0.0, state.crash_time - delta_time)

    if offroad:
        speed = max(0.0, speed - speed * OFFROAD_SPEED_DRAG * delta_time)
    if crash_time <= 0 and _has_collision(
        state.traffic, distance, lateral, car_type
    ):
        speed *= 0.48
        crash_time = 0.9

    traffic, next_traffic_id, passed_count = _advance_traffic(
        state.traffic, distance, state.next_traffic_id
    )
    return replace(
        state,
        distance=distance,
        speed=speed,
        lateral=lateral,
        score=state.score + passed_count * 250,
        crash_time=crash_time,
        game_over=distance >= finish_distance,
        traffic=traffic,
        next_traffic_id=next_traffic_id,
        heading_error=heading_error,
    )
