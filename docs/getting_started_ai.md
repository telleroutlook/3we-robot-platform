# Getting Started — AI Researchers

> **From zero to AI-controlled robot in 5 minutes. No hardware, no ROS2, just Python.**

---

## Prerequisites

- Python 3.10+
- No ROS2 installation required
- No physical hardware required (simulation-first)

---

## 1. Install

```bash
pip install threewe[sim]
```

This installs the Python API with Gymnasium environment support. Total size ~15MB.

For VLM/VLA integration (GPT-4o, Qwen-VL):
```bash
pip install threewe[sim,ai]
```

---

## 2. Hello World (30 seconds)

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        # Sensor data — all numpy arrays
        image = robot.get_camera_image()    # (480, 640, 3) uint8
        scan = robot.get_lidar_scan()       # .ranges: (360,) float32
        pose = robot.get_pose()             # .x, .y, .theta

        # Navigate
        result = await robot.move_to(x=2.0, y=1.0)
        print(f"Arrived: {result.success}")

asyncio.run(main())
```

Switch `backend="gazebo"` to `backend="real"` — the Python API stays the same. Sim-to-real transfer in practice still depends on your task; see [Sim-to-Real Gap](sim_to_real_gap.md) for what needs tuning.

---

## 3. RL Training (Gymnasium)

Standard Gymnasium interface — plug into any RL library (SB3, CleanRL, RLlib):

```python
import gymnasium
import threewe.gym  # registers environments

env = gymnasium.make("3we/Navigation-v1")
obs, info = env.reset()

for step in range(1000):
    action = env.action_space.sample()  # replace with your policy
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

env.close()
```

**Available environments:**

| ID | Task | Difficulty |
|:---|:-----|:-----------|
| `3we/Navigation-v1` | Point-to-point navigation | Easy |
| `3we/Exploration-v1` | Map unknown area | Medium |
| `3we/ObjectNav-v1` | Find target object | Hard |
| `3we/VLN-v1` | Follow language instruction | Hard |

---

## 4. VLM-Powered Navigation

Use GPT-4o (or any VLM) to control the robot with natural language:

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        # One-line VLM instruction execution
        result = await robot.execute_instruction("find the red object and approach it")
        print(f"Done: {result.success} — {result.description}")

asyncio.run(main())
```

Requires `OPENAI_API_KEY` environment variable. See `examples/vlm_navigation.py` for the full manual VLM loop.

---

## 5. Data Collection for Imitation Learning

Record trajectories compatible with LeRobot / HuggingFace Hub:

```python
import asyncio
from threewe import Robot
from threewe.data import TrajectoryRecorder

async def main():
    async with Robot(backend="gazebo") as robot:
        recorder = TrajectoryRecorder(robot, fps=10)

        # Record while robot executes a task
        await recorder.start()
        await robot.move_to(x=3.0, y=2.0)
        trajectory = await recorder.stop()

        # Save as HDF5 (compatible with ACT, Diffusion Policy)
        trajectory.save("demo_001.hdf5")

asyncio.run(main())
```

---

## 6. Benchmark Your Model

Evaluate navigation performance with standardized metrics:

```bash
threewe benchmark run --task pointnav --episodes 100 --backend gazebo
```

Output: Success Rate, SPL (Success weighted by Path Length), collision count.

---

## What's Under the Hood

You never need to touch ROS2, but here's what happens when you call `robot.move_to()`:

```
Your Python Code
    → threewe Backend Abstraction Layer
        → [Gazebo] gz-transport + Nav2 path planner
        → [Real]   ROS2 topics + micro-ROS + ESP32 motor control
```

Same API, different physics. The abstraction guarantees identical data formats (numpy arrays, SI units, right-hand coordinate frame) regardless of backend.

---

## Next Steps

| Goal | Resource |
|:-----|:---------|
| Interactive tutorials | `notebooks/01_hello_world.ipynb` through `05_data_collection.ipynb` |
| Train RL policy | `examples/rl_obstacle_avoidance.py` |
| Deploy VLA model | `examples/vlm_navigation.py` |
| Build the hardware | [Assembly Guide](assembly_guide.md) + [BOM](https://github.com/telleroutlook/3we-robot-platform/blob/main/hardware/bom/README.md) |
| Benchmark comparison | `threewe benchmark run --help` |

---

## API Cheatsheet

```python
from threewe import Robot

async with Robot(backend="gazebo") as robot:
    # ─── Perception (all synchronous, returns numpy) ───
    robot.get_camera_image()       # (H, W, 3) uint8
    robot.get_rgbd_image()         # .rgb + .depth (meters)
    robot.get_lidar_scan()         # .ranges (N,) float32
    robot.get_pose()               # .x, .y, .theta
    robot.get_velocity()           # .vx, .vy, .omega
    robot.get_imu()                # .acceleration, .angular_velocity
    robot.get_map()                # .data (H, W) occupancy grid
    robot.get_observation()        # dict for RL: {"image", "lidar", "pose", ...}

    # ─── Action (async for motion, sync for velocity) ───
    robot.set_velocity(vx, vy, omega)   # direct control (m/s, rad/s)
    robot.stop()                        # immediate halt
    await robot.move_to(x, y)           # Nav2 path planning
    await robot.move_forward(1.0)       # drive straight 1m
    await robot.rotate(1.57)            # turn 90° CCW
    await robot.explore(timeout=60)     # autonomous frontier exploration

    # ─── AI Integration ───
    robot.execute_action(action_array)           # RL policy output → motors
    await robot.execute_instruction("go left")   # VLM reasoning → action
```
