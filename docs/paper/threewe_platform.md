# 3we: An Open Platform for Sim-to-Real Embodied AI Research

**Authors:** 3we Contributors

**Abstract.** Embodied AI research requires tight integration between simulation environments and physical robots, yet current platforms impose significant barriers: high hardware costs ($5,000+), complex middleware stacks, and fundamental gaps between simulated and real-world behavior. We present 3we, an open-source robot platform that addresses these challenges through three contributions: (1) an AI-First Python API that eliminates direct ROS2 interaction, reducing typical task implementations from 60+ lines to under 5; (2) reproducible open hardware under CERN-OHL-P v2 with a bill of materials under $300; and (3) a Backend Abstraction Layer that enforces identical data formats and coordinate frames across Gazebo, Isaac Sim, and physical hardware backends. The platform provides native Gymnasium environments for reinforcement learning, built-in support for Vision-Language-Action (VLA) model deployment, and a trajectory recording pipeline compatible with the LeRobot ecosystem. Three standardized benchmark tasks (PointNav, ObjectNav, Exploration) with a public leaderboard enable reproducible evaluation. By dramatically lowering the cost and complexity of sim-to-real research, 3we aims to democratize embodied AI development for the broader research community.

---

## 1. Introduction

Embodied AI stands at an inflection point. The emergence of Vision-Language Models (VLMs) and Vision-Language-Action (VLA) models has demonstrated that foundation model capabilities can extend beyond text and images into physical action spaces [1, 2]. However, translating these advances into real-world robotic systems remains prohibitively difficult for most research groups.

Three primary barriers impede progress. First, research-grade mobile robot platforms typically cost $5,000-$25,000, restricting experimentation to well-funded laboratories. Second, the standard middleware stack (ROS2 + Nav2 + custom drivers) presents a steep learning curve orthogonal to AI research itself, requiring months of systems engineering before any learning experiment can begin. Third, the sim-to-real transfer gap remains poorly standardized: policies trained in simulation frequently fail on hardware due to undocumented differences in observation spaces, action semantics, and timing behavior between simulators and physical systems.

We introduce 3we (pronounced "three-we"), an open platform designed to eliminate these barriers. Our contributions are:

- An **AI-First Python API** (`threewe` package) that abstracts ROS2 entirely, exposing perception, navigation, and AI model integration through a minimal async interface.
- **Open hardware** under the CERN Open Hardware Licence (Permissive v2), with a complete bill of materials costing approximately $300 and requiring no custom PCB fabrication.
- A **Backend Abstraction Layer** with a formally specified consistency contract, ensuring that code written for simulation executes identically on physical hardware with zero modification.
- **Standardized benchmarks** with public leaderboard infrastructure for reproducible evaluation of navigation and exploration policies.

The remainder of this paper is organized as follows: Section 2 discusses related work; Section 3 presents the system architecture; Section 4 details the Python API design; Section 5 describes the sim-to-real consistency mechanism; Section 6 introduces the benchmark suite; Section 7 covers the hardware design; Section 8 discusses the data ecosystem; and Section 9 concludes with future directions.

---

## 2. Related Work

**TurtleBot Series.** The TurtleBot family [3] has served as the de facto educational mobile robot platform for over a decade. However, TurtleBot3 is limited to differential drive kinematics, costs approximately $600-$1,500, ships without AI acceleration hardware, and requires direct ROS2 programming for all tasks. The 3we platform provides omnidirectional motion via mecanum wheels, 13 TOPS of edge AI compute, and a Python API that hides ROS2 complexity.

**NVIDIA Isaac Sim.** Isaac Sim [4] provides high-fidelity physics simulation with GPU-accelerated parallelism for reinforcement learning. While powerful for training, it is proprietary, requires substantial GPU resources (RTX 3070+), and provides no direct path to affordable physical hardware. 3we treats Isaac Sim as one of several interchangeable backends rather than a standalone platform.

**HuggingFace LeRobot.** LeRobot [5] establishes an excellent data ecosystem for robot learning, providing standardized dataset formats (Parquet + MP4) and pre-trained VLA model checkpoints. However, its mobile robot support is limited, with primary focus on manipulation tasks. 3we provides direct LeRobot format compatibility through its trajectory recorder while adding navigation-specific capabilities (SLAM, Nav2, exploration).

