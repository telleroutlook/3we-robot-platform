# SPDX-License-Identifier: Apache-2.0
from setuptools import find_packages, setup

package_name = "robot_competition"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/competition.launch.py"]),
        ("share/" + package_name + "/config", ["config/competition_params.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="3WE Robot Team",
    maintainer_email="dev@3we.org",
    description="RoboCup Logistics League competition nodes",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "referee_client = robot_competition.referee_client_node:main",
            "mps_detector = robot_competition.mps_detector_node:main",
            "task_executor = robot_competition.task_executor_node:main",
            "fleet_coordinator = robot_competition.fleet_coordinator_node:main",
        ],
    },
)
