# SPDX-License-Identifier: Apache-2.0
"""Tests for HuggingFace Hub interoperability."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from threewe.data.hub import (
    DatasetCard,
    generate_dataset_card,
    pull_dataset,
    push_dataset,
    validate_lerobot_schema,
)


class TestGenerateDatasetCard:
    def test_basic_card(self):
        card = DatasetCard(
            name="test-dataset",
            robot="3we_standard_v2",
            task="pointnav",
            num_episodes=50,
            total_steps=5000,
        )
        md = generate_dataset_card(card)
        assert "# test-dataset" in md
        assert "3we_standard_v2" in md
        assert "pointnav" in md
        assert "50" in md
        assert "5000" in md

    def test_card_has_lerobot_tag(self):
        card = DatasetCard(name="x", robot="r", task="t", num_episodes=1, total_steps=10)
        md = generate_dataset_card(card)
        assert "lerobot" in md

    def test_card_with_description(self):
        card = DatasetCard(
            name="x",
            robot="r",
            task="t",
            num_episodes=1,
            total_steps=10,
            description="Custom description here",
        )
        md = generate_dataset_card(card)
        assert "Custom description here" in md


class TestValidateLerobotSchema:
    def test_valid_csv(self, tmp_path: Path):
        import csv

        path = tmp_path / "episode.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp",
                    "pose_x",
                    "pose_y",
                    "pose_theta",
                    "action_vx",
                    "action_vy",
                    "action_omega",
                    "vel_vx",
                    "vel_vy",
                    "vel_omega",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "timestamp": 1.0,
                    "pose_x": 0.0,
                    "pose_y": 0.0,
                    "pose_theta": 0.0,
                    "action_vx": 0.1,
                    "action_vy": 0.0,
                    "action_omega": 0.0,
                    "vel_vx": 0.1,
                    "vel_vy": 0.0,
                    "vel_omega": 0.0,
                }
            )

        errors = validate_lerobot_schema(path)
        assert errors == []

    def test_missing_columns(self, tmp_path: Path):
        import csv

        path = tmp_path / "episode.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "pose_x"])
            writer.writeheader()
            writer.writerow({"timestamp": 1.0, "pose_x": 0.0})

        errors = validate_lerobot_schema(path)
        assert len(errors) > 0
        assert any("Missing required" in e for e in errors)

    def test_file_not_found(self, tmp_path: Path):
        errors = validate_lerobot_schema(tmp_path / "nonexistent.parquet")
        assert len(errors) == 1
        assert "not found" in errors[0]


class TestPushDataset:
    def test_import_error_without_hub(self, tmp_path: Path):
        with patch.dict("sys.modules", {"huggingface_hub": None}):
            with pytest.raises(ImportError, match="huggingface-hub"):
                push_dataset(tmp_path, "user/dataset")

    def test_missing_directory(self, tmp_path: Path):
        mock_hf = MagicMock()
        with patch.dict("sys.modules", {"huggingface_hub": mock_hf}):
            with pytest.raises(FileNotFoundError):
                push_dataset(tmp_path / "nonexistent", "user/dataset")

    def test_push_calls_api(self, tmp_path: Path):
        mock_api_cls = MagicMock()
        mock_api = MagicMock()
        mock_api_cls.return_value = mock_api
        mock_module = MagicMock()
        mock_module.HfApi = mock_api_cls

        with patch.dict("sys.modules", {"huggingface_hub": mock_module}):
            url = push_dataset(tmp_path, "user/my-dataset", token="test-token")

        mock_api_cls.assert_called_once_with(token="test-token")
        mock_api.create_repo.assert_called_once()
        mock_api.upload_folder.assert_called_once()
        assert "user/my-dataset" in url


class TestPullDataset:
    def test_import_error_without_hub(self, tmp_path: Path):
        with patch.dict("sys.modules", {"huggingface_hub": None}):
            with pytest.raises(ImportError, match="huggingface-hub"):
                pull_dataset("user/dataset", tmp_path)

    def test_pull_calls_snapshot_download(self, tmp_path: Path):
        mock_module = MagicMock()
        mock_module.snapshot_download.return_value = str(tmp_path / "downloaded")

        with patch.dict("sys.modules", {"huggingface_hub": mock_module}):
            result = pull_dataset("user/my-dataset", tmp_path / "out", token="tok")

        mock_module.snapshot_download.assert_called_once_with(
            repo_id="user/my-dataset",
            repo_type="dataset",
            local_dir=str(tmp_path / "out"),
            token="tok",
            revision=None,
        )
        assert result == tmp_path / "downloaded"