**Habitat and AI2-THOR.** These simulation platforms [6, 7] enable large-scale embodied AI experimentation in photorealistic environments but provide no deployment path to physical robots. Policies trained in these environments require separate engineering effort for real-world transfer. 3we bridges this gap through its consistency contract.

**Genesis World.** Genesis [8] offers generative simulation with differentiable physics, representing a promising future direction. As the ecosystem matures, 3we's modular backend architecture allows integration as an additional simulation backend.

---

## 3. System Architecture

The 3we platform employs a three-layer architecture separating user-facing AI research code from middleware and hardware concerns:

```
+----------------------------------------------------------+
|  Layer 3: User Application                               |
|  ┌─────────────────────────────────────────────────────┐ |
|  │  from threewe import Robot                          │ |
|  │  robot.get_camera_image()  /  robot.move_to(x,y)   │ |
|  │  robot.execute_instruction("find the red cup")      │ |
|  └─────────────────────────────────────────────────────┘ |
+----------------------------------------------------------+
|  Layer 2: Backend Abstraction Layer                       |
|  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  |
|  │  Gazebo  │  │  Isaac Sim   │  │  Real Hardware   │  |
|  │ (CPU,CI) │  │ (GPU,Train)  │  │ (Pi5+ESP32+ROS) │  |
|  └──────────┘  └──────────────┘  └──────────────────┘  |
+----------------------------------------------------------+
|  Layer 1: Physical / Simulated Substrate                  |
|  ┌──────────────────────────────────────────────────────┐|
|  │  ROS2 Jazzy · Nav2 · micro-ROS · Gazebo Harmonic    │|
|  │  ESP32-S3 · Mecanum Drive · Hailo-8L · SLAM Toolbox │|
|  └──────────────────────────────────────────────────────┘|
+----------------------------------------------------------+
```

**Hardware Platform.** The physical robot comprises a Raspberry Pi 5 (8GB) as the main compute unit, a Hailo-8L M.2 accelerator providing 13 TOPS of neural network inference, an ESP32-S3 microcontroller running micro-ROS for real-time motor control, four mecanum wheels enabling omnidirectional motion, a 2D LiDAR for SLAM, and a USB fisheye camera. Total weight is approximately 2.5 kg with a maximum linear velocity of 1.2 m/s.

**Software Stack.** The runtime environment uses ROS2 Jazzy with Nav2 for path planning, SLAM Toolbox for map building, and micro-ROS on the ESP32-S3 for 50 Hz motor control loops. Critically, none of these components are exposed to the end user; the `threewe` Python package mediates all interaction through the Backend Abstraction Layer.

---

## 4. AI-First Python API

### 4.1 Design Philosophy

The `threewe` package (v0.2.0) is designed for AI researchers who should never need to learn ROS2 concepts (nodes, topics, services, actions) to conduct embodied AI experiments. The API provides:

- Synchronous sensor access (images, LiDAR, pose, IMU)
- Async navigation primitives (`move_to`, `explore`, `follow_path`)
- Native VLM/VLA integration (`execute_instruction`, `VLARunner`)
- Gymnasium-compatible environments for RL training

### 4.2 Code Comparison

A typical navigation task illustrates the complexity reduction:

**Traditional ROS2 (60+ lines):**
```python
import rclpy
from rclpy.node import Node
from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
# ... 60+ lines of node setup, spin, callback management
```

**3we API (5 lines):**
```python
from threewe import Robot
async with Robot(backend="gazebo") as robot:
    image = robot.get_camera_image()       # (480, 640, 3) uint8
    result = await robot.move_to(x=2.0, y=1.0)
    print(f"Success: {result.success}")
```

### 4.3 Gymnasium Integration

The platform registers standard Gymnasium environments for seamless integration with any RL library (Stable-Baselines3, CleanRL, RLlib):

```python
import gymnasium
env = gymnasium.make("3we/Navigation-v1", backend="gazebo")
obs, info = env.reset()
obs, reward, terminated, truncated, info = env.step(action)
```

Three environments of increasing difficulty are provided: `Navigation-v1` (point-to-point), `Exploration-v1` (frontier-based coverage), and `ObjectNav-v1` (semantic goal navigation).

### 4.4 VLM/VLA Native Support

For foundation model research, the API provides first-class integration:

```python
# VLM-driven navigation (one line)
result = await robot.execute_instruction("find the red object")

# VLA model deployment
from threewe.ai import VLARunner
runner = VLARunner.from_pretrained("lerobot/act_3we_nav")
action = runner.predict(image, instruction="go to the kitchen")
```

