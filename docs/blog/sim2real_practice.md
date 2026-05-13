# Sim2Real: Same Python Code from Gazebo to Real Hardware

The number one pain point in robot learning research is the Sim2Real gap. You spend weeks training a policy in simulation, tune hyperparameters until the success rate looks good in MuJoCo or Gazebo, then deploy on hardware and watch the robot drive into a wall. The simulation physics do not match reality. The camera images look different. The motor response has latency your simulator did not model.

The `threewe` SDK was designed from day one to minimize this gap through a rigorous **Backend Abstraction Layer** and a quantified **Sim2Real Validation Protocol**. The core promise: change `backend="gazebo"` to `backend="real"`, and your code runs on hardware with no other modifications.

```python
from threewe import Robot

# Development and training
async with Robot(backend="gazebo") as robot:
    image = robot.get_camera_image()
    await robot.move_to(x=2.0, y=1.5)

# Deployment -- the ONLY change
async with Robot(backend="real") as robot:
    image = robot.get_camera_image()
    await robot.move_to(x=2.0, y=1.5)
```

This is not marketing. It is an engineering contract enforced by automated tests that run on every commit. Let us look at how it works and why it does not fall apart when you switch backends.

---

## The Backend Abstraction Layer

The `threewe` SDK uses a three-layer architecture:

```
┌──────────────────────────────────────────────────────────┐
│                    User Code (Python)                      │
│                                                           │
│    robot.get_image()                                      │
│    robot.get_lidar_scan()                                 │
│    robot.get_pose()                                       │
│    await robot.move_to(x, y)                             │
│    robot.set_velocity(vx, vy, omega)                      │
│    robot.get_observation()                                │
└───────────────────────────┬──────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────┐
│              Backend Abstraction Layer                     │
│                                                           │
│    BackendBase (abstract class)                           │
│    ├── connect() / disconnect()                           │
│    ├── get_camera_image() → (H, W, 3) uint8             │
│    ├── get_rgbd_image() → RGBDImage                      │
│    ├── get_lidar_scan() → LaserScan                      │
│    ├── get_pose() → Pose2D                               │
│    ├── get_velocity() → Velocity                         │
│    ├── get_imu() → IMUData                               │
│    ├── set_velocity(vx, vy, omega)                       │
│    ├── move_to(x, y, theta) → MoveResult                 │
│    ├── move_forward(distance) → MoveResult               │
│    └── rotate(angle) → MoveResult                        │
└───────────────────────────┬──────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐  ┌────────▼────────┐  ┌───────▼──────┐
│ GazeboBackend│  │ IsaacSimBackend │  │  RealBackend │
│              │  │                 │  │              │
│ Gazebo       │  │ Isaac Sim       │  │ ROS2 Jazzy   │
│ Harmonic     │  │ 4.x             │  │ + micro-ROS  │
│ + ros2_gz    │  │ + IsaacLab      │  │ + Pi5 + ESP32│
└──────────────┘  └─────────────────┘  └──────────────┘
```

Each backend implements the same abstract interface. The contract is not just "same method names" -- it specifies exact data formats, coordinate frames, and units.

---

## The Consistency Contract

This is what makes Sim2Real transfer work. Every backend must satisfy these invariants:

### Image Data

| Property | Specification |
|----------|---------------|
| Shape | `(H, W, 3)` where H=480, W=640 by default |
| Dtype | `uint8` |
| Channel order | BGR (OpenCV convention) |
| Color space | sRGB |
| Field of view | Matches physical camera (160-degree fisheye) |

### Depth Data

| Property | Specification |
|----------|---------------|
| Shape | `(H, W)` matching RGB |
| Dtype | `float32` |
| Units | Meters |
| Invalid pixels | `0.0` |
| Range | 0.1m to 10.0m |

### LiDAR Data

| Property | Specification |
|----------|---------------|
| Shape | `(N,)` where N=360 |
| Dtype | `float32` |
| Units | Meters |
| Angular sampling | Uniform, counterclockwise |
| Frame | Body-center, X-forward |
| Range | 0.1m to 12.0m |
| Invalid readings | `0.0` |

