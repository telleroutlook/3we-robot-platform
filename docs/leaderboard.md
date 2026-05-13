# 3we Benchmark Leaderboard

Standardized evaluation for embodied AI agents on the 3we robot platform. All benchmarks run in deterministic simulation environments with fixed seeds, enabling reproducible comparison of navigation and exploration policies.

## Tasks

The benchmark suite evaluates agents on three core embodied AI tasks:

| Task | Description | Environment |
|------|-------------|-------------|
| **PointNav** | Navigate to a specified (x, y) coordinate | Indoor office scenes with static obstacles |
| **ObjectNav** | Navigate to an instance of a named object category | Indoor scenes with semantic object annotations |
| **Exploration** | Maximize map coverage within a time budget | Unknown environments requiring frontier-based or learned exploration |

## Metrics

| Metric | Definition | Range |
|--------|-----------|-------|
| **SR** (Success Rate) | Fraction of episodes where the agent reached the goal | 0.0 - 1.0 |
| **SPL** (Success weighted by Path Length) | Success penalized by path inefficiency relative to shortest path | 0.0 - 1.0 |
| **Duration** | Mean episode wall-clock time in seconds | 0.0+ |
| **Coverage** | Fraction of explorable area visited (exploration only) | 0.0 - 1.0 |

## Baseline Results

Results measured on the `office_v2` scene with 100 episodes per task, seed range `[0, 99]`.

| Agent | Task | Scene | SR | SPL | Duration (s) | Coverage |
|-------|------|-------|-----|-----|--------------|----------|
| Nav2 DWB | pointnav | office_v2 | 0.85 | 0.72 | 12.3 | - |
| Frontier Exploration | exploration | office_v2 | 0.90 | - | 45.2 | 0.82 |
| Random Agent | objectnav | office_v2 | 0.12 | 0.08 | 28.1 | - |

## Running Benchmarks

Install the benchmark dependencies and run evaluation:

```bash
pip install threewe[sim]
```

Run a benchmark task:

```bash
threewe benchmark run --task pointnav --episodes 100
```

Run with a specific backend and scene:

```bash
threewe benchmark run --task objectnav --episodes 100 --backend gazebo --scene office_v2
```

Compare your result against a baseline:

```bash
threewe benchmark compare --result result.json --baseline nav2_pointnav_office
```

## Submission Format

Results must be submitted as a JSON file conforming to the following schema:

```json
{
  "agent_name": "string (required) — display name for leaderboard",
  "task": "string (required) — one of: pointnav, objectnav, exploration",
  "scene": "string (required) — scene identifier (e.g., office_v2)",
  "episodes": "integer (required) — number of episodes evaluated",
  "seed_start": "integer (required) — first seed used",
  "metrics": {
    "success_rate": "float (required) — fraction of successful episodes",
    "spl": "float (required for pointnav/objectnav) — success weighted by path length",
    "mean_duration": "float (required) — mean episode duration in seconds",
    "coverage": "float (required for exploration) — fraction of area explored"
  },
  "software": {
    "threewe_version": "string (required) — threewe package version",
    "backend": "string (required) — gazebo or isaac_sim",
    "backend_version": "string (required) — simulator version"
  },
  "metadata": {
    "method": "string (optional) — brief description of the approach",
    "paper_url": "string (optional) — link to paper or preprint",
    "code_url": "string (optional) — link to source code",
    "hardware": "string (optional) — training hardware description"
  }
}
```

Example submission:

```json
{
  "agent_name": "PPO-LiDAR-v2",
  "task": "pointnav",
  "scene": "office_v2",
  "episodes": 100,
  "seed_start": 0,
  "metrics": {
    "success_rate": 0.91,
    "spl": 0.78,
    "mean_duration": 10.5
  },
  "software": {
    "threewe_version": "0.2.0",
    "backend": "gazebo",
    "backend_version": "Harmonic"
  },
  "metadata": {
    "method": "PPO with 360-point LiDAR + goal vector, 500k timesteps",
    "code_url": "https://github.com/user/ppo-nav"
  }
}
```

## How to Submit

Submit your result to the leaderboard:

```bash
threewe benchmark submit --result result.json
```

The submission tool validates schema compliance and checks that the seed range matches the official protocol before uploading.

## Evaluation Protocol

To ensure fair and reproducible comparison, all submissions must follow this protocol:

1. **Deterministic seeds**: Episodes use seeds `[seed_start, seed_start + episodes)`. The official evaluation uses `seed_start=0`.
2. **Scene version**: Results are only comparable within the same scene version. The current official scene is `office_v2`.
3. **Software version**: Record the exact `threewe` package version and simulator version. Results from different versions are grouped separately on the leaderboard.
4. **No scene-specific tuning**: Agents must not be trained on the exact evaluation episodes. Training on the same scene type is permitted, but not on the specific seed-generated configurations used for evaluation.
5. **Timeout**: Episodes that exceed the task-specific time limit are marked as failures. PointNav: 60s, ObjectNav: 120s, Exploration: 180s.
6. **Single attempt**: Each episode is attempted exactly once. No retries or cherry-picking.

## Full Documentation

For detailed benchmark API reference, custom task definitions, and advanced evaluation options, see the [benchmark module documentation](api_reference.md#benchmark).
