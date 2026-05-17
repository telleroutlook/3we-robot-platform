# 3we Robot Platform Documentation

AI-First Open Infrastructure for Embodied Robotics — same Python code runs in simulation and on real hardware.

---

## Quick Start

```bash
pip install threewe
```

```python
from threewe import Robot

robot = Robot(backend="gazebo")
robot.move_to(x=2.0, y=1.5)
print(robot.pose())
```

---

## Sections

<div class="grid cards" markdown>

- :material-rocket-launch: **Getting Started**

    Installation, first robot program, backend switching

    [:octicons-arrow-right-24: Basic Setup](getting_started_basic.md)
    [:octicons-arrow-right-24: AI Researchers](getting_started_ai.md)
    [:octicons-arrow-right-24: Sim2Real](guides/sim2real_quickstart.md)

- :material-api: **SDK Reference**

    Python API, auto-generated docs, web control

    [:octicons-arrow-right-24: Python API](api_reference.md)
    [:octicons-arrow-right-24: Auto-generated](reference/api.md)
    [:octicons-arrow-right-24: Web Control](web_control_api.md)

- :material-chip: **Hardware**

    Assembly, firmware, payload modules

    [:octicons-arrow-right-24: Assembly Guide](assembly_guide.md)
    [:octicons-arrow-right-24: Firmware](firmware_guide.md)
    [:octicons-arrow-right-24: PBC-34 Payload](pbc34_payload_guide.md)

- :material-chart-line: **Benchmarks**

    Leaderboard, evaluation protocol, performance

    [:octicons-arrow-right-24: Leaderboard](leaderboard.md)
    [:octicons-arrow-right-24: Performance](performance_benchmarks.md)

</div>

---

## Architecture

The platform spans five layers:

| Layer | Component | Technology |
|-------|-----------|-----------|
| SDK | `threewe` Python package | Python 3.10+, Gymnasium |
| Web | Real-time control UI | TypeScript, Web Components |
| ROS2 | Navigation, SLAM, perception | ROS2 Humble |
| Firmware | Motor control, sensor fusion | ESP32-S3, ESP-IDF 5.x |
| Hardware | Open PCB + mechanical design | KiCad 8+, CERN-OHL-P |

---

## Links

- [GitHub Repository](https://github.com/telleroutlook/3we-robot-platform)
- [Website](https://3we.org)
- [Contributing](https://github.com/telleroutlook/3we-robot-platform/blob/main/CONTRIBUTING.md)