### Pose

| Property | Specification |
|----------|---------------|
| Frame | Map frame (right-hand: X forward, Y left, Z up) |
| Position units | Meters |
| Angle units | Radians |
| Angle convention | Counterclockwise positive from X-axis |
| Origin | First SLAM keyframe or spawn position |

### Velocity

| Property | Specification |
|----------|---------------|
| Frame | Body frame |
| Linear units | m/s |
| Angular units | rad/s |
| `vx` | Forward (positive = forward) |
| `vy` | Lateral (positive = left) |
| `omega` | Yaw rate (positive = counterclockwise) |

### Navigation Commands

| Property | Specification |
|----------|---------------|
| `move_to(x, y, theta)` | Navigate to map-frame pose using path planning |
| `move_forward(d)` | Drive straight in current heading by `d` meters |
| `rotate(a)` | Rotate in place by `a` radians (positive = CCW) |
| `set_velocity(vx, vy, omega)` | Direct velocity command (body frame) |
| Timeout | Motors stop if no command for 200ms |

This contract means that a policy trained on Gazebo images will receive images with identical format, resolution, color space, and field of view when running on hardware. LiDAR data has the same array shape and unit system. Velocity commands mean the same thing.

---

## Code Comparison: Identical Across Backends

Here is a concrete navigation task that works on all three backends without modification:

```python
import asyncio
import numpy as np
from threewe import Robot, Pose2D

async def patrol(backend: str = "gazebo"):
    """Patrol a rectangle, collecting observations at each corner."""

    waypoints = [
        Pose2D(x=2.0, y=0.0, theta=0.0),
        Pose2D(x=2.0, y=2.0, theta=1.57),
        Pose2D(x=0.0, y=2.0, theta=3.14),
        Pose2D(x=0.0, y=0.0, theta=-1.57),
    ]

    async with Robot(backend=backend, scene="office_v2") as robot:
        for i, wp in enumerate(waypoints):
            # Navigate to waypoint
            result = await robot.move_to(x=wp.x, y=wp.y, theta=wp.theta)
            print(f"Waypoint {i}: success={result.success}, "
                  f"distance={result.distance:.2f}m, "
                  f"duration={result.duration:.1f}s")

            # Collect observation
            obs = robot.get_observation(
                modalities=["image", "lidar", "pose", "velocity"]
            )
            print(f"  Pose: ({obs['pose'][0]:.2f}, {obs['pose'][1]:.2f}, "
                  f"{obs['pose'][2]:.2f})")
            print(f"  Min LiDAR range: {obs['lidar'].min():.2f}m")
            print(f"  Image shape: {obs['image'].shape}")

# Run in simulation
asyncio.run(patrol("gazebo"))

# Run on real hardware -- SAME code
asyncio.run(patrol("real"))
```

The output format is identical. The numbers will differ (real-world noise, different physics), but the data types, shapes, and semantics are guaranteed to match.

---

## Quantified Validation: Transfer Tests

We do not just claim Sim2Real works -- we measure it. The SDK includes a formal validation protocol with 5 standard transfer tests:

### Standard Transfer Tests

| Test | Metric | Pass Condition | Description |
|------|--------|---------------|-------------|
| `straight_walk_5m` | Endpoint error (m) | real < sim x 2.0 | Drive 5m forward, measure position error |
| `rotation_360` | Angle error (deg) | real < 1.0 (absolute) | Rotate 360 degrees, measure final heading error |
| `obstacle_avoidance_3` | Success rate | real > sim x 0.7 | Navigate past 3 obstacles |
| `pointnav_10m` | SPL | real > sim x 0.6 | Navigate 10m with optimal path ratio |
| `dynamic_obstacle` | Collision rate | real < sim x 1.5 | Navigate with moving obstacles |

### Running the Validation

```bash
# Sim-only validation (CI-friendly, no hardware needed)
threewe test sim2real --backend gazebo --scene office_v2

# Full sim2real comparison (requires hardware)
threewe sim2real report --backend gazebo --scene office_v2 --trials 5
```

Example output:

