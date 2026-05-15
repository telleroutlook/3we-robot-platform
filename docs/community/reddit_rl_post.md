---
Platform: Reddit
Subreddit: r/reinforcementlearning
---

# Gymnasium env for a real mobile robot — mock backend, no hardware needed to train

I built a Gymnasium environment that wraps a real robot platform (ESP32-S3 + Pi 5, mecanum wheels, LiDAR). The env works standalone with a mock backend — no ROS2, no GPU, just numpy.

```python
import gymnasium
import threewe.gym  # registers envs

env = gymnasium.make("3we/Navigation-v1")
obs, info = env.reset()

for _ in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()
```

**Observation space:** 360-dim LiDAR scan + 2D pose + velocity (configurable)

**Action space:** continuous `[vx, vy, omega]` (omnidirectional mecanum drive)

**What the mock backend simulates:**
- 2D kinematics with proper mecanum wheel model
- Collision detection against office-layout obstacles
- LiDAR raycasting (360 rays, configurable range)
- Configurable noise/domain randomization for Sim2Real

The goal is Sim2Real transfer — same code switches to `backend="gazebo"` or `backend="real"` with zero changes. The real hardware is <$500 to reproduce (open BOM + PCB in the repo).

**Try it:**

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python -c "import gymnasium; import threewe.gym; env = gymnasium.make('3we/Navigation-v1'); print(env.observation_space, env.action_space)"
```

Requires Python 3.10+ and numpy only.

**Questions for this community:**

1. Is the obs/action space what you'd expect for mobile robot navigation? What would you add?
2. Would you want a pre-trained PPO/SAC baseline included in the repo?
3. For Sim2Real: do you find domain randomization config (friction, sensor noise, latency) useful at the env level, or do you handle that in your training wrapper?

GitHub: https://github.com/telleroutlook/3we-robot-platform
