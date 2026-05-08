# SPDX-License-Identifier: Apache-2.0
"""Tests that robot_interfaces message and service types are importable and well-formed."""


def test_wheel_speeds_importable():
    from robot_interfaces.msg import WheelSpeeds

    msg = WheelSpeeds()
    assert hasattr(msg, "header")
    assert hasattr(msg, "front_left")
    assert hasattr(msg, "front_right")
    assert hasattr(msg, "rear_left")
    assert hasattr(msg, "rear_right")


def test_wheel_speeds_default_values():
    from robot_interfaces.msg import WheelSpeeds

    msg = WheelSpeeds()
    assert msg.front_left == 0.0
    assert msg.front_right == 0.0
    assert msg.rear_left == 0.0
    assert msg.rear_right == 0.0


def test_emergency_stop_state_importable():
    from robot_interfaces.msg import EmergencyStopState

    msg = EmergencyStopState()
    assert hasattr(msg, "header")
    assert hasattr(msg, "stopped")
    assert hasattr(msg, "state")
    assert hasattr(msg, "reason")


def test_emergency_stop_state_constants():
    from robot_interfaces.msg import EmergencyStopState

    assert EmergencyStopState.STATE_NORMAL == 0
    assert EmergencyStopState.STATE_ESTOPPED == 1
    assert EmergencyStopState.STATE_RECOVERY == 2


def test_payload_state_importable():
    from robot_interfaces.msg import PayloadState

    msg = PayloadState()
    assert hasattr(msg, "header")
    assert hasattr(msg, "payload_id")
    assert hasattr(msg, "name")
    assert hasattr(msg, "connected")
    assert hasattr(msg, "power_5v_active")
    assert hasattr(msg, "power_12v_active")
    assert hasattr(msg, "power_vbat_active")
    assert hasattr(msg, "current_5v")
    assert hasattr(msg, "current_12v")
    assert hasattr(msg, "power_consumption_watts")
    assert hasattr(msg, "status")


def test_payload_state_constants():
    from robot_interfaces.msg import PayloadState

    assert PayloadState.STATUS_IDLE == 0
    assert PayloadState.STATUS_ACTIVE == 1
    assert PayloadState.STATUS_ERROR == 2
    assert PayloadState.STATUS_UPDATING == 3


def test_emergency_stop_srv_importable():
    from robot_interfaces.srv import EmergencyStop

    req = EmergencyStop.Request()
    resp = EmergencyStop.Response()
    assert hasattr(req, "reason")
    assert hasattr(resp, "success")
    assert hasattr(resp, "current_state")
    assert hasattr(resp, "message")


def test_emergency_stop_srv_constants():
    from robot_interfaces.srv import EmergencyStop

    assert EmergencyStop.Response.STATE_NORMAL == 0
    assert EmergencyStop.Response.STATE_ESTOPPED == 1
    assert EmergencyStop.Response.STATE_RECOVERY == 2
    assert EmergencyStop.Response.STATE_RELAY_FAULT == 3


def test_payload_power_srv_importable():
    from robot_interfaces.srv import PayloadPower

    req = PayloadPower.Request()
    resp = PayloadPower.Response()
    assert hasattr(req, "payload_id")
    assert hasattr(req, "rail")
    assert hasattr(req, "enable")
    assert hasattr(resp, "success")
    assert hasattr(resp, "message")
