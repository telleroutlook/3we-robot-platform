# Sim2Real Quick Start Guide

> Train a navigation policy in simulation. Deploy on real hardware. Zero code changes.

## Prerequisites

| Requirement | For Simulation | For Real Hardware |
|-------------|----------------|-------------------|
| Python 3.10+ | Required | Required |
| `threewe[sim]` | Required | Required |
| `stable-baselines3` | Required | Required |
| ROS2 Jazzy | Not needed | Required |
| Physical robot | Not needed | Required |

## Installation

```bash
pip install "threewe[sim]" stable-baselines3
```

## Step 1: Train in Simulation

```python
from threewe import Robot
import threewe.gym  # registers 3we/* Gymnasium environments

import gymnasium
from stable_baselines3 import PPO

# Create environment — runs entirely in simulation
env = gymnasium.make("3we/Navigation-v1", max_steps=500)

# Train PPO for 50k steps (~2 minutes)
model = PPO("MultiInputPolicy", env, verbose=1)
model.fit(total_timesteps=50_000)
model.save("nav_ppo")
```

## Step 2: Evaluate in Simulation

```python
import asyncio
from threewe import Robot

async def evaluate(backend="gazebo"):
    async with Robot(backend=backend) as robot:
        pose = robot.get_pose()
        print(f"Start: ({pose.x:.2f}, {pose.y:.2f})")

        result = await robot.move_to(x=2.0, y=1.5)
        print(f"Reached: ({result.final_pose.x:.2f}, {result.final_pose.y:.2f})")
        print(f"Success: {result.success}")

asyncio.run(evaluate("gazebo"))
```

## Step 3: Deploy on Real Hardware

```python
# THE ONLY CHANGE: backend="gazebo" → backend="real"
asyncio.run(evaluate("real"))
```

That's it. No retraining. No fine-tuning. No code modification.

## One-Click Script

For the complete experience (train + evaluate + compare):

```bash
# Simulation only
./examples/sim2real_demo/reproduce.sh

# Simulation + real hardware comparison
./examples/sim2real_demo/reproduce.sh --real
```

## Understanding the Results

The script outputs a comparison table:

```
  Sim path length:   2.634m (52 steps)
  Real path length:  2.891m (58 steps)
  Endpoint error:    0.043m
  Transfer ratio:    1.10
```

| Metric | Good | Acceptable | Investigate |
|--------|------|------------|-------------|
| Endpoint error | < 0.1m | < 0.3m | > 0.3m |
| Transfer ratio | 0.8–1.2 | 0.6–1.5 | < 0.6 or > 1.5 |
| Path length ratio | ~1.0 | 0.7–1.3 | varies widely |

A transfer ratio of 1.0 means simulation and real-world behavior are identical. Values near 1.0 indicate strong Sim2Real transfer.

## Advanced: Domain Randomization

To improve transfer robustness, enable domain randomization during training:

```python
from threewe.sim.domain_randomization import DomainRandomization

dr = DomainRandomization()
# Each episode samples different physics/sensor parameters
params = dr.sample()
# params includes: mass_scale, friction_scale, lidar_noise_scale, etc.
```

## Advanced: Quantitative Validation

Use the built-in Sim2Real benchmark for rigorous transfer testing:

```python
from threewe.benchmark.sim2real import STANDARD_TRANSFER_TESTS, evaluate_transfer

# 5 standard transfer tests with pass/fail criteria
for test in STANDARD_TRANSFER_TESTS:
    print(f"{test.name}: {test.metric} (threshold: {test.threshold})")
```

Run the full validation suite:

```bash
python examples/sim2real_validation.py --backend gazebo --trials 10
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Robot doesn't move | `robot_bringup` not running | `ros2 launch robot_bringup robot.launch.py` |
| Large endpoint error | Wheel slip on surface | Enable domain randomization during training |
| Timeout on real hardware | Nav2 not configured | Check `ros2 topic list` for `/cmd_vel` |
| Import error | Missing dependencies | `pip install threewe[sim] stable-baselines3` |

## Video Recording Tips

For creating a side-by-side demonstration video:

1. Run simulation in one terminal, record Gazebo window
2. Run real hardware, record robot with fixed camera
3. Overlay terminal output showing the code (highlight `backend=` parameter)
4. Use OBS Studio with side-by-side scene layout
5. Add LiDAR point cloud visualization via RViz2 as picture-in-picture
