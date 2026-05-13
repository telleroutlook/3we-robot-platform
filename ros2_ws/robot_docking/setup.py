# SPDX-License-Identifier: Apache-2.0
from setuptools import setup

package_name = "robot_docking"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/docking_params.yaml"]),
        ("share/" + package_name + "/launch", ["launch/docking.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Platform Contributors",
    maintainer_email="dev@robot-platform.org",
    description="Autonomous charging dock approach and docking via AprilTag visual servoing",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "docking_controller = robot_docking.docking_controller:main",
            "visual_servo = robot_docking.visual_servo:main",
            "contact_detector = robot_docking.contact_detector:main",
            "apriltag_detector = robot_docking.apriltag_detector:main",
        ],
    },
)
