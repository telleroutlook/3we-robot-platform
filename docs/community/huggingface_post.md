---
Platform: HuggingFace Community Posts
---

# A Gymnasium interface for a real $300 robot — mock backend works now, no hardware needed to try

I've been building an open-source robot platform (ESP32-S3 + Raspberry Pi 5, mecanum wheels, ROS2) with a Python SDK that wraps everything behind a simple API:

```python
from threewe import Robot

async with Robot(backend="mock") as robot:
    await robot.move_to(x=3.0, y=2.0)
    scan = robot.get_lidar_scan()  # 360 rays
    pose = robot.get_pose()
```

The same code runs on `backend="mock"` (pure Python, zero deps beyond numpy), `backend="gazebo"`, or `backend="real"` — no changes needed.

**What works today:**
- Mock backend with 2D kinematics, collision detection, LiDAR raycasting — 309 tests passing
- `gymnasium.make("3we/Navigation-v1")` for RL training
- VLM integration (GPT-4o / Qwen-VL → robot actions)
- Data recording in HDF5 format (LeRobot-compatible export planned)

**Try it (30 seconds):**

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

Requires only Python 3.10+ and numpy.

**What I'm looking for feedback on:**

1. For RL researchers: is the Gymnasium env interface what you'd expect? What observations/action spaces do you want?
2. For VLM/VLA researchers: the SDK has `robot.execute_instruction("go to the red door")` — what would make this useful for your workflow?
3. For anyone doing imitation learning: trajectory recording exports to HDF5. Would direct LeRobot dataset format be more useful?

Hardware is <$500 to reproduce (full open BOM + KiCad PCB files in the repo). The full Sim2Real chain validation is the next milestone.

GitHub: https://github.com/telleroutlook/3we-robot-platform
Dev Log (design decisions + honest status): https://3we.org/blog/dev-log-001/