```
Running sim2real transfer tests (backend=gazebo, scene=office_v2)
==================================================
  Tests to run: ['straight_walk_5m', 'rotation_360', 'obstacle_avoidance_3',
                 'pointnav_10m', 'dynamic_obstacle']
  Mode: sim-only (validates thresholds against sim baseline)

  [PASS] straight_walk_5m: sim_value=0.082
  [PASS] rotation_360: sim_value=0.340
  [PASS] obstacle_avoidance_3: sim_value=0.867
  [PASS] pointnav_10m: sim_value=0.742
  [PASS] dynamic_obstacle: sim_value=0.067

Results: 5/5 passed
```

### Programmatic Validation

```python
import asyncio
from threewe.benchmark.sim2real import Sim2RealValidator

async def validate():
    validator = Sim2RealValidator()

    # Full comparison: sim vs real
    report = await validator.validate(
        sim_backend="gazebo",
        real_backend="real",
        num_trials=5,
    )

    print(f"Overall: {'PASS' if report.overall_passed else 'FAIL'}")
    print(f"Pass rate: {report.pass_rate:.0%}")

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.test_name}: "
              f"sim={result.sim_value:.3f}, "
              f"real={result.real_value:.3f}, "
              f"ratio={result.transfer_ratio:.2f}")

asyncio.run(validate())
```

---

## Why the Transfer Works

The backend abstraction alone does not guarantee transfer. Several engineering decisions make the gap manageable:

### 1. Matched Sensor Models

The Gazebo simulation uses sensor plugins configured to match real hardware specs:

- Camera: Same resolution (640x480), same lens model (160-degree fisheye with barrel distortion)
- LiDAR: Same angular resolution (1 degree), same noise model (Gaussian, sigma=0.01m)
- IMU: Same update rate (100Hz), same noise characteristics (BNO055 datasheet values)

### 2. Calibrated Motor Model

The simulated motors use response curves measured from the actual JGA25-370 motors:

- Velocity ramp-up time: 150ms (matched in simulation)
- Steady-state velocity accuracy: within 5%
- Encoder resolution: 11 counts/revolution (modeled in sim)

### 3. Consistent Navigation Stack

Both sim and real use the same Nav2 configuration:

- Same planner (NavFn)
- Same controller (DWB)
- Same costmap parameters
- Same recovery behaviors

This means path planning behavior is identical. The only difference is that real-world costmaps are noisier due to sensor noise.

### 4. Standardized Observation Format

The `robot.get_observation()` method returns a dict of numpy arrays with fixed dtypes and shapes. Whether data comes from Gazebo physics or real sensors, your model always receives:

```python
obs = robot.get_observation(modalities=["image", "lidar", "pose", "velocity"])
# obs["image"]:    (480, 640, 3) uint8
# obs["lidar"]:    (360,) float32
# obs["pose"]:     (3,) float32  [x, y, theta]
# obs["velocity"]: (3,) float32  [vx, vy, omega]
```

---

## Domain Randomization for Robust Transfer

For RL training, the SDK provides built-in domain randomization to make policies robust to the sim-real gap:

```python
from threewe.sim.domain_randomization import DomainRandomization

# Default randomization ranges
dr = DomainRandomization()

# Or load from config file
dr = DomainRandomization.from_yaml("configs/domain_randomization.yaml")

# Sample randomized parameters for one episode
params = dr.sample()
print(params)
# {
#     "mass_scale": 1.05,        # 0.9-1.1x robot mass
#     "friction_scale": 0.92,    # 0.8-1.2x floor friction
#     "motor_torque_noise": 0.02, # Gaussian noise on motor output
#     "gravity_noise": -0.003,   # Slight gravity variation
#     "lighting_intensity": 1.2,  # 0.5-1.5x scene lighting
#     "color_jitter": 0.05,      # Random color shift
#     "lidar_noise_scale": 1.3,   # 0.5-2.0x LiDAR noise
#     "imu_noise_scale": 0.8,     # 0.5-2.0x IMU noise
#     "camera_noise_scale": 1.1,  # 0.5-2.0x camera noise
#     "odometry_slip_scale": 1.4, # 0.5-2.0x wheel slip
# }
```