---

## 5. Sim2Real Consistency

### 5.1 Consistency Contract

The Backend Abstraction Layer (`BackendBase`) enforces a formal contract across all backends:

| Data Type | Format | Convention |
|-----------|--------|------------|
| RGB Image | `(H, W, 3)` uint8 | BGR color order |
| Depth | `(H, W)` float32 | Meters, invalid = 0.0 |
| LiDAR | `(N,)` float32 | Meters, uniform angular sampling |
| Pose | `(x, y, theta)` | Right-hand, X-forward, Y-left, radians |
| Velocity | `(vx, vy, omega)` | m/s linear, rad/s angular |

This contract is verified at the interface level: any backend implementation that violates these specifications fails type checking and runtime assertions.

### 5.2 Domain Randomization

The simulation backends support configurable domain randomization to improve transfer robustness:

- **Physics:** mass scaling (0.9-1.1x), friction variation (0.8-1.2x), motor torque noise
- **Visual:** texture randomization, lighting intensity variation (0.5-1.5x), color jitter
- **Sensor:** LiDAR/IMU/camera noise scaling, odometry slip simulation

### 5.3 Transfer Validation Protocol

To quantify sim-to-real gap, the platform provides a standardized protocol:

1. Train policy in simulation with domain randomization
2. Evaluate on 50 episodes across 3 simulation seeds
3. Deploy identical code on physical hardware
4. Evaluate on 10 matched real-world episodes
5. Report transfer ratio: `SR_real / SR_sim`

---

## 6. Benchmarks

### 6.1 Task Definitions

Three standardized benchmark tasks are provided:

| Task | Metric | Success Condition | Scenes |
|------|--------|-------------------|--------|
| PointNav | SPL, Success Rate | Within 0.5m of goal | 7 environments |
| ObjectNav | SPL, Success Rate | Object detected and approached | 4 environments |
| Exploration | Coverage (%) | Percentage of navigable area mapped | 3 environments |

### 6.2 Metrics

We adopt standard embodied AI metrics:

- **Success Rate (SR):** Fraction of episodes reaching the goal condition.
- **SPL (Success weighted by Path Length):** SPL = (1/N) * sum(S_i * L_i / max(P_i, L_i)), penalizing inefficient paths [9].
- **Coverage:** Ratio of explored cells to total navigable cells in the occupancy grid.

### 6.3 Reproducibility

Each benchmark run records: random seed, domain randomization config, hardware profile, backend version, and episode-level trajectories. The public leaderboard accepts submissions via the CLI:

```bash
threewe benchmark run pointnav --episodes 50 --submit
```

---

## 7. Hardware Design

### 7.1 Open Hardware License

All hardware designs (schematics, PCB layouts, mechanical drawings) are released under the CERN Open Hardware Licence - Permissive v2 (CERN-OHL-P), allowing unrestricted commercial and academic use.

### 7.2 Bill of Materials

The standard configuration costs approximately $300 (CNY equivalent):

| Component | Specification | Cost (approx.) |
|-----------|--------------|----------------|
| Compute | Raspberry Pi 5 8GB | $82 |
| AI Accelerator | Hailo-8L M.2 (13 TOPS) | $80 |
| AI HAT+ | M.2 carrier for Pi 5 | $27 |
| MCU | ESP32-S3 (micro-ROS) | $5 |
| Camera | USB Fisheye 170deg 1080P | $12 |
| Motors (x4) | N20 Gear Motor 1:50 w/ encoder | $7 each |
| Wheels (x4) | 65mm Mecanum (PU rollers) | $5 each |
| Battery | 2S 18650 packs (x2) | $10 each |
| Structure + misc | Mounts, cables, hub, cooling | $25 |
| **Total** | | **~$300** |

### 7.3 Key Specifications

| Parameter | Value |
|-----------|-------|
| Dimensions | ~250 x 220 x 150 mm |
| Weight | ~2.5 kg |
| Drive type | 4-wheel mecanum (omnidirectional) |
| Max velocity | 1.2 m/s linear, 3.0 rad/s angular |
| AI compute | 13 TOPS (Hailo-8L) + Pi 5 CPU |
| SLAM | 2D LiDAR, SLAM Toolbox |
| Control loop | 50 Hz (ESP32 micro-ROS) |
| Communication | Wi-Fi (DTLS encrypted) |
| Battery life | ~2 hours continuous operation |

