# threewe

AI-First Python API for the 3we robot platform — Sim2Real with zero code changes.

## Quick Start

```python
from threewe import Robot

async with Robot(backend="gazebo") as robot:
    image = robot.get_image()
    robot.move_to(x=2.0, y=1.0)
    pose = robot.get_pose()
```

## Installation

```bash
pip install threewe
```

For simulation support:
```bash
pip install threewe[sim]
```

For AI integration (VLM/VLA):
```bash
pip install threewe[ai]
```

## License

Apache-2.0
