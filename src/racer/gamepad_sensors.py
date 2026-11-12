"""Read game-controller motion sensors through SDL2."""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pygame

ACCELEROMETER = 1
GYROSCOPE = 2


@dataclass(frozen=True)
class SensorController:
    """An open SDL controller and its enabled motion sensor types."""

    handle: int
    enabled_sensors: frozenset[int]


@dataclass
class SensorSmoother:
    """Apply exponential smoothing to samples, tracked per device and sensor."""

    alpha: float = 0.2
    _values: dict[tuple[int, int], tuple[float, float, float]] = field(
        default_factory=dict[tuple[int, int], tuple[float, float, float]],
        init=False,
        repr=False,
    )

    def update(
        self,
        instance_id: int,
        sensor_type: int,
        values: tuple[float, float, float] | None,
    ) -> tuple[float, float, float] | None:
        """Smooth a sample, or clear its history when it is unavailable."""

        key = (instance_id, sensor_type)
        if values is None:
            self._values.pop(key, None)
            return None

        previous = self._values.get(key)
        if previous is None:
            self._values[key] = values
            return values

        smoothed = (
            previous[0] + self.alpha * (values[0] - previous[0]),
            previous[1] + self.alpha * (values[1] - previous[1]),
            previous[2] + self.alpha * (values[2] - previous[2]),
        )
        self._values[key] = smoothed
        return smoothed


class SDLControllerSensors:
    """Enable and read SDL game-controller accelerometer and gyro sensors."""

    def __init__(self, library: Any | None = None) -> None:
        self._sdl = library if library is not None else self._load_sdl()
        if self._sdl is not None and not self._configure_api():
            self._sdl = None

    @staticmethod
    def _load_sdl() -> Any | None:
        package_dir = Path(pygame.__file__).parent
        candidates = [
            package_dir / "SDL2.dll",
            *package_dir.glob("libSDL2*"),
            *package_dir.glob(".dylibs/libSDL2*"),
            *package_dir.parent.glob("pygame.libs/libSDL2*"),
        ]
        library_name = ctypes.util.find_library("SDL2")
        if library_name is not None:
            candidates.append(Path(library_name))

        for candidate in candidates:
            try:
                return ctypes.CDLL(str(candidate))
            except OSError:
                continue
        return None

    def _configure_api(self) -> bool:
        sdl = self._sdl
        if sdl is None:
            return False
        required = (
            "SDL_GameControllerOpen",
            "SDL_GameControllerHasSensor",
            "SDL_GameControllerSetSensorEnabled",
            "SDL_GameControllerGetSensorData",
            "SDL_GameControllerClose",
        )
        if any(not hasattr(sdl, name) for name in required):
            return False

        sdl.SDL_GameControllerOpen.argtypes = [ctypes.c_int]
        sdl.SDL_GameControllerOpen.restype = ctypes.c_void_p
        sdl.SDL_GameControllerHasSensor.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        sdl.SDL_GameControllerHasSensor.restype = ctypes.c_int
        sdl.SDL_GameControllerSetSensorEnabled.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
        ]
        sdl.SDL_GameControllerSetSensorEnabled.restype = ctypes.c_int
        sdl.SDL_GameControllerGetSensorData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
        ]
        sdl.SDL_GameControllerGetSensorData.restype = ctypes.c_int
        sdl.SDL_GameControllerClose.argtypes = [ctypes.c_void_p]
        sdl.SDL_GameControllerClose.restype = None
        return True

    def open(self, device_index: int) -> SensorController | None:
        """Open a mapped controller and enable its available IMU sensors."""

        if self._sdl is None:
            return None

        handle = self._sdl.SDL_GameControllerOpen(device_index)
        if not handle:
            return None

        enabled = frozenset(
            sensor_type
            for sensor_type in (ACCELEROMETER, GYROSCOPE)
            if self._sdl.SDL_GameControllerHasSensor(handle, sensor_type)
            and self._sdl.SDL_GameControllerSetSensorEnabled(
                handle, sensor_type, 1
            )
            == 0
        )
        if not enabled:
            self._sdl.SDL_GameControllerClose(handle)
            return None
        return SensorController(handle, enabled)

    def read(
        self, controller: SensorController | None, sensor_type: int
    ) -> tuple[float, float, float] | None:
        """Return the latest three-axis sensor sample when available."""

        if (
            self._sdl is None
            or controller is None
            or sensor_type not in controller.enabled_sensors
        ):
            return None

        values = (ctypes.c_float * 3)()
        result = self._sdl.SDL_GameControllerGetSensorData(
            controller.handle, sensor_type, values, len(values)
        )
        if result != 0:
            return None
        return float(values[0]), float(values[1]), float(values[2])

    def close(self, controller: SensorController) -> None:
        """Release an SDL controller handle opened for sensor access."""

        if self._sdl is not None:
            self._sdl.SDL_GameControllerClose(controller.handle)