---

## 8. Data Ecosystem

### 8.1 Trajectory Recording

The `TrajectoryRecorder` class captures observation-action pairs during teleoperation or autonomous execution at the full control rate:

```python
from threewe.data import TrajectoryRecorder
recorder = TrajectoryRecorder(robot)
recorder.start_episode()
# ... robot operates ...
recorder.end_episode()
recorder.export("dataset_v1", format="lerobot")
```

Each timestep records: RGB image, pose (x, y, theta), velocity, commanded action, and optionally LiDAR and depth data.

### 8.2 LeRobot Format Compatibility

Exported datasets follow the LeRobot specification (Parquet metadata + MP4 video streams), enabling direct use with the LeRobot training pipeline and HuggingFace Hub distribution:

```bash
threewe data push my_dataset --repo-id user/3we-office-nav
```

### 8.3 VLA Deployment Pipeline

The complete pipeline from data collection to model deployment:

1. Collect demonstrations via teleoperation or VLM-guided execution
2. Export to LeRobot format and upload to HuggingFace Hub
3. Train VLA model using LeRobot training scripts
4. Deploy trained model on-device via `VLARunner.from_pretrained()`
5. Evaluate on standardized benchmarks

The Hailo-8L accelerator enables on-device VLA inference at approximately 10 Hz for typical model architectures (ACT, Diffusion Policy).

---

## 9. Conclusion and Future Work

We have presented 3we, an open platform that addresses the three primary barriers to embodied AI research: cost, complexity, and sim-to-real consistency. The AI-First Python API reduces implementation effort by an order of magnitude compared to direct ROS2 programming. The open hardware design enables reproduction at approximately $300. The Backend Abstraction Layer with its formal consistency contract ensures that code developed in simulation transfers to physical hardware without modification.

**Future directions** include: (1) Isaac Sim backend completion for GPU-parallel RL training with thousands of concurrent environments; (2) a Hardware Abstraction Layer (HAL) enabling the `threewe` API to drive third-party robot platforms (TurtleBot, Unitree, custom hardware); (3) multi-robot fleet coordination for cooperative exploration and task allocation; and (4) integration with emerging generative simulation platforms (Genesis) for automatic environment generation.

We invite the robotics and AI research community to adopt, reproduce, and extend the platform. All source code, hardware designs, and documentation are available at https://github.com/3we-org/3we-robot-platform under permissive open-source licenses.

---

## References

[1] A. Brohan et al., "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control," in *Proc. CoRL*, 2023.

[2] OpenAI, "GPT-4o: Multimodal Reasoning Across Text, Vision, and Audio," OpenAI Technical Report, 2024.

[3] R. Amsters and P. Slaets, "TurtleBot3: A Mobile Robot Platform for Education and Research," in *IROS Workshop on Open Source Robotics*, 2020.

[4] NVIDIA, "Isaac Sim: Scalable Robotics Simulation for Synthetic Data Generation and Robot Learning," NVIDIA Developer Documentation, 2023.

[5] C. Cadene et al., "LeRobot: State-of-the-art Machine Learning for Real-World Robotics," HuggingFace, 2024.

[6] M. Savva et al., "Habitat: A Platform for Embodied AI Research," in *Proc. ICCV*, 2019.

[7] E. Kolve et al., "AI2-THOR: An Interactive 3D Environment for Visual AI," arXiv:1712.05474, 2017.

[8] Genesis Contributors, "Genesis: A Generative and Universal Physics Engine for Robotics and Beyond," arXiv:2409.18051, 2024.

[9] P. Anderson et al., "On Evaluation of Embodied Navigation Agents," arXiv:1807.06757, 2018.

[10] S. Macenski et al., "The Marathon 2: A Navigation System," in *Proc. IROS*, 2020. (Nav2)

[11] M. Towers et al., "Gymnasium: A Standard Interface for Reinforcement Learning Environments," arXiv:2407.17032, 2024.

[12] J. Schulman et al., "Proximal Policy Optimization Algorithms," arXiv:1707.06347, 2017.

---

## Citation

If you use the 3we platform in your research, please cite:

```bibtex
@software{threewe2026,
  title={3we: An Open Platform for Sim-to-Real Embodied AI Research},
  author={{3we Contributors}},
  year={2026},
  url={https://github.com/3we-org/3we-robot-platform},
}
```
