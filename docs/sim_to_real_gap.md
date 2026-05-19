# Sim-to-Real Gap: What 3we Does and Doesn't Solve

This page is here because we want to be honest about what our backend abstraction actually delivers, and where you, the user, will still need to do work.

## TL;DR

- **The Python API is the same** across `mock`, `gazebo`, `isaac_sim`, and `real` backends. You don't rewrite glue code when you switch.
- **Sim-to-real transfer is not the same** as API consistency. Different tasks need different simulation fidelity, and most non-trivial policies need some form of task-specific tuning, domain randomization, or fine-tuning on real data before they transfer.
- **We provide presets** for common research scenarios. We do not provide a magic "train in sim, deploy on real" pipeline that works for arbitrary tasks. Anyone who tells you their platform does, for arbitrary tasks, is probably overselling.

If you came here expecting "zero-effort Sim2Real", we owe you an apology — earlier versions of our README oversold this. We've corrected the framing. The honest pitch is below.

## What Actually Stays the Same Across Backends

When you change `backend="gazebo"` to `backend="real"`:

- The `Robot` class, its methods, and their signatures are identical.
- Sensor data shapes and types match (e.g. `get_lidar_scan().ranges` is `(360,)` float32 in both).
- Actions and result types match (`move_to`, `MoveResult`, `Pose`).
- Gymnasium environment IDs and observation/action spaces match.

What this gets you in practice: you don't rewrite your training loop, evaluation script, or policy code. ROS2 launch-file workflows already give you a similar property — what we add on top is a Python class API and a zero-dependency `mock` backend, which are useful if you'd rather not write nodes and launch files just to iterate on an algorithm.

## What Does Not Stay the Same

The simulation underneath the API is not a perfect physical model of your real robot. Specifically:

| Aspect | Sim default | Real-world reality |
|---|---|---|
| **IMU noise** | Gaussian with fixed bias | Bias drifts with temperature, humidity, vibration; non-Gaussian higher-order effects |
| **Wheel/motor dynamics** | Idealized friction, no backlash | Static/kinetic friction transitions, gear backlash, motor cogging, voltage sag under load |
| **LiDAR** | Clean point cloud, no specular failures | Reflective/transparent surfaces drop out, sun saturation, dust |
| **RGB camera** | Rendered, fixed exposure | Auto-exposure, motion blur, lens distortion, white balance drift |
| **Battery / power** | Constant voltage | Voltage sag affects motor torque, sensor noise floors, control loop timing |
| **Wireless** | Zero latency, no loss | Variable latency, packet loss, congestion |

For a thoughtful expansion of why a "complete" simulation isn't realistic — even with infinite engineering budget — see [@peci1's comment on this thread](https://discourse.openrobotics.org/) (if you're reading this in context, you know the one).

## What Transfers Reasonably Well, in Practice

Based on what we've tested and what published Sim2Real literature converges on:

- **Point-to-point navigation** in a structured environment, at conservative speeds, using LiDAR + odometry, with classical Nav2 planning. Often transfers without retraining.
- **Coverage / exploration policies** trained with domain-randomized LiDAR. Usually transfers with mild degradation.
- **High-level decision policies** that consume already-processed inputs (a detected target's relative position, a discrete map) rather than raw sensor pixels.

## What Usually Needs Task-Specific Work

- **End-to-end RL from raw RGB camera to motor commands.** Without domain randomization (lighting, textures, camera intrinsics) and ideally fine-tuning on real frames, transfer is unreliable.
- **Anything depending on accurate IMU at >100 Hz** (legged locomotion-style proprioception, precise dead reckoning). Sim defaults are too clean.
- **Manipulation with contact dynamics.** Friction and compliance models in Gazebo and Isaac Sim are decent but not your robot's specific gripper.
- **Behaviors near the limits of the platform** (high-speed turns, near-empty battery, marginal lighting). Sim doesn't model these failure modes faithfully.

For tasks in this category, plan to do at least one of:

1. **Pick a different sensor fidelity per task.** Train a clustering algorithm on a segmentation camera, not a rendered RGB camera. Train a walking policy on randomized IMU noise without rendering at all. Don't pay for fidelity you don't need.
2. **Apply domain randomization** during sim training (we expose this via `Robot(... , randomization=...)` and per-Gym-env configs).
3. **Fine-tune on real data** collected with `threewe.data.record_trajectory()` or a teleop session.
4. **Validate in stages**: mock → gazebo → real, narrowing the gap step by step rather than expecting a one-shot transfer.

## How Our Backends Differ

| Backend | Use it for | Don't use it for |
|---|---|---|
| `mock` | Algorithm prototyping, unit tests, CI, teaching the API | Anything physics-dependent (no contact, no real dynamics) |
| `gazebo` | Navigation, exploration, mid-fidelity Sim2Real validation | High-frequency control, GPU-parallel RL training (slow), accurate visual rendering |
| `isaac_sim` | GPU-parallel RL training, high-fidelity rendering, large-scale domain randomization | Quick iteration on a laptop without an NVIDIA GPU |
| `real` | Final validation, data collection, deployment | Burning CPU cycles you could be burning in sim instead |

## Provided Sim Presets

For common scenarios we ship configurations that have at least been sanity-checked. These are starting points, not guarantees:

- `3we/Navigation-v1` — Gazebo + Nav2, LiDAR-based, conservative speeds. Closest to "works out of the box on real hardware."
- `3we/Exploration-v1` — Domain-randomized LiDAR. Transfers with degradation.
- `3we/ObjectNav-v1` — Requires either segmentation-camera training or RGB + DR + real fine-tune. Plan accordingly.
- `3we/VLN-v1` — VLM-driven; the bottleneck is the VLM, not the sim-real gap. Sim is mostly there for cheap iteration.

If your task isn't on this list, expect to spend time configuring sensor fidelity and tuning a sim config that matches what your policy actually depends on.

## Why We Wrote This Page

A community member pointed out that selling "Sim2Real with zero code changes" as a feature is misleading: the single-string backend switch is real, but the *transfer* it implies is not free. They're right, and we'd rather have honest users than disappointed ones. If we can save you a week of debugging by being upfront about what doesn't transfer, that's a better deal than a clean marketing line.

If you find a case where our presets work or don't work for your task, please open an issue or PR — the more concrete the gap analysis, the more useful this page becomes.
