---
Platform: Reddit
Subreddit: r/python
---

# Show r/Python: A robotics SDK where the same async API controls mock sim, Gazebo, and real hardware

I built a Python SDK for controlling robots where you write your code once and switch between backends without changes:

```python
from threewe import Robot

async with Robot(backend="mock") as robot:
    await robot.move_to(x=3.0, y=2.0)
    scan = robot.get_lidar_scan()  # 360-element numpy array
    pose = robot.get_pose()        # typed NamedTuple
```

Change `"mock"` to `"gazebo"` or `"real"` — same code, different backend.

**Design choices I'd like feedback on:**

1. **Async context manager pattern** — `async with Robot(...) as robot:` handles connection lifecycle. Is this idiomatic enough, or would you prefer explicit `connect()`/`disconnect()`?

2. **Typed returns** — every method returns typed dataclasses/NamedTuples (`Pose`, `LidarScan`, `NavigationResult`), not dicts. Full type hints throughout.

3. **Zero mandatory deps for mock** — `pip install -e sdk/threewe/` requires only numpy. AI features (VLM) and simulation (Gymnasium) are optional extras: `pip install threewe[ai]`, `pip install threewe[sim]`.

4. **Backend abstraction** — all backends implement the same `Backend` protocol. Adding a new simulator = implement ~10 methods.

**Try it:**

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

Needs Python 3.10+ and numpy. The mock backend simulates 2D navigation with collision detection and LiDAR raycasting — actual computation, not just returning dummy values.

**What it's for:** This is the SDK layer for an open-source robot platform (ESP32-S3 + Raspberry Pi 5, <$500 hardware). The goal is making robot programming as accessible as `import requests` — researchers write Python, the SDK handles ROS2/firmware/hardware.

309 tests passing, 0.1.0-alpha. Not on PyPI yet (install from source).

GitHub: https://github.com/telleroutlook/3we-robot-platform
