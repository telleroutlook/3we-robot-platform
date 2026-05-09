# SPDX-License-Identifier: Apache-2.0
"""Setup script for robot_perception package."""

from setuptools import find_packages, setup

package_name = "robot_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="3WE Team",
    maintainer_email="team@3we.org",
    description="Hailo AI accelerator inference node for object detection",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "inference_node = robot_perception.inference_node:main",
        ],
    },
)
