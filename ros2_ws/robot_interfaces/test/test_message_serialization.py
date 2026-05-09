# SPDX-License-Identifier: Apache-2.0
"""Deep validation of message/service field behavior and value roundtrips."""

import pytest


class TestWheelSpeeds:
    """Validate WheelSpeeds message field assignment and edge cases."""

    def _make_msg(self):
        from robot_interfaces.msg import WheelSpeeds

        return WheelSpeeds()

    def test_field_assignment_roundtrip(self) -> None:
        msg = self._make_msg()
        msg.front_left = 1.5
        msg.front_right = -2.0
        msg.rear_left = 0.0
        msg.rear_right = 3.14
        assert msg.front_left == pytest.approx(1.5)
        assert msg.front_right == pytest.approx(-2.0)
        assert msg.rear_left == pytest.approx(0.0)
        assert msg.rear_right == pytest.approx(3.14)

    def test_negative_values_valid(self) -> None:
        msg = self._make_msg()
        msg.front_left = -10.0
        msg.rear_right = -0.001
        assert msg.front_left < 0
        assert msg.rear_right < 0

    def test_header_population(self) -> None:
        from builtin_interfaces.msg import Time

        msg = self._make_msg()
        msg.header.stamp = Time(sec=100, nanosec=500)
        msg.header.frame_id = "base_link"
        assert msg.header.stamp.sec == 100
        assert msg.header.stamp.nanosec == 500
        assert msg.header.frame_id == "base_link"


class TestEmergencyStopState:
    """Validate EmergencyStopState message fields and constants."""

    def _make_msg(self):
        from robot_interfaces.msg import EmergencyStopState

        return EmergencyStopState()

    def test_state_constants_reachable(self) -> None:
        from robot_interfaces.msg import EmergencyStopState

        msg = self._make_msg()
        for state_val in [
            EmergencyStopState.STATE_NORMAL,
            EmergencyStopState.STATE_ESTOPPED,
            EmergencyStopState.STATE_RECOVERY,
        ]:
            msg.state = state_val
            assert msg.state == state_val

    def test_stopped_field(self) -> None:
        msg = self._make_msg()
        msg.stopped = True
        assert msg.stopped is True
        msg.stopped = False
        assert msg.stopped is False

    def test_reason_accepts_strings(self) -> None:
        msg = self._make_msg()
        msg.reason = "watchdog timeout"
        assert msg.reason == "watchdog timeout"
        msg.reason = ""
        assert msg.reason == ""

    def test_reason_accepts_unicode(self) -> None:
        msg = self._make_msg()
        msg.reason = "紧急停止"
        assert msg.reason == "紧急停止"


class TestPayloadState:
    """Validate PayloadState message fields and status constants."""

    def _make_msg(self):
        from robot_interfaces.msg import PayloadState

        return PayloadState()

    def test_all_status_values(self) -> None:
        from robot_interfaces.msg import PayloadState

        msg = self._make_msg()
        for status_val in [
            PayloadState.STATUS_IDLE,
            PayloadState.STATUS_ACTIVE,
            PayloadState.STATUS_ERROR,
            PayloadState.STATUS_UPDATING,
        ]:
            msg.status = status_val
            assert msg.status == status_val

    def test_power_fields_as_floats(self) -> None:
        msg = self._make_msg()
        msg.current_5v = 0.250
        msg.current_12v = 1.5
        msg.power_consumption_watts = 18.75
        assert msg.current_5v == pytest.approx(0.250)
        assert msg.current_12v == pytest.approx(1.5)
        assert msg.power_consumption_watts == pytest.approx(18.75)

    def test_bool_power_rails(self) -> None:
        msg = self._make_msg()
        msg.power_5v_active = True
        msg.power_12v_active = False
        msg.power_vbat_active = True
        assert msg.power_5v_active is True
        assert msg.power_12v_active is False
        assert msg.power_vbat_active is True

    def test_payload_identity_fields(self) -> None:
        msg = self._make_msg()
        msg.payload_id = "SENSOR_V2"
        msg.name = "Environmental Monitor"
        msg.connected = True
        assert msg.payload_id == "SENSOR_V2"
        assert msg.name == "Environmental Monitor"
        assert msg.connected is True


class TestEmergencyStopService:
    """Validate EmergencyStop service request/response."""

    def test_request_roundtrip(self) -> None:
        from robot_interfaces.srv import EmergencyStop

        req = EmergencyStop.Request()
        req.reason = "obstacle detected"
        assert req.reason == "obstacle detected"

    def test_response_roundtrip(self) -> None:
        from robot_interfaces.srv import EmergencyStop

        resp = EmergencyStop.Response()
        resp.success = True
        resp.current_state = EmergencyStop.Response.STATE_ESTOPPED
        resp.message = "E-stop activated"
        assert resp.success is True
        assert resp.current_state == 1
        assert resp.message == "E-stop activated"

    def test_response_all_states(self) -> None:
        from robot_interfaces.srv import EmergencyStop

        resp = EmergencyStop.Response()
        for state_val in [
            EmergencyStop.Response.STATE_NORMAL,
            EmergencyStop.Response.STATE_ESTOPPED,
            EmergencyStop.Response.STATE_RECOVERY,
            EmergencyStop.Response.STATE_RELAY_FAULT,
        ]:
            resp.current_state = state_val
            assert resp.current_state == state_val


class TestPayloadPowerService:
    """Validate PayloadPower service request/response."""

    def test_request_rail_values(self) -> None:
        from robot_interfaces.srv import PayloadPower

        req = PayloadPower.Request()
        for rail in ["5V", "12V", "VBAT"]:
            req.rail = rail
            assert req.rail == rail

    def test_request_fields(self) -> None:
        from robot_interfaces.srv import PayloadPower

        req = PayloadPower.Request()
        req.payload_id = "LIDAR_UNIT"
        req.rail = "12V"
        req.enable = True
        assert req.payload_id == "LIDAR_UNIT"
        assert req.rail == "12V"
        assert req.enable is True

    def test_response_roundtrip(self) -> None:
        from robot_interfaces.srv import PayloadPower

        resp = PayloadPower.Response()
        resp.success = False
        resp.message = "Overcurrent protection triggered"
        assert resp.success is False
        assert resp.message == "Overcurrent protection triggered"
