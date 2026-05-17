# SPDX-License-Identifier: Apache-2.0
"""Communication fault injection for chaos engineering tests.

Wraps a BackendBase to simulate network/communication faults:
- Latency injection (configurable delay + jitter)
- Packet loss (randomly returns stale sensor data)
- Temporary disconnection (backend goes offline for a duration)

Usage::

    from threewe.sim.fault_injection import FaultConfig, FaultInjector

    config = FaultConfig(latency_ms=50, packet_loss_rate=0.1)
    faulty = FaultInjector(backend, config)
    image = faulty.get_camera_image()  # may be delayed or stale
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from random import Random
from typing import Any


@dataclass(frozen=True)
class FaultConfig:
    """Configuration for fault injection scenarios."""

    latency_ms: float = 0.0
    latency_jitter_ms: float = 0.0
    packet_loss_rate: float = 0.0
    disconnect_after_s: float | None = None
    disconnect_duration_s: float = 5.0
    seed: int = 42


_SENSOR_METHODS = frozenset(
    {
        "get_camera_image",
        "get_rgbd_image",
        "get_lidar_scan",
        "get_pose",
        "get_velocity",
        "get_imu",
        "get_battery_state",
        "get_map",
        "get_wheel_speeds",
        "get_motor_current",
    }
)


class FaultInjector:
    """Wraps a BackendBase with fault injection capabilities.

    Uses ``__getattr__`` delegation: methods not in the sensor set pass through
    unchanged. Sensor reads are subject to latency, packet loss, and disconnect.
    """

    def __init__(self, backend: Any, config: FaultConfig | None = None) -> None:
        self._backend = backend
        self._config = config or FaultConfig()
        self._rng = Random(self._config.seed)
        self._start_time = time.monotonic()
        self._stale_cache: dict[str, Any] = {}
        self._call_count = 0

    @property
    def config(self) -> FaultConfig:
        return self._config

    @property
    def is_disconnected(self) -> bool:
        """Check if currently in a simulated disconnect window."""
        if self._config.disconnect_after_s is None:
            return False
        elapsed = time.monotonic() - self._start_time
        if elapsed < self._config.disconnect_after_s:
            return False
        disconnect_elapsed = elapsed - self._config.disconnect_after_s
        return disconnect_elapsed < self._config.disconnect_duration_s

    @property
    def call_count(self) -> int:
        return self._call_count

    def _apply_latency(self) -> None:
        delay_s = self._config.latency_ms / 1000.0
        if self._config.latency_jitter_ms > 0:
            jitter = self._rng.uniform(0, self._config.latency_jitter_ms) / 1000.0
            delay_s += jitter
        if delay_s > 0:
            time.sleep(delay_s)

    def _should_drop(self) -> bool:
        return self._rng.random() < self._config.packet_loss_rate

    def _wrap_sensor_call(self, method_name: str) -> Any:
        """Return a wrapper that applies faults to the given sensor method."""

        def _faulted_call(*args: Any, **kwargs: Any) -> Any:
            self._call_count += 1

            if self.is_disconnected:
                if method_name in self._stale_cache:
                    return self._stale_cache[method_name]
                from threewe.exceptions import RobotTimeoutError

                raise RobotTimeoutError(f"Backend disconnected (fault injection): {method_name}")

            self._apply_latency()

            if self._should_drop() and method_name in self._stale_cache:
                return self._stale_cache[method_name]

            result = getattr(self._backend, method_name)(*args, **kwargs)
            self._stale_cache[method_name] = result
            return result

        return _faulted_call

    def __getattr__(self, name: str) -> Any:
        if name in _SENSOR_METHODS:
            return self._wrap_sensor_call(name)
        return getattr(self._backend, name)