### Randomization Categories

**Physics Randomization:**

- Mass scaling (0.9x to 1.1x) -- accounts for payload variations
- Friction scaling (0.8x to 1.2x) -- different floor surfaces
- Motor torque noise -- actuator imprecision
- Gravity noise -- sensor mounting angle variations

**Visual Randomization:**

- Lighting intensity (0.5x to 1.5x) -- different times of day
- Texture randomization -- varied wall/floor appearances
- Shadow randomization -- different light positions
- Color jitter -- camera white balance variations

**Sensor Randomization:**

- LiDAR noise scaling -- accounts for real-world reflectivity variation
- IMU noise scaling -- temperature drift, vibration effects
- Camera noise scaling -- varying illumination quality
- Odometry slip scaling -- wheel-floor contact variation

### Using DR with Gymnasium Environments

```python
import gymnasium as gym
from threewe.sim.domain_randomization import DomainRandomization

dr = DomainRandomization(seed=42)
env = gym.make("threewe/NavigationEnv-v0")

for episode in range(1000):
    params = dr.sample()
    obs, info = env.reset(options={"domain_randomization": params})
    done = False
    while not done:
        action = policy(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
```

### Custom Randomization Config

Create a YAML file to customize ranges for your specific hardware and environment:

```yaml
# configs/domain_randomization.yaml
physics:
  mass_scale_range: [0.85, 1.15]
  friction_scale_range: [0.7, 1.3]
  motor_torque_noise_stddev: 0.08

visual:
  randomize_textures: true
  randomize_lighting: true
  lighting_intensity_range: [0.3, 1.8]
  color_jitter: 0.15

sensor:
  lidar_noise_scale_range: [0.3, 2.5]
  imu_noise_scale_range: [0.5, 2.0]
  camera_noise_scale_range: [0.5, 2.5]
  odometry_slip_scale_range: [0.5, 2.5]
```

---

## When to Use Each Backend

| Backend | Use Case | GPU Required | Speed |
|---------|----------|-------------|-------|
| **Gazebo** | Development, CI/CD, basic RL training | No | Real-time |
| **Isaac Sim** | Large-scale RL, domain randomization, photorealistic sim | Yes (RTX) | 10-100x |
| **Real** | Final validation, deployment, data collection | No | Real-time |

**Gazebo** is the default development backend. It runs headless on CPU, making it ideal for CI pipelines and quick iteration. Launch with:

```bash
threewe launch --backend gazebo --scene office_v2
```

**Isaac Sim** is the training backend for serious RL research. It supports parallel environments (64+), GPU-accelerated rendering, and tighter physics. Launch with:

```bash
threewe launch --backend isaac_sim --scene office_v2 --num-envs 64
```

**Real hardware** is the validation backend. Your code runs unchanged:

```python
async with Robot(backend="real") as robot:
    pass  # Same API as simulation
```

---

## A Complete Training-to-Deployment Pipeline

The typical research workflow has four phases:

1. **Develop in Gazebo** -- iterate on algorithms with fast feedback
2. **Train with DR** -- use domain randomization for robust policies
3. **Validate transfer** -- run `threewe test sim2real` to check pass/fail
4. **Deploy on hardware** -- change `backend="gazebo"` to `backend="real"`

```python
# Phase 2: Train with domain randomization
import gymnasium as gym
from threewe.sim.domain_randomization import DomainRandomization
from stable_baselines3 import PPO

dr = DomainRandomization()
env = gym.make("threewe/NavigationEnv-v0")
model = PPO("MultiInputPolicy", env, verbose=1)
model.learn(total_timesteps=1_000_000)
model.save("nav_policy_v1")
```

```python
# Phase 4: Deploy -- same observation/action interface
import asyncio
from stable_baselines3 import PPO
from threewe import Robot

model = PPO.load("nav_policy_v1")

async def deploy():
    async with Robot(backend="real") as robot:
        while True:
            obs = robot.get_observation(
                modalities=["image", "lidar", "pose", "velocity"]
            )
            action, _ = model.predict(obs, deterministic=True)
            robot.execute_action(action)

asyncio.run(deploy())
```

