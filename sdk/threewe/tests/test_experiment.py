# SPDX-License-Identifier: Apache-2.0
"""Tests for experiment reproducibility module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from threewe.experiment import ExperimentProtocol, load_protocol, save_protocol


class TestExperimentProtocol:
    def test_creation_with_required_fields(self):
        proto = ExperimentProtocol(
            seed=42,
            backend="gazebo",
            scene="office_v2",
            hardware="3we_standard_v2",
            task="pointnav",
        )
        assert proto.seed == 42
        assert proto.backend == "gazebo"
        assert proto.scene == "office_v2"
        assert proto.hardware == "3we_standard_v2"
        assert proto.task == "pointnav"
        assert proto.hyperparams == {}

    def test_auto_populates_timestamp(self):
        proto = ExperimentProtocol(
            seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
        )
        assert proto.timestamp != ""
        assert "T" in proto.timestamp

    def test_auto_populates_sdk_version(self):
        import threewe

        proto = ExperimentProtocol(
            seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
        )
        assert proto.sdk_version == threewe.__version__

    def test_auto_populates_git_sha(self):
        proto = ExperimentProtocol(
            seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
        )
        assert isinstance(proto.git_sha, str)

    def test_explicit_timestamp_not_overwritten(self):
        proto = ExperimentProtocol(
            seed=1,
            backend="gazebo",
            scene="s",
            hardware="h",
            task="pointnav",
            timestamp="2026-01-01T00:00:00",
        )
        assert proto.timestamp == "2026-01-01T00:00:00"

    def test_explicit_sdk_version_not_overwritten(self):
        proto = ExperimentProtocol(
            seed=1,
            backend="gazebo",
            scene="s",
            hardware="h",
            task="pointnav",
            sdk_version="0.1.0",
        )
        assert proto.sdk_version == "0.1.0"

    def test_frozen(self):
        proto = ExperimentProtocol(
            seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
        )
        with pytest.raises(AttributeError):
            proto.seed = 99  # type: ignore[misc]

    def test_hyperparams(self):
        proto = ExperimentProtocol(
            seed=1,
            backend="gazebo",
            scene="s",
            hardware="h",
            task="pointnav",
            hyperparams={"lr": 0.001, "batch_size": 32},
        )
        assert proto.hyperparams == {"lr": 0.001, "batch_size": 32}

    def test_git_sha_graceful_failure(self):
        with patch("threewe.experiment._get_git_sha", return_value=""):
            proto = ExperimentProtocol(
                seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
            )
            assert proto.git_sha == ""


class TestSaveLoadProtocol:
    def test_save_and_load_roundtrip(self, tmp_path):
        proto = ExperimentProtocol(
            seed=123,
            backend="isaac_sim",
            scene="warehouse_v1",
            hardware="unitree_go2",
            task="exploration",
            hyperparams={"gamma": 0.99},
            timestamp="2026-05-13T10:00:00",
            sdk_version="0.2.0a2",
            git_sha="abc123def456",
        )
        path = tmp_path / "protocol.json"
        save_protocol(proto, path)

        loaded = load_protocol(path)
        assert loaded.seed == 123
        assert loaded.backend == "isaac_sim"
        assert loaded.scene == "warehouse_v1"
        assert loaded.hardware == "unitree_go2"
        assert loaded.task == "exploration"
        assert loaded.hyperparams == {"gamma": 0.99}
        assert loaded.timestamp == "2026-05-13T10:00:00"
        assert loaded.sdk_version == "0.2.0a2"
        assert loaded.git_sha == "abc123def456"

    def test_save_creates_directories(self, tmp_path):
        proto = ExperimentProtocol(
            seed=1, backend="gazebo", scene="s", hardware="h", task="pointnav"
        )
        path = tmp_path / "nested" / "dir" / "protocol.json"
        save_protocol(proto, path)
        assert path.exists()

    def test_save_produces_valid_json(self, tmp_path):
        proto = ExperimentProtocol(
            seed=42, backend="gazebo", scene="office_v2", hardware="h", task="pointnav"
        )
        path = tmp_path / "out.json"
        save_protocol(proto, path)

        data = json.loads(path.read_text())
        assert data["seed"] == 42
        assert data["backend"] == "gazebo"
        assert data["scene"] == "office_v2"

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Protocol file not found"):
            load_protocol(tmp_path / "nonexistent.json")

    def test_load_handles_missing_optional_fields(self, tmp_path):
        data = {
            "seed": 7,
            "backend": "gazebo",
            "scene": "s",
            "hardware": "h",
            "task": "pointnav",
        }
        path = tmp_path / "minimal.json"
        path.write_text(json.dumps(data))

        loaded = load_protocol(path)
        assert loaded.seed == 7
        assert loaded.hyperparams == {}
        assert loaded.timestamp != ""
        assert loaded.sdk_version != ""
