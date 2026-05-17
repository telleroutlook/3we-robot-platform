# SPDX-License-Identifier: Apache-2.0
"""Integration tests for fault injection — verify graceful degradation.

These tests use the MockBackend (no ROS2 required) to validate that the
Robot class and higher-level operations handle communication faults without
crashing or entering undefined states.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from threewe.sim.fault_injection import FaultConfig, FaultInjector


pytestmark = [pytest.mark.simulation, pytest.mark.timeout(30)]


@pytest.fixture()
def mock_backend():
    """Stand up a MockBackend for fault injection tests."""
    from threewe.config import load_config
    from threewe.backends.mock import MockBackend

    config = load_config("standard_v2")
    backend = MockBackend(config, scene="office_v2")
    backend.connect()
    yield backend
    backend.disconnect()


class TestLatencyResilience:
    """Verify operations complete under high latency."""

    def test_sensor_reads_with_50ms_latency(self, mock_backend):
        cfg = FaultConfig(latency_ms=50, latency_jitter_ms=20)
        faulty = FaultInjector(mock_backend, cfg)

        start = time.monotonic()
        image = faulty.get_camera_image()
        elapsed = time.monotonic() - start

        assert image is not None
        assert image.shape[2] == 3
        assert elapsed >= 0.04

    def test_consecutive_reads_all_succeed(self, mock_backend):
        cfg = FaultConfig(latency_ms=20, latency_jitter_ms=10)
        faulty = FaultInjector(mock_backend, cfg)

        for _ in range(10):
            pose = faulty.get_pose()
            assert hasattr(pose, "x")
            assert hasattr(pose, "y")


class TestPacketLossResilience:
    """Verify stale-data fallback under packet loss."""

    def test_heavy_loss_returns_valid_data(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=0.8, seed=42)
        faulty = FaultInjector(mock_backend, cfg)

        results = []
        for _ in range(20):
            scan = faulty.get_lidar_scan()
            results.append(scan)

        # All results should be valid (either fresh or stale)
        assert all(r is not None for r in results)

    def test_velocity_commands_unaffected_by_loss(self, mock_backend):
        cfg = FaultConfig(packet_loss_rate=0.9)
        faulty = FaultInjector(mock_backend, cfg)

        # set_velocity is a command, not a sensor read — should pass through
        faulty.set_velocity(0.5, 0.0, 0.1)
        vel = mock_backend.get_velocity()
        assert vel.vx != 0.0 or vel.omega != 0.0


class TestDisconnectionResilience:
    """Verify disconnect/reconnect behavior."""

    def test_disconnect_with_cached_data_returns_stale(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.05, disconnect_duration_s=5.0)
        faulty = FaultInjector(mock_backend, cfg)

        # Read before disconnect to populate cache
        initial_image = faulty.get_camera_image()
        time.sleep(0.1)

        # During disconnect, should get stale data
        stale_image = faulty.get_camera_image()
        assert stale_image is not None
        assert np.array_equal(initial_image, stale_image)

    def test_disconnect_without_cache_raises(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.0, disconnect_duration_s=5.0)
        faulty = FaultInjector(mock_backend, cfg)

        from threewe.exceptions import RobotTimeoutError

        with pytest.raises(RobotTimeoutError):
            faulty.get_camera_image()

    def test_recovery_after_disconnect_window(self, mock_backend):
        cfg = FaultConfig(disconnect_after_s=0.0, disconnect_duration_s=0.05)
        faulty = FaultInjector(mock_backend, cfg)

        # Populate cache for disconnect period
        faulty._stale_cache["get_camera_image"] = np.zeros((1,), dtype=np.uint8)

        time.sleep(0.1)  # wait for disconnect window to expire
        image = faulty.get_camera_image()
        # Should get fresh data from backend (not stale)
        assert image.shape == (480, 640, 3)


class TestCombinedFaults:
    """Verify behavior under multiple simultaneous faults."""

    def test_latency_plus_packet_loss(self, mock_backend):
        cfg = FaultConfig(latency_ms=30, packet_loss_rate=0.3, seed=7)
        faulty = FaultInjector(mock_backend, cfg)

        results = []
        for _ in range(20):
            pose = faulty.get_pose()
            results.append(pose)

        assert all(r is not None for r in results)
        assert faulty.call_count == 20

    def test_all_sensor_methods_tolerate_faults(self, mock_backend):
        cfg = FaultConfig(latency_ms=10, packet_loss_rate=0.2, seed=55)
        faulty = FaultInjector(mock_backend, cfg)

        # Exercise every sensor method
        faulty.get_camera_image()
        faulty.get_lidar_scan()
        faulty.get_pose()
        faulty.get_velocity()
        faulty.get_imu()
        faulty.get_battery_state()
        faulty.get_wheel_speeds()
        faulty.get_motor_current()

        assert faulty.call_count == 8
