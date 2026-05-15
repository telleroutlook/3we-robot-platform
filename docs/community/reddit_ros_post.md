---
Platform: Reddit
Subreddit: r/ROS
---

# Python SDK that wraps ROS2 Nav2 behind a simple API — same code for mock/Gazebo/real

I've been building a ROS2 Jazzy robot platform (ESP32-S3 + Pi 5, mecanum drive, LD06 LiDAR, Nav2) and got tired of writing boilerplate for every experiment. So I built a Python SDK that hides all of it:

```python
from threewe import Robot

async with Robot(backend="real") as robot:
    await robot.move_to(x=3.0, y=2.0)  # calls Nav2 NavigateToPose
    scan = robot.get_lidar_scan()        # subscribes to /scan
    imu = robot.get_imu()                # subscribes to /imu/data
```

The key idea: switch `backend="real"` to `"mock"` or `"gazebo"` and the same code runs without ROS2 installed. The mock backend does 2D kinematics + LiDAR raycasting in pure Python (numpy only).

**Architecture:**

```
Your Python code
    ↓
threewe SDK (Robot class, typed returns)
    ↓
┌─────────────┬──────────────┬─────────────┐
│ MockBackend │ GazeboBackend│ RealBackend │
│ (numpy)     │ (ros_gz)     │ (rclpy)     │
└─────────────┴──────────────┴─────────────┘
```

**What works today:**
- Mock backend: 309 tests passing, full 2D nav with collision detection
- Real backend: interfaces defined, publishes to /cmd_vel, subscribes to /scan, /odom, /imu
- Gazebo backend: interface done, integration testing in progress
- Gymnasium wrapper: `gymnasium.make("3we/Navigation-v1")`

**Hardware:**
- ESP32-S3 running micro-ROS (motor PID, encoder odometry, IMU fusion)
- Pi 5 running ROS2 Jazzy (Nav2, SLAM Toolbox, perception)
- 4× mecanum wheels (omnidirectional)
- LD06 LiDAR, BNO055 IMU
- Full open hardware: KiCad PCB + BOM, <$500 total

**Try without any hardware or ROS2:**

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

**Questions:**

1. For the RealBackend, I'm wrapping Nav2's NavigateToPose action. Would you also want direct /cmd_vel access through the same API, or should that be a separate low-level interface?
2. The SDK currently assumes a single robot. For multi-robot (namespaced topics), would you expect `Robot(namespace="/robot1")` or a fleet manager class?
3. Anyone using a similar pattern (Python wrapper over ROS2) — what pain points did you hit?

GitHub: https://github.com/telleroutlook/3we-robot-platform

Dev log (ESP32-S3 vs STM32, PBC-34 bus prototyping failures): https://3we.org/blog/dev-log-001/
