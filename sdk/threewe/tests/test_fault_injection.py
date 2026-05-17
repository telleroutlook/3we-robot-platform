# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the fault injection module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from threewe.sim.fault_injection import FaultConfig, FaultInjector


@pytest.fixture()
def mock_backend():
    """Create a mock backend with sensible sensor defaults."""
    backend = MagicMock()
    backend.is_connected = True
    backend.get_camera_image.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    backend.get_lidar_scan.return_value = MagicMock(ranges=np.ones(360, dtype=np.float32))
    backend.get_pose.return_value = MagicMock(x=1.0, y=2.0, theta=0.0)
    backend.get_velocity.return_value = MagicMock(vx=0.1, vy=0.0, omega=0.0)
    backend.get_imu.return_value = MagicMock()
    backend.get_wheel_speeds.return_value = np.array([100.0, 100.0, 100.0, 100.0])
    backend.get_motor_current.return_value = np.array([0.5, 0.5, 0.5, 0.5])
    return backend


class TestFaultConfigDefaults:
    def test_default_config_has_no_faults(self):
        cfg = FaultConfig()
        assert cfg.latency_ms == 0.0
        assert cfg.packet_loss_rate == 0.0
        assert cfg.disconnect_after_s is None

    def test_config_is_frozen(self):
        cfg = FaultConfig()
        with pytest.raises((TypeError, AttributeError)):
            cfg.latency_ms = 100.0  # type: ignore[misc]


class TestPassthrough:
    def test_non_sensor_methods_pass_through(self, mock_backend):
        injector = FaultInjector(mock_backend)
        injector.set_velocity(1.0, 0.0, 0.0)
        mock_backend.set_velocity.assert_called_once_with(1.0, 0.0, 0.0)

    def test_is_connected_passes_through(self, mock_backend):
        injector = FaultInjector(mock_backend)
        assert injector.is_connected is True


class TestLatencyInjection:
    def test_latency_adds_delay(self, mock_backend):
        cfg = FaultConfig(latency_ms=50)
        injector = FaultInjector(mock_backend, cfg)

        start = time.monotonic()
        injector.get_camera_image()
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms >= 45  # allow small timing variance

    def test_jitter_varies_delay(self, mock_backend):
        cfg = FaultConfig(latency_ms=10, latency_jitter_ms=20)
        injector = FaultInjector(mock_backend, cfg)

        delays = []
        for _ in range(10):
            start = time.monotonic()
            injector.get_camera_image()
            delays.append((time.monotonic() - start) * 1000)

        assert max(delays) - min(delays) > 1.0  # jitter produces variance

    def test_zero_latency_no_delay(self, mock_backend):
        cfg = FaultConfig(latency_ms=0)
        injector = FaultInjector(mock_backend, cfg)

        start = time.monotonic()
        injector.get_camera_image()
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 50


class TestPacketLoss:
    def test_loss_returns_stale_data(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=1.0)
        injector = FaultInjector(mock_backend, cfg)

        # First call populates the cache (no stale data yet, so it goes through)
        result1 = injector.get_camera_image()
        # Second call should return stale cache
        mock_backend.get_camera_image.return_value = np.ones((480, 640, 3), dtype=np.uint8)
        result2 = injector.get_camera_image()

        assert np.array_equal(result1, result2)

    def test_no_loss_returns_fresh_data(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=0.0)
        injector = FaultInjector(mock_backend, cfg)

        injector.get_camera_image()
        mock_backend.get_camera_image.return_value = np.ones((480, 640, 3), dtype=np.uint8)
        result = injector.get_camera_image()

        assert np.all(result == 1)

    def test_partial_loss_rate(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=0.5, seed=123)
        injector = FaultInjector(mock_backend, cfg)

        # Run many calls, some should be fresh, some stale
        injector.get_pose()  # populate cache
        for _ in range(100):
            injector.get_pose()
        # With 50% loss, we expect the backend to be called less than 100 additional times
        assert mock_backend.get_pose.call_count < 101


class TestDisconnection:
    def test_disconnect_raises_timeout(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.0, disconnect_duration_s=10.0)
        injector = FaultInjector(mock_backend, cfg)

        from threewe.exceptions import RobotTimeoutError

        with pytest.raises(RobotTimeoutError, match="fault injection"):
            injector.get_camera_image()

    def test_disconnect_returns_stale_if_cached(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.1, disconnect_duration_s=10.0)
        injector = FaultInjector(mock_backend, cfg)

        # Populate cache before disconnect
        result_before = injector.get_camera_image()
        time.sleep(0.15)  # trigger disconnect window

        result_during = injector.get_camera_image()
        assert np.array_equal(result_before, result_during)

    def test_reconnects_after_duration(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.0, disconnect_duration_s=0.05)
        injector = FaultInjector(mock_backend, cfg)

        # Initially disconnected — populate stale first by manipulating start time
        injector._stale_cache["get_camera_image"] = np.zeros((1,), dtype=np.uint8)
        injector.get_camera_image()  # stale, from disconnect

        time.sleep(0.1)  # disconnect window expires
        result = injector.get_camera_image()
        # Should now call the real backend
        assert np.array_equal(result, mock_backend.get_camera_image.return_value)


class TestCallCounting:
    def test_call_count_increments(self, mock_backend):
        injector = FaultInjector(mock_backend)
        assert injector.call_count == 0
        injector.get_camera_image()
        injector.get_pose()
        assert injector.call_count == 2


class TestSeedReproducibility:
    def test_same_seed_same_behavior(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=0.5, seed=99)

        injector1 = FaultInjector(mock_backend, cfg)
        injector2 = FaultInjector(mock_backend, cfg)

        # Populate cache
        injector1.get_pose()
        injector2.get_pose()

        drops1 = [injector1._should_drop() for _ in range(50)]
        drops2 = [injector2._should_drop() for _ in range(50)]
        assert drops1 == drops2
