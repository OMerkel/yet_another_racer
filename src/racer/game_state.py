"""Immutable game state and pure race simulation functions."""

import math
from dataclasses import dataclass, replace

from .input import DriveInput

RACE_SECONDS = 90.0
START_SPEED = 120.0
MAX_SPEED = 300.0
MAX_WORLD_SPEED_FACTOR = 2.0
MAX_STEERING_RATE = (1.15 + MAX_SPEED / 140) / 2

LANES = (-0.66, 0.0, 0.66)
TRAFFIC_COLORS = (
    (238, 91, 67),
    (80, 188, 207),
    (238, 193, 72),
    (187, 110, 187),
)


@dataclass(frozen=True)
class CarType:
    """Visual model and relative acceleration and braking for a car."""

    shape: str
    name: str
    acceleration: float
    braking: float


CAR_TYPES = (
    CarType(shape="f1", name="FORMULA", acceleration=1.0, braking=1.0),
    CarType(shape="simple", name="CLASSIC", acceleration=0.7, braking=0.8),
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
    time_left: float
    score: int
    crash_time: float
    game_over: bool
    traffic: tuple[TrafficCar, ...]
    next_traffic_id: int


def _traffic_car(distance: float, identifier: int) -> TrafficCar:
    lane = LANES[(identifier * 2 + 1) % len(LANES)]
    color = TRAFFIC_COLORS[(identifier * 3) % len(TRAFFIC_COLORS)]
    return TrafficCar(distance, lane, color)


def new_game() -> GameState:
    """Return a deterministic fresh race state."""
    traffic = tuple(
        _traffic_car(290 + index * 235, index) for index in range(10)
    )
    return GameState(
        distance=0.0,
        speed=START_SPEED,
        lateral=0.0,
        time_left=RACE_SECONDS,
        score=0,
        crash_time=0.0,
        game_over=False,
        traffic=traffic,
        next_traffic_id=len(traffic),
    )


def _has_collision(
    traffic: tuple[TrafficCar, ...], distance: float, lateral: float
) -> bool:
    return any(
        -3 < car.distance - distance < 9 and abs(car.lane - lateral) < 0.32
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

    speed = state.speed
    throttle = max(0.0, min(1.0, controls.accelerate))
    brake = max(0.0, min(1.0, controls.brake))
    speed += (140 * throttle * car_type.acceleration - 14) * delta_time
    speed -= 180 * brake * car_type.braking * delta_time
    speed = max(0.0, min(MAX_SPEED, speed))

    steering_gain = MAX_STEERING_RATE * (speed / MAX_SPEED)
    lateral = state.lateral + controls.steering * steering_gain * delta_time
    lateral -= (
        math.sin(state.distance * 0.0016)
        * (speed / MAX_SPEED)
        * 0.11
        * delta_time
    )
    lateral = max(-1.12, min(1.12, lateral))

    world_speed_factor = 1 + speed / MAX_SPEED * (MAX_WORLD_SPEED_FACTOR - 1)
    distance = (
        state.distance + speed * 0.44704 * world_speed_factor * delta_time
    )
    time_left = max(0.0, state.time_left - delta_time)
    crash_time = max(0.0, state.crash_time - delta_time)

    if abs(lateral) > 0.94:
        speed = max(50.0, speed - 125 * delta_time)
    if crash_time <= 0 and _has_collision(state.traffic, distance, lateral):
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
        time_left=time_left,
        score=state.score + passed_count * 250,
        crash_time=crash_time,
        game_over=time_left <= 0,
        traffic=traffic,
        next_traffic_id=next_traffic_id,
    )
