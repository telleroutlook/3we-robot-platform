from setuptools import setup

package_name = "robot_diagnostics"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/config",
            [
                "config/health_thresholds.yaml",
                "config/notifications.yaml",
            ],
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Robot Platform Contributors",
    maintainer_email="dev@robot-platform.org",
    description="Diagnostics aggregator and fleet telemetry bridge",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "diagnostics_node = robot_diagnostics.diagnostics_node:main",
            "mqtt_bridge_node = robot_diagnostics.mqtt_bridge_node:main",
            "health_monitor_node = robot_diagnostics.health_monitor_node:main",
            "notification_dispatcher = robot_diagnostics.notification_dispatcher:main",
        ],
    },
)
