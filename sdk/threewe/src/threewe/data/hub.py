# SPDX-License-Identifier: Apache-2.0
"""HuggingFace Hub interoperability for LeRobot datasets and models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetCard:
    """Metadata for a dataset card (README.md on Hub)."""

    name: str
    robot: str
    task: str
    num_episodes: int
    total_steps: int
    fps: int = 10
    description: str = ""


def generate_dataset_card(metadata: DatasetCard) -> str:
    """Generate a README.md content for a LeRobot dataset on HuggingFace Hub.

    Args:
        metadata: Dataset card metadata.

    Returns:
        Markdown string for the README.md.
    """
    return f"""---
tags:
- lerobot
- robotics
- {metadata.task}
task_categories:
- robotics
---

# {metadata.name}

{metadata.description or f"LeRobot-compatible dataset recorded with threewe on {metadata.robot}."}

## Dataset Info

| Key | Value |
|-----|-------|
| Robot | {metadata.robot} |
| Task | {metadata.task} |
| Episodes | {metadata.num_episodes} |
| Total Steps | {metadata.total_steps} |
| FPS | {metadata.fps} |

## Format

This dataset follows the [LeRobot](https://github.com/huggingface/lerobot) format:

```
data/
  episode_000.parquet
  episode_001.parquet
  ...
videos/
  episode_000.mp4
  ...
meta/
  info.json
```

## Usage

```python
from threewe.data import pull_dataset

pull_dataset("{metadata.name}", local_dir="./data")
```
"""


def validate_lerobot_schema(parquet_path: str | Path) -> list[str]:
    """Validate that a Parquet file follows LeRobot column conventions.

    Args:
        parquet_path: Path to a .parquet file.

    Returns:
        List of validation errors (empty if valid).
    """
    path = Path(parquet_path)
    errors: list[str] = []

    if not path.exists():
        errors.append(f"File not found: {path}")
        return errors

    if path.suffix == ".csv":
        import csv

        with open(path) as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
    else:
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(path)
            columns = set(table.column_names)
        except ImportError:
            errors.append("pyarrow not installed — cannot validate Parquet schema")
            return errors

    required_columns = {"timestamp", "action_vx", "action_vy", "action_omega"}
    pose_columns = {"pose_x", "pose_y", "pose_theta"}

    missing_required = required_columns - columns
    if missing_required:
        errors.append(f"Missing required columns: {sorted(missing_required)}")

    missing_pose = pose_columns - columns
    if missing_pose:
        errors.append(f"Missing pose columns: {sorted(missing_pose)}")

    return errors


def push_dataset(
    local_dir: str | Path,
    repo_id: str,
    token: str | None = None,
) -> str:
    """Push a LeRobot dataset directory to HuggingFace Hub.

    Args:
        local_dir: Local directory containing data/, videos/, meta/.
        repo_id: HuggingFace repo ID (e.g. 'user/dataset-name').
        token: HuggingFace API token. Uses cached token if None.

    Returns:
        URL of the uploaded dataset.

    Raises:
        ImportError: If huggingface-hub is not installed.
        FileNotFoundError: If local_dir doesn't exist.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise ImportError(
            "huggingface-hub is required for Hub operations. Install with: pip install threewe[hub]"
        ) from exc

    local_dir = Path(local_dir)
    if not local_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {local_dir}")

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    api.upload_folder(
        folder_path=str(local_dir),
        repo_id=repo_id,
        repo_type="dataset",
    )

    return f"https://huggingface.co/datasets/{repo_id}"


def pull_dataset(
    repo_id: str,
    local_dir: str | Path,
    token: str | None = None,
    revision: str | None = None,
) -> Path:
    """Pull a LeRobot dataset from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repo ID.
        local_dir: Local directory to save to.
        token: HuggingFace API token.
        revision: Specific dataset revision (commit hash) to pin the download.

    Returns:
        Path to the downloaded dataset.

    Raises:
        ImportError: If huggingface-hub is not installed.
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise ImportError(
            "huggingface-hub is required for Hub operations. Install with: pip install threewe[hub]"
        ) from exc

    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    path = snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=str(local_dir),
        token=token,
        revision=revision,
    )
    return Path(path)
