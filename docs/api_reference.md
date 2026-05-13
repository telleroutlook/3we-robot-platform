# threewe API Reference

Auto-generated API documentation for the `threewe` Python package.

**Version**: 0.2.0

## Table of Contents

- [Robot](#robot)
- [Types](#types)
- [Backends](#backends)
- [Gymnasium Environments](#gymnasium-environments)
- [AI Module](#ai-module)
- [Data Module](#data-module)
- [Benchmark](#benchmark)
- [CLI](#cli)
- [Configuration](#configuration)
- [Exceptions](#exceptions)

## Robot

> Robot — the main user-facing entry point.

### `Robot`

AI-First interface for controlling a 3we robot.

Supports three backends:
- "gazebo": Gazebo Harmonic simulation (CPU, CI, quick iteration)
- "isaac_sim": NVIDIA Isaac Sim (GPU RL training, domain randomization)
- "real": Physical robot via ROS2 (Pi 5 + ESP32-S3 + micro-ROS)

All backends return data in identical formats — code written for one backend
works on all others without modification.

```python
Robot(self, backend: 'str' = 'gazebo', config: 'str | RobotConfig' = 'standard_v2', *, hardware: 'str' = '3we_standard_v2', scene: 'str' = 'office_v2', auto_connect: 'bool' = True) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `backend_name` *(property)*
- `config` *(property)*
- `connect(self) -> 'None'`
  Connect to the robot or simulator.
- `disconnect(self) -> 'None'`
  Disconnect from the robot or simulator.
- `execute_action(self, action: 'np.ndarray') -> 'None'`
  Execute a policy network output action vector.
- `execute_instruction(self, instruction: 'str') -> 'ExecutionResult'`
  Execute a natural language instruction using VLM reasoning.
- `explore(self, timeout: 'float' = 60.0) -> 'ExploreResult'`
  Autonomously explore unknown areas until map is complete or timeout.
- `follow_path(self, waypoints: 'list[Pose2D]') -> 'MoveResult'`
  Follow a sequence of waypoints in order.
- `get_battery_state(self) -> 'BatteryState'`
  Get battery voltage, percentage, and charging state.
- `get_camera_image(self) -> 'np.ndarray'`
  Get RGB image. Returns (H, W, 3) uint8 numpy array.
- `get_image(self) -> 'np.ndarray'`
  Get RGB image. Returns (H, W, 3) uint8 numpy array.
- `get_imu(self) -> 'IMUData'`
  Get IMU sensor data.
- `get_lidar_scan(self) -> 'LaserScan'`
  Get 2D laser scan.
- `get_map(self) -> 'OccupancyGrid'`
  Get current SLAM occupancy grid map.
- `get_observation(self, modalities: 'list[str] | None' = None) -> 'dict[str, np.ndarray]'`
  Get standardized observation dict for VLA/RL model ingestion.
- `get_pose(self) -> 'Pose2D'`
  Get robot pose in the map frame.
- `get_rgbd_image(self) -> 'RGBDImage'`
  Get RGB-D image with depth in meters.
- `get_velocity(self) -> 'Velocity'`
  Get current body-frame velocity.
- `hardware` *(property)*
- `is_connected` *(property)*
- `move_forward(self, distance: 'float') -> 'MoveResult'`
  Drive straight forward by the specified distance (meters).
- `move_to(self, x: 'float', y: 'float', theta: 'float | None' = None, timeout: 'float' = 60.0) -> 'MoveResult'`
  Navigate to target pose using Nav2 path planning.
- `rotate(self, angle: 'float') -> 'MoveResult'`
  Rotate in place by the specified angle (radians, positive=CCW).
- `set_velocity(self, vx: 'float', vy: 'float', omega: 'float') -> 'None'`
  Command body velocity. Must be called continuously or timeout stops motors.
- `stop(self) -> 'None'`
  Immediately stop all motion.


## Types

> Core data types for the threewe API.

### `BatteryState`

Battery status.

```python
BatteryState(self, voltage: 'float' = 0.0, percentage: 'float' = 0.0, is_charging: 'bool' = False) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `CameraIntrinsics`

Pinhole camera intrinsic parameters.

```python
CameraIntrinsics(self, fx: 'float' = 0.0, fy: 'float' = 0.0, cx: 'float' = 0.0, cy: 'float' = 0.0, width: 'int' = 640, height: 'int' = 480) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `ExecutionResult`

Result of a VLM instruction execution.

```python
ExecutionResult(self, success: 'bool' = False, description: 'str' = '', images: 'list' = <factory>) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `ExploreResult`

Result of an exploration action.

```python
ExploreResult(self, coverage: 'float' = 0.0, duration: 'float' = 0.0, cells_explored: 'int' = 0, timed_out: 'bool' = False) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `IMUData`

IMU sensor reading.

```python
IMUData(self, acceleration: 'np.ndarray', angular_velocity: 'np.ndarray', orientation: 'np.ndarray', timestamp: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `LaserScan`

2D laser scan.

```python
LaserScan(self, ranges: 'np.ndarray', angles: 'np.ndarray', angle_min: 'float' = 0.0, angle_max: 'float' = 0.0, range_max: 'float' = 12.0, timestamp: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `MoveResult`

Result of a navigation action.

```python
MoveResult(self, success: 'bool', final_pose: 'Pose2D', duration: 'float' = 0.0, distance: 'float' = 0.0, reason: 'str' = 'reached') -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `OccupancyGrid`

2D occupancy grid map.

```python
OccupancyGrid(self, data: 'np.ndarray', resolution: 'float' = 0.05, origin: 'Pose2D' = <factory>, timestamp: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `Pose2D`

2D pose in the map frame.

```python
Pose2D(self, x: 'float' = 0.0, y: 'float' = 0.0, theta: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `RGBDImage`

RGB-D image pair with intrinsics.

```python
RGBDImage(self, rgb: 'np.ndarray', depth: 'np.ndarray', intrinsics: 'CameraIntrinsics', timestamp: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `Velocity`

Body-frame velocity.

```python
Velocity(self, vx: 'float' = 0.0, vy: 'float' = 0.0, omega: 'float' = 0.0) -> None
```

Initialize self.  See help(type(self)) for accurate signature.


## Backends

> Backend Abstraction Layer — the Sim2Real consistency contract.

### `BackendBase`

Abstract base for all robot backends.

Consistency contract guarantees:
- Image: (H, W, 3) uint8 BGR
- Depth: (H, W) float32, meters, invalid=0.0
- LiDAR: (N,) float32, meters, uniform angular sampling
- Pose: right-hand, X forward, Y left, Z up, radians
- Velocity: m/s linear, rad/s angular

**Methods:**

- `connect(self) -> 'None'`
  Establish connection to the backend.
- `disconnect(self) -> 'None'`
  Cleanly disconnect from the backend.
- `explore(self, timeout: 'float' = 60.0) -> 'ExploreResult'`
  Autonomously explore unknown areas.
- `follow_path(self, waypoints: 'list') -> 'MoveResult'`
  Follow a sequence of Pose2D waypoints in order.
- `get_battery_state(self) -> 'BatteryState'`
  Get battery status.
- `get_camera_image(self) -> 'np.ndarray'`
  Get RGB image. Returns (H, W, 3) uint8.
- `get_imu(self) -> 'IMUData'`
  Get IMU reading.
- `get_lidar_scan(self) -> 'LaserScan'`
  Get 2D laser scan.
- `get_map(self) -> 'OccupancyGrid'`
  Get current occupancy grid map.
- `get_pose(self) -> 'Pose2D'`
  Get robot pose in map frame.
- `get_rgbd_image(self) -> 'RGBDImage'`
  Get RGB-D image pair.
- `get_velocity(self) -> 'Velocity'`
  Get current body velocity.
- `is_connected` *(property)*
  Whether the backend is currently connected.
- `move_forward(self, distance: 'float') -> 'MoveResult'`
  Drive forward by the specified distance in meters.
- `move_to(self, x: 'float', y: 'float', theta: 'float | None' = None, timeout: 'float' = 60.0) -> 'MoveResult'`
  Navigate to target pose using path planning.
- `rotate(self, angle: 'float') -> 'MoveResult'`
  Rotate in place by the specified angle in radians.
- `set_velocity(self, vx: 'float', vy: 'float', omega: 'float') -> 'None'`
  Command body velocity. Must be called continuously or timeout stops motors.
- `stop(self) -> 'None'`
  Immediately stop all motion.


## Gymnasium Environments

> Gymnasium environments for the 3we robot platform.

### `ExplorationEnv`

Coverage-based exploration environment.

Observation space (Dict):
    - image: (64, 64, 3) uint8 RGB
    - lidar: (360,) float32, meters
    - pose: (3,) float32 [x, y, theta]
    - velocity: (3,) float32 [vx, vy, omega]
    - coverage_map: (64, 64) float32, 0=unexplored, 1=explored

Action space (Box):
    - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

Reward:
    - New cells explored
    - Collision penalty

```python
ExplorationEnv(self, render_mode: 'str | None' = None, max_steps: 'int' = 1000, map_size: 'int' = 64, image_size: 'tuple[int, int]' = (64, 64), lidar_points: 'int' = 360, arena_size: 'float' = 5.0) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `close(self) -> 'None'`
  After the user has finished using the environment, close contains the code necessary to "clean up" the environment.
- `get_wrapper_attr(self, name: 'str') -> 'Any'`
  Gets the attribute `name` from the environment.
- `has_wrapper_attr(self, name: 'str') -> 'bool'`
  Checks if the attribute `name` exists in the environment.
- `np_random` *(property)*
  Returns the environment's internal :attr:`_np_random` that if not set will initialise with a random seed.
- `np_random_seed` *(property)*
  Returns the environment's internal :attr:`_np_random_seed` that if not set will first initialise with a random int as seed.
- `render(self) -> 'np.ndarray | None'`
  Compute the render frames as specified by :attr:`render_mode` during the initialization of the environment.
- `reset(self, *, seed: 'int | None' = None, options: 'dict[str, Any] | None' = None) -> 'tuple[dict[str, np.ndarray], dict[str, Any]]'`
  Resets the environment to an initial internal state, returning an initial observation and info.
- `set_wrapper_attr(self, name: 'str', value: 'Any', *, force: 'bool' = True) -> 'bool'`
  Sets the attribute `name` on the environment with `value`, see `Wrapper.set_wrapper_attr` for more info.
- `step(self, action: 'np.ndarray') -> 'tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]'`
  Run one timestep of the environment's dynamics using the agent actions.
- `unwrapped` *(property)*
  Returns the base non-wrapped environment.

### `NavigationEnv`

Point-to-point navigation environment.

Observation space (Dict):
    - image: (64, 64, 3) uint8 RGB
    - lidar: (360,) float32, meters
    - pose: (3,) float32 [x, y, theta]
    - velocity: (3,) float32 [vx, vy, omega]
    - goal: (2,) float32 [gx, gy]

Action space (Box):
    - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

Reward:
    - Distance reduction toward goal
    - Collision penalty
    - Goal reached bonus

```python
NavigationEnv(self, render_mode: 'str | None' = None, max_steps: 'int' = 500, goal_threshold: 'float' = 0.2, image_size: 'tuple[int, int]' = (64, 64), lidar_points: 'int' = 360, arena_size: 'float' = 5.0) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `close(self) -> 'None'`
  After the user has finished using the environment, close contains the code necessary to "clean up" the environment.
- `get_wrapper_attr(self, name: 'str') -> 'Any'`
  Gets the attribute `name` from the environment.
- `has_wrapper_attr(self, name: 'str') -> 'bool'`
  Checks if the attribute `name` exists in the environment.
- `np_random` *(property)*
  Returns the environment's internal :attr:`_np_random` that if not set will initialise with a random seed.
- `np_random_seed` *(property)*
  Returns the environment's internal :attr:`_np_random_seed` that if not set will first initialise with a random int as seed.
- `render(self) -> 'np.ndarray | None'`
  Compute the render frames as specified by :attr:`render_mode` during the initialization of the environment.
- `reset(self, *, seed: 'int | None' = None, options: 'dict[str, Any] | None' = None) -> 'tuple[dict[str, np.ndarray], dict[str, Any]]'`
  Resets the environment to an initial internal state, returning an initial observation and info.
- `set_wrapper_attr(self, name: 'str', value: 'Any', *, force: 'bool' = True) -> 'bool'`
  Sets the attribute `name` on the environment with `value`, see `Wrapper.set_wrapper_attr` for more info.
- `step(self, action: 'np.ndarray') -> 'tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]'`
  Run one timestep of the environment's dynamics using the agent actions.
- `unwrapped` *(property)*
  Returns the base non-wrapped environment.

### `ObjectNavEnv`

Object-goal navigation: navigate to an object by category name.

Observation space (Dict):
    - image: (64, 64, 3) uint8 RGB
    - lidar: (360,) float32, meters
    - pose: (3,) float32 [x, y, theta]
    - velocity: (3,) float32 [vx, vy, omega]
    - object_goal: (10,) float32 one-hot encoding of target category

Action space (Box):
    - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

Reward:
    - Distance reduction toward object
    - Object reached bonus
    - Collision penalty

```python
ObjectNavEnv(self, render_mode: 'str | None' = None, max_steps: 'int' = 500, goal_threshold: 'float' = 0.3, image_size: 'tuple[int, int]' = (64, 64), lidar_points: 'int' = 360, arena_size: 'float' = 5.0, num_objects: 'int' = 5) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `close(self) -> 'None'`
  After the user has finished using the environment, close contains the code necessary to "clean up" the environment.
- `get_wrapper_attr(self, name: 'str') -> 'Any'`
  Gets the attribute `name` from the environment.
- `has_wrapper_attr(self, name: 'str') -> 'bool'`
  Checks if the attribute `name` exists in the environment.
- `np_random` *(property)*
  Returns the environment's internal :attr:`_np_random` that if not set will initialise with a random seed.
- `np_random_seed` *(property)*
  Returns the environment's internal :attr:`_np_random_seed` that if not set will first initialise with a random int as seed.
- `render(self) -> 'np.ndarray | None'`
  Compute the render frames as specified by :attr:`render_mode` during the initialization of the environment.
- `reset(self, *, seed: 'int | None' = None, options: 'dict[str, Any] | None' = None) -> 'tuple[dict[str, np.ndarray], dict[str, Any]]'`
  Resets the environment to an initial internal state, returning an initial observation and info.
- `set_wrapper_attr(self, name: 'str', value: 'Any', *, force: 'bool' = True) -> 'bool'`
  Sets the attribute `name` on the environment with `value`, see `Wrapper.set_wrapper_attr` for more info.
- `step(self, action: 'np.ndarray') -> 'tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]'`
  Run one timestep of the environment's dynamics using the agent actions.
- `unwrapped` *(property)*
  Returns the base non-wrapped environment.

### `VLNEnv`

Vision-Language Navigation: follow a natural language instruction.

Observation space (Dict):
    - image: (64, 64, 3) uint8 RGB
    - lidar: (360,) float32, meters
    - pose: (3,) float32 [x, y, theta]
    - velocity: (3,) float32 [vx, vy, omega]
    - instruction_embedding: (64,) float32 encoded instruction

Action space (Box):
    - (3,) float32 [vx, vy, omega] normalized to [-1, 1]

The environment simulates waypoint-following for language instructions.
A pre-defined path of waypoints represents the instruction trajectory;
reward is based on progress along the path.

```python
VLNEnv(self, render_mode: 'str | None' = None, max_steps: 'int' = 500, waypoint_threshold: 'float' = 0.3, image_size: 'tuple[int, int]' = (64, 64), lidar_points: 'int' = 360, arena_size: 'float' = 5.0, num_waypoints: 'int' = 4, embedding_dim: 'int' = 64) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `close(self) -> 'None'`
  After the user has finished using the environment, close contains the code necessary to "clean up" the environment.
- `get_wrapper_attr(self, name: 'str') -> 'Any'`
  Gets the attribute `name` from the environment.
- `has_wrapper_attr(self, name: 'str') -> 'bool'`
  Checks if the attribute `name` exists in the environment.
- `np_random` *(property)*
  Returns the environment's internal :attr:`_np_random` that if not set will initialise with a random seed.
- `np_random_seed` *(property)*
  Returns the environment's internal :attr:`_np_random_seed` that if not set will first initialise with a random int as seed.
- `render(self) -> 'np.ndarray | None'`
  Compute the render frames as specified by :attr:`render_mode` during the initialization of the environment.
- `reset(self, *, seed: 'int | None' = None, options: 'dict[str, Any] | None' = None) -> 'tuple[dict[str, np.ndarray], dict[str, Any]]'`
  Resets the environment to an initial internal state, returning an initial observation and info.
- `set_wrapper_attr(self, name: 'str', value: 'Any', *, force: 'bool' = True) -> 'bool'`
  Sets the attribute `name` on the environment with `value`, see `Wrapper.set_wrapper_attr` for more info.
- `step(self, action: 'np.ndarray') -> 'tuple[dict[str, np.ndarray], float, bool, bool, dict[str, Any]]'`
  Run one timestep of the environment's dynamics using the agent actions.
- `unwrapped` *(property)*
  Returns the base non-wrapped environment.


## AI Module

> VLM-driven instruction execution.

### Module: `threewe.ai.vlm_runner`

### `VLMRunner`

Runs VLM inference for robot instruction execution.

```python
VLMRunner(self, model: 'str' = 'gpt-4o', api_key: 'str | None' = None, base_url: 'str | None' = None, max_steps: 'int' = 20, temperature: 'float' = 0.0) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `plan(self, image: 'np.ndarray', instruction: 'str') -> 'str'`
  Get a single-step action plan from the VLM given an image and instruction.

### `execute_vlm_instruction(robot: 'Robot', instruction: 'str', model: 'str' = 'gpt-4o', api_key: 'str | None' = None, base_url: 'str | None' = None, max_steps: 'int' = 20, on_step: 'StepCallback | None' = None) -> 'ExecutionResult'`

Execute a natural language instruction using a VLM in a perception-action loop.

The VLM observes camera images and generates navigation actions
until the instruction is fulfilled or max_steps is reached.

Args:
    robot: Connected Robot instance.
    instruction: Natural language task description.
    model: VLM model name.
    api_key: Optional API key override.
    base_url: Optional API base URL override.
    max_steps: Maximum perception-action cycles.
    on_step: Optional callback invoked after each step with
        (step_number, raw_response, parsed_action).

> VLA (Vision-Language-Action) model runner.

### Module: `threewe.ai.vla_runner`

### `VLARunner`

Run VLA models for end-to-end robot control.

A VLA model takes observations (image + state) and optionally a language
instruction, and directly outputs action vectors (velocities/joint commands).

```python
VLARunner(self, model_path: 'str', device: 'str' = 'cpu') -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `action_dim` *(property)*
  Expected output action dimension.
- `predict(self, obs: 'dict[str, np.ndarray]', instruction: 'str' = '') -> 'np.ndarray'`
  Predict action from observation.


## Data Module

> Trajectory recording for imitation learning data collection.

### Module: `threewe.data.recorder`

### `Episode`

A single recorded episode (trajectory).

```python
Episode(self, steps: 'list[TimeStep]' = <factory>, metadata: 'dict' = <factory>) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `duration` *(property)*
- `length` *(property)*

### `TimeStep`

A single recorded timestep.

```python
TimeStep(self, timestamp: 'float', image: 'np.ndarray', pose: 'np.ndarray', velocity: 'np.ndarray', action: 'np.ndarray', lidar: 'np.ndarray | None' = None, depth: 'np.ndarray | None' = None) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `TrajectoryRecorder`

Records robot trajectories for imitation learning.

Usage:
    recorder = TrajectoryRecorder(robot)
    recorder.start_episode()
    # ... control robot ...
    recorder.record_step(action=[0.1, 0.0, 0.0])
    recorder.end_episode()
    recorder.save_hdf5("trajectories.h5")

```python
TrajectoryRecorder(self, robot: 'Robot', record_lidar: 'bool' = False, record_depth: 'bool' = False) -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `end_episode(self) -> 'Episode'`
  End current episode and store it.
- `num_episodes` *(property)*
- `record_step(self, action: 'list[float] | np.ndarray') -> 'None'`
  Record current observation and the action taken.
- `save_hdf5(self, path: 'str | Path') -> 'None'`
  Save all episodes to HDF5 format.
- `save_lerobot(self, output_dir: 'str | Path') -> 'None'`
  Export episodes in LeRobot-compatible format (Parquet + MP4).
- `start_episode(self, metadata: 'dict | None' = None) -> 'None'`
  Start recording a new episode.
- `total_steps` *(property)*

> HuggingFace Hub interoperability for LeRobot datasets and models.

### Module: `threewe.data.hub`

### `DatasetCard`

Metadata for a dataset card (README.md on Hub).

```python
DatasetCard(self, name: 'str', robot: 'str', task: 'str', num_episodes: 'int', total_steps: 'int', fps: 'int' = 10, description: 'str' = '') -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `generate_dataset_card(metadata: 'DatasetCard') -> 'str'`

Generate a README.md content for a LeRobot dataset on HuggingFace Hub.

Args:
    metadata: Dataset card metadata.

Returns:
    Markdown string for the README.md.

### `pull_dataset(repo_id: 'str', local_dir: 'str | Path', token: 'str | None' = None) -> 'Path'`

Pull a LeRobot dataset from HuggingFace Hub.

Args:
    repo_id: HuggingFace repo ID.
    local_dir: Local directory to save to.
    token: HuggingFace API token.

Returns:
    Path to the downloaded dataset.

Raises:
    ImportError: If huggingface-hub is not installed.

### `push_dataset(local_dir: 'str | Path', repo_id: 'str', token: 'str | None' = None) -> 'str'`

Push a LeRobot dataset directory to HuggingFace Hub.

Args:
    local_dir: Local directory containing data/, videos/, meta/.
    repo_id: HuggingFace repo ID (e.g. 'user/dataset-name').
    token: HuggingFace API token. Uses cached token if None.

Returns:
    URL of the uploaded dataset.

Raises:
    ImportError: If huggingface-hub is not installed.
    FileNotFoundError: If local_dir doesn't exist.

### `validate_lerobot_schema(parquet_path: 'str | Path') -> 'list[str]'`

Validate that a Parquet file follows LeRobot column conventions.

Args:
    parquet_path: Path to a .parquet file.

Returns:
    List of validation errors (empty if valid).


## Benchmark

> Benchmark runner — executes evaluation episodes and collects metrics.

### Module: `threewe.benchmark.runner`

### `BenchmarkReport`

Aggregated benchmark results.

```python
BenchmarkReport(self, task: 'str', backend: 'str', num_episodes: 'int', success_rate: 'float', spl: 'float', avg_duration: 'float', avg_path_length: 'float', coverage: 'float' = 0.0, episodes: 'list[EpisodeResult]' = <factory>, timestamp: 'str' = '') -> None
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `save(self, path: 'str | Path') -> 'None'`
- `to_json(self) -> 'str'`

### `BenchmarkRunner`

Runs standardized benchmark episodes on the robot.

```python
BenchmarkRunner(self, backend: 'str' = 'gazebo', scene: 'str' = 'office_v2') -> 'None'
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `run_exploration(self, num_episodes: 'int' = 10, timeout_per_episode: 'float' = 120.0) -> 'BenchmarkReport'`
  Run exploration coverage benchmark.
- `run_objectnav(self, num_episodes: 'int' = 100, seed: 'int' = 42) -> 'BenchmarkReport'`
  Run object-goal navigation benchmark using scene poses.
- `run_pointnav(self, num_episodes: 'int' = 100, seed: 'int' = 42) -> 'BenchmarkReport'`
  Run point-to-point navigation benchmark using scene poses.

### `EpisodeResult`

Result of a single benchmark episode.

```python
EpisodeResult(self, episode_id: 'int', success: 'bool', duration: 'float', path_length: 'float', optimal_length: 'float' = 0.0, coverage: 'float' = 0.0, reason: 'str' = '') -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `run_benchmark_cli(task: 'str', episodes: 'int', backend: 'str', scene: 'str') -> 'None'`

CLI entry point for benchmark execution.

> Benchmark metrics: SPL, Success Rate, Coverage.

### Module: `threewe.benchmark.metrics`

### `compute_coverage(explored_cells: 'int', total_cells: 'int') -> 'float'`

Compute exploration coverage ratio.

### `compute_spl(successes: 'list[bool]', path_lengths: 'list[float]', optimal_lengths: 'list[float]') -> 'float'`

Compute Success weighted by Path Length (SPL).

SPL = (1/N) * sum( S_i * (L_i / max(P_i, L_i)) )
where S_i = success, L_i = optimal path, P_i = actual path.

### `compute_success_rate(successes: 'list[bool]') -> 'float'`

Compute success rate as fraction of successful episodes.

> Benchmark task definitions — pluggable evaluation protocols.

### Module: `threewe.benchmark.tasks`

### `BenchmarkTask`

Protocol for pluggable benchmark tasks.

```python
BenchmarkTask(self, *args, **kwargs)
```

**Methods:**

- `is_success(self, episode: 'EpisodeResult') -> 'bool'`
- `metrics` *(property)*
- `name` *(property)*
- `valid_scenes` *(property)*

### `ExplorationTask`

Coverage exploration task.

Robot must maximize area coverage within a time limit.
Metrics: coverage_pct, duration

```python
ExplorationTask(self, name: 'str' = 'exploration', metrics: 'tuple[str, ...]' = ('coverage', 'avg_duration', 'success_rate'), valid_scenes: 'tuple[str, ...]' = ('office_v2', 'apartment_v1', 'corridor_v1', 'warehouse_v1', 'outdoor_v1'), coverage_threshold: 'float' = 0.8) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `is_success(self, episode: 'EpisodeResult') -> 'bool'`

### `ObjectNavTask`

Object-goal navigation task.

Robot must navigate to an object of a specified category.
Metrics: SPL, success_rate

```python
ObjectNavTask(self, name: 'str' = 'objectnav', metrics: 'tuple[str, ...]' = ('spl', 'success_rate', 'avg_duration'), valid_scenes: 'tuple[str, ...]' = ('office_v2', 'apartment_v1', 'warehouse_v1', 'cluttered_v1', 'dynamic_v1'), object_categories: 'tuple[str, ...]' = ('chair', 'desk', 'door', 'plant', 'monitor', 'couch', 'table', 'shelf', 'refrigerator', 'bed')) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `is_success(self, episode: 'EpisodeResult') -> 'bool'`

### `PointNavTask`

Point-to-point navigation task.

Metrics: SPL, success_rate
Success condition: robot reaches within 0.5m of goal.

```python
PointNavTask(self, name: 'str' = 'pointnav', metrics: 'tuple[str, ...]' = ('spl', 'success_rate', 'avg_duration'), valid_scenes: 'tuple[str, ...]' = ('office_v2', 'apartment_v1', 'corridor_v1', 'warehouse_v1', 'cluttered_v1', 'outdoor_v1', 'dynamic_v1'), success_threshold: 'float' = 0.5) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

**Methods:**

- `is_success(self, episode: 'EpisodeResult') -> 'bool'`

### `get_task(name: 'str') -> 'BenchmarkTask'`

Get a benchmark task by name.

Raises:
    ValueError: If task name is unknown.

### `list_tasks() -> 'list[str]'`

Return names of all registered benchmark tasks.


## CLI

> CLI entry point for threewe commands.

### `main() -> 'None'`


## Configuration

> Configuration loading and validation.

### `APIConfig`

APIConfig(image_size: 'tuple[int, int]' = (640, 480), lidar_points: 'int' = 360, control_frequency: 'int' = 50)

```python
APIConfig(self, image_size: 'tuple[int, int]' = (640, 480), lidar_points: 'int' = 360, control_frequency: 'int' = 50) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `HardwareConfig`

HardwareConfig(platform: 'str' = '3we_standard_v2', wheels: 'str' = 'mecanum_65mm', lidar: 'str' = 'ld06', camera: 'str' = 'fisheye_1080p', imu: 'str' = 'bno055')

```python
HardwareConfig(self, platform: 'str' = '3we_standard_v2', wheels: 'str' = 'mecanum_65mm', lidar: 'str' = 'ld06', camera: 'str' = 'fisheye_1080p', imu: 'str' = 'bno055') -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `LimitsConfig`

LimitsConfig(max_linear_velocity: 'float' = 0.5, max_angular_velocity: 'float' = 1.0, safety_distance: 'float' = 0.15)

```python
LimitsConfig(self, max_linear_velocity: 'float' = 0.5, max_angular_velocity: 'float' = 1.0, safety_distance: 'float' = 0.15) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `NavigationConfig`

NavigationConfig(planner: 'str' = 'navfn', controller: 'str' = 'dwb', goal_tolerance: 'float' = 0.1)

```python
NavigationConfig(self, planner: 'str' = 'navfn', controller: 'str' = 'dwb', goal_tolerance: 'float' = 0.1) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `RobotConfig`

RobotConfig(hardware: 'HardwareConfig' = <factory>, limits: 'LimitsConfig' = <factory>, navigation: 'NavigationConfig' = <factory>, api: 'APIConfig' = <factory>)

```python
RobotConfig(self, hardware: 'HardwareConfig' = <factory>, limits: 'LimitsConfig' = <factory>, navigation: 'NavigationConfig' = <factory>, api: 'APIConfig' = <factory>) -> None
```

Initialize self.  See help(type(self)) for accurate signature.

### `load_config(name: 'str' = 'standard_v2') -> 'RobotConfig'`

Load a robot configuration by name.

Searches in order:
1. Absolute/relative path if name contains a path separator
2. Built-in configs directory (sdk/threewe/configs/)
3. Current working directory


## Exceptions

> Exception hierarchy for threewe.

### `ConnectionError`

Cannot connect to the robot or simulator.

```python
ConnectionError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `EmergencyStopError`

Emergency stop triggered.

```python
EmergencyStopError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `HardwareError`

Hardware fault detected (motor overheat, sensor disconnect).

```python
HardwareError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `NavigationError`

Navigation action failed (path blocked, goal unreachable).

```python
NavigationError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `SafetyError`

Safety constraint violated (speed limit, boundary breach).

```python
SafetyError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `ThreeweError`

Base exception for all threewe errors.

```python
ThreeweError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

### `TimeoutError`

Operation timed out.

```python
TimeoutError(self, /, *args, **kwargs)
```

Initialize self.  See help(type(self)) for accurate signature.

