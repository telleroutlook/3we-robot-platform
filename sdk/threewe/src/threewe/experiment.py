# SPDX-License-Identifier: Apache-2.0
"""Experiment reproducibility — deterministic protocol specification.

Captures all parameters needed to reproduce a robotics experiment:
seed, backend, scene, hardware, task, hyperparameters, and metadata.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import threewe


@dataclass(frozen=True)
class ExperimentProtocol:
    """Complete specification for reproducing a robotics experiment.

    Captures everything needed to re-run an experiment identically:
    random seed, simulation backend, scene, hardware profile,
    task configuration, and hyperparameters.
    """

    seed: int
    backend: str
    scene: str
    hardware: str
    task: str
    hyperparams: dict = field(default_factory=dict)
    timestamp: str = ""
    git_sha: str = ""
    sdk_version: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if not self.sdk_version:
            object.__setattr__(self, "sdk_version", threewe.__version__)
        if not self.git_sha:
            sha = _get_git_sha()
            if sha:
                object.__setattr__(self, "git_sha", sha)


def save_protocol(protocol: ExperimentProtocol, path: str | Path) -> None:
    """Save an experiment protocol to a JSON file.

    Args:
        protocol: The protocol to persist.
        path: Output file path (will be created/overwritten).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(protocol), indent=2))


def load_protocol(path: str | Path) -> ExperimentProtocol:
    """Load an experiment protocol from a JSON file.

    Args:
        path: Path to a previously saved protocol JSON.

    Returns:
        ExperimentProtocol with all fields populated.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Protocol file not found: {path}")

    data = json.loads(path.read_text())
    return ExperimentProtocol(
        seed=data["seed"],
        backend=data["backend"],
        scene=data["scene"],
        hardware=data["hardware"],
        task=data["task"],
        hyperparams=data.get("hyperparams", {}),
        timestamp=data.get("timestamp", ""),
        git_sha=data.get("git_sha", ""),
        sdk_version=data.get("sdk_version", ""),
    )


def _get_git_sha() -> str:
    """Get current git commit SHA, or empty string if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""
