---
Platform: Hacker News
Type: Show HN
---

# Show HN: Open-source robot platform with a Python SDK – mock backend runs with zero deps

Title (≤80 chars):
Show HN: Open-source robot platform – same Python API for sim and real hardware

URL to submit:
https://github.com/telleroutlook/3we-robot-platform

Text (optional, for the comment body — HN "Show HN" posts can have either a URL or text, not both. Submit the URL, then post this as the first comment):

---

I built an open-source robot platform (ESP32-S3 + Raspberry Pi 5, mecanum wheels, ROS2) with a Python SDK that abstracts away the robotics stack entirely:

```python
from threewe import Robot

async with Robot(backend="mock") as robot:
    await robot.move_to(x=3.0, y=2.0)
    scan = robot.get_lidar_scan()
```

The same code runs on `backend="mock"` (pure Python, only numpy), `backend="gazebo"`, or `backend="real"` — zero changes.

The mock backend does 2D kinematics with collision detection and LiDAR raycasting. It's not a toy stub — 309 tests pass against it. You can try it in 30 seconds:

```
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

Requires Python 3.10+ and numpy. No ROS2, no GPU, no account.

What's there today:
- Mock backend with full 2D navigation simulation
- gymnasium.make("3we/Navigation-v1") for RL training
- VLM integration (GPT-4o / Qwen-VL → robot actions)
- HDF5 trajectory recording
- Open hardware: KiCad PCB, full BOM, <$500 to reproduce

What's not done yet:
- Gazebo/Isaac Sim backend integration testing
- Not on PyPI yet (install from source)
- No real hardware video yet (boards are assembled, validation in progress)

The honest dev log about hardware decisions and prototyping failures: https://3we.org/blog/dev-log-001/

I'd appreciate feedback on the SDK API design — especially from anyone who's built Gymnasium environments or worked with Nav2.