The transition from Phase 2 to Phase 4 requires changing exactly one string: `"gazebo"` to `"real"`.

---

## Handling the Remaining Gap

No abstraction layer eliminates the Sim2Real gap entirely. Here are the remaining sources of error and how the SDK addresses them:

| Source | Problem | Mitigation |
|--------|---------|------------|
| Sensor noise | Real sensors are noisier than modeled | Configurable `SensorNoiseModel` tuned to hardware datasheets |
| Motor latency | Real motors have acceleration limits and delays | First-order lag filter in Gazebo matched to JGA25-370 curves |
| Floor variation | Different surfaces change friction/odometry | Domain randomization with wide friction ranges (0.7-1.3x) |
| Lighting | Real lighting varies dramatically | Visual DR (0.3-1.8x intensity) during training |

The SDK provides a `SensorNoiseModel` you can tune to your specific hardware:

```python
from threewe.sim.noise import SensorNoiseModel

noise = SensorNoiseModel(
    lidar_gaussian_stddev=0.02,    # 2cm noise on LiDAR
    imu_accel_stddev=0.01,         # m/s^2
    imu_gyro_stddev=0.005,         # rad/s
    camera_gaussian_stddev=5.0,    # pixel intensity noise
    odometry_slip_factor=0.05,     # 5% wheel slip
)
```

---

## Continuous Integration for Sim2Real

The 3we platform runs Sim2Real validation on every pull request:

```yaml
# .github/workflows/sim2real-validation.yml
name: Sim2Real Validation
on: [pull_request]

jobs:
  transfer-tests:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pip install threewe[sim]
      - name: Run transfer tests
        run: threewe test sim2real --backend gazebo
      - name: Generate report
        run: threewe sim2real report --backend gazebo --trials 3
```

If the transfer tests regress (e.g., someone changes the motor model without updating the simulator), CI fails. This prevents accidental degradation of Sim2Real consistency.

---

## Quick Start

### 1. Install

```bash
# Simulation only (no hardware needed)
pip install threewe[sim]

# With AI integration
pip install threewe[ai]

# Full installation
pip install threewe[sim,ai]
```

### 2. Launch Simulation

```bash
threewe launch --backend gazebo --scene office_v2
```

### 3. Write Your Code

```python
import asyncio
from threewe import Robot

async def main():
    async with Robot(backend="gazebo") as robot:
        # This exact code will work on real hardware
        obs = robot.get_observation()
        await robot.move_to(x=3.0, y=2.0)
        await robot.move_forward(1.0)
        await robot.rotate(1.57)

asyncio.run(main())
```

### 4. Validate Transfer

```bash
threewe test sim2real --backend gazebo
```

### 5. Deploy on Hardware

Change `backend="gazebo"` to `backend="real"`. Run the same script.

---

## Summary

The Sim2Real gap is not eliminated -- that requires solving physics and rendering at infinite fidelity. But it is managed, measured, and minimized through:

- **BackendBase** abstract class enforcing identical API contracts across sim and real
- **Consistency contract** specifying exact numpy dtypes, shapes, coordinate frames, and units
- **Domain randomization** for physics, visuals, and sensor noise
- **Automated validation** via 5-test transfer protocol with quantified pass/fail criteria
- **CI enforcement** where transfer tests run on every PR to prevent regression

For indoor navigation tasks, this approach enables reliable transfer from Gazebo training to real hardware deployment.

---

## Links

- GitHub: [https://github.com/3we-org/3we-robot-platform](https://github.com/3we-org/3we-robot-platform)
- Transfer test definitions: `sdk/threewe/src/threewe/benchmark/sim2real.py`
- Backend interface: `sdk/threewe/src/threewe/backends/__init__.py`
- Domain randomization: `sdk/threewe/src/threewe/sim/domain_randomization.py`
- PyPI: [https://pypi.org/project/threewe](https://pypi.org/project/threewe)

---

Published by the 3we team
