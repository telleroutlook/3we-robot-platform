# SPDX-License-Identifier: Apache-2.0
from setuptools import setup

package_name = "robot_collection"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/collection_params.yaml"]),
        ("share/" + package_name + "/launch", ["launch/collection.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Platform Contributors",
    maintainer_email="dev@robot-platform.org",
    description="Autonomous ball collection demo with state machine orchestration",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "collection_manager = robot_collection.collection_manager_node:main",
            "ball_tracker = robot_collection.ball_tracker_node:main",
            "arm_controller = robot_collection.arm_controller_node:main",
            "basket_controller = robot_collection.basket_controller_node:main",
        ],
    },
)
