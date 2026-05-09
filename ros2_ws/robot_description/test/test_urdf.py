# SPDX-License-Identifier: Apache-2.0
"""Validates the robot URDF/Xacro model parses correctly and has expected structure."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parent.parent
XACRO_FILE = PKG_DIR / "urdf" / "robot.urdf.xacro"

EXPECTED_LINKS = [
    "base_footprint",
    "base_link",
    "front_left_wheel_link",
    "front_right_wheel_link",
    "rear_left_wheel_link",
    "rear_right_wheel_link",
    "imu_link",
    "ultrasonic_front_link",
    "ultrasonic_back_link",
    "ultrasonic_left_link",
    "ultrasonic_right_link",
    "payload_mount_link",
]

WHEEL_LINKS = [
    "front_left_wheel_link",
    "front_right_wheel_link",
    "rear_left_wheel_link",
    "rear_right_wheel_link",
]

WHEEL_JOINTS = [
    "front_left_wheel_joint",
    "front_right_wheel_joint",
    "rear_left_wheel_joint",
    "rear_right_wheel_joint",
]


@pytest.fixture(scope="module")
def urdf_xml() -> ET.Element:
    """Process the Xacro file and return parsed XML root."""
    try:
        import xacro
    except ImportError:
        pytest.skip("xacro package not available")

    doc = xacro.process_file(str(XACRO_FILE))
    xml_str = doc.toprettyxml(indent="  ")
    return ET.fromstring(xml_str)


def _get_links(root: ET.Element) -> list[str]:
    return [link.get("name", "") for link in root.findall("link")]


def _get_joints(root: ET.Element) -> list[ET.Element]:
    return root.findall("joint")


def test_xacro_processes_without_errors(urdf_xml: ET.Element) -> None:
    assert urdf_xml.tag == "robot"
    assert urdf_xml.get("name") is not None


def test_expected_links_exist(urdf_xml: ET.Element) -> None:
    links = _get_links(urdf_xml)
    for expected in EXPECTED_LINKS:
        assert expected in links, f"Missing link: {expected}"


def test_expected_joints_exist(urdf_xml: ET.Element) -> None:
    joint_names = [j.get("name", "") for j in _get_joints(urdf_xml)]
    for expected in WHEEL_JOINTS:
        assert expected in joint_names, f"Missing joint: {expected}"


def test_wheel_joints_are_continuous(urdf_xml: ET.Element) -> None:
    joints = {j.get("name"): j for j in _get_joints(urdf_xml)}
    for name in WHEEL_JOINTS:
        joint = joints[name]
        assert joint.get("type") == "continuous", f"{name} should be continuous"
        axis = joint.find("axis")
        assert axis is not None
        xyz = axis.get("xyz", "").split()
        assert xyz == ["0", "1", "0"], f"{name} axis should be [0,1,0], got {xyz}"


def test_chassis_dimensions(urdf_xml: ET.Element) -> None:
    base_link = None
    for link in urdf_xml.findall("link"):
        if link.get("name") == "base_link":
            base_link = link
            break
    assert base_link is not None

    box = base_link.find(".//visual/geometry/box")
    assert box is not None
    size = [float(v) for v in box.get("size", "").split()]
    assert abs(size[0] - 0.300) < 0.001
    assert abs(size[1] - 0.250) < 0.001
    assert abs(size[2] - 0.080) < 0.001


def test_wheel_radius(urdf_xml: ET.Element) -> None:
    for link in urdf_xml.findall("link"):
        if link.get("name") in WHEEL_LINKS:
            cylinder = link.find(".//visual/geometry/cylinder")
            assert cylinder is not None, f"Wheel {link.get('name')} missing cylinder"
            radius = float(cylinder.get("radius", "0"))
            assert abs(radius - 0.024) < 0.001


def test_all_links_have_inertia(urdf_xml: ET.Element) -> None:
    for link in urdf_xml.findall("link"):
        name = link.get("name", "")
        if name == "base_footprint":
            continue
        inertial = link.find("inertial")
        assert inertial is not None, f"Link {name} missing <inertial>"


def test_mass_values_positive(urdf_xml: ET.Element) -> None:
    for link in urdf_xml.findall("link"):
        name = link.get("name", "")
        if name == "base_footprint":
            continue
        mass_elem = link.find(".//inertial/mass")
        assert mass_elem is not None, f"Link {name} missing mass"
        mass = float(mass_elem.get("value", "0"))
        assert mass > 0, f"Link {name} has non-positive mass: {mass}"
