# SPDX-License-Identifier: Apache-2.0
"""Tests for AI modules: VLMRunner and VLARunner."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from threewe.types import MoveResult, Pose2D


class TestVLMRunner:
    def test_encode_image_rgb(self):
        pytest.importorskip("PIL")
        from threewe.ai.vlm_runner import VLMRunner

        runner = VLMRunner()
        image = np.zeros((64, 64, 3), dtype=np.uint8)
        b64 = runner._encode_image(image)
        assert isinstance(b64, str)
        assert len(b64) > 0

    def test_encode_image_produces_valid_base64(self):
        pytest.importorskip("PIL")
        import base64

        from threewe.ai.vlm_runner import VLMRunner

        runner = VLMRunner()
        image = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
        b64 = runner._encode_image(image)
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0

    def test_plan_calls_openai(self):
        pytest.importorskip("PIL")
        from threewe.ai.vlm_runner import VLMRunner

        runner = VLMRunner(model="gpt-4o", api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {"action": "move_forward", "distance": 0.5, "reason": "path clear"}
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        runner._client = mock_client

        image = np.zeros((64, 64, 3), dtype=np.uint8)
        result = runner.plan(image, "go forward")

        assert "move_forward" in result
        mock_client.chat.completions.create.assert_called_once()

    def test_plan_returns_stop_on_empty_response(self):
        pytest.importorskip("PIL")
        from threewe.ai.vlm_runner import VLMRunner

        runner = VLMRunner()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        runner._client = mock_client

        image = np.zeros((64, 64, 3), dtype=np.uint8)
        result = runner.plan(image, "test")

        parsed = json.loads(result)
        assert parsed["action"] == "stop"


class TestVLMInstructionExecution:
    @pytest.mark.asyncio
    async def test_execute_returns_success_on_done(self):
        pytest.importorskip("PIL")
        from threewe.ai.vlm_runner import execute_vlm_instruction

        mock_robot = MagicMock()
        mock_robot.get_image.return_value = np.zeros((64, 64, 3), dtype=np.uint8)

        with patch("threewe.ai.vlm_runner.VLMRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.plan.return_value = json.dumps({"action": "done", "reason": "arrived"})

            result = await execute_vlm_instruction(mock_robot, "go to the door")

        assert result.success is True
        assert "arrived" in result.description

    @pytest.mark.asyncio
    async def test_execute_stops_at_max_steps(self):
        pytest.importorskip("PIL")

        from threewe.ai.vlm_runner import execute_vlm_instruction

        mock_robot = MagicMock()
        mock_robot.get_image.return_value = np.zeros((64, 64, 3), dtype=np.uint8)
        mock_robot.move_forward = AsyncMock(
            return_value=MoveResult(success=True, final_pose=Pose2D())
        )

        with patch("threewe.ai.vlm_runner.VLMRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.plan.return_value = json.dumps({"action": "move_forward", "distance": 0.3})

            result = await execute_vlm_instruction(mock_robot, "keep going", max_steps=3)

        assert result.success is False
        assert "max steps" in result.description

    @pytest.mark.asyncio
    async def test_execute_handles_json_error_gracefully(self):
        pytest.importorskip("PIL")
        from threewe.ai.vlm_runner import execute_vlm_instruction

        mock_robot = MagicMock()
        mock_robot.get_image.return_value = np.zeros((64, 64, 3), dtype=np.uint8)

        with patch("threewe.ai.vlm_runner.VLMRunner") as MockRunner:
            instance = MockRunner.return_value
            instance.plan.return_value = "not valid json {{{{"

            result = await execute_vlm_instruction(mock_robot, "test", max_steps=2)

        assert result.success is False


class TestVLARunner:
    def test_from_local_raises_on_missing_model(self, tmp_path):
        from threewe.ai.vla_runner import VLARunner

        with pytest.raises(FileNotFoundError, match="No model file found"):
            VLARunner.from_local(str(tmp_path))

    def test_predict_raises_when_model_not_loaded(self):
        from threewe.ai.vla_runner import VLARunner

        runner = VLARunner("/nonexistent")
        with pytest.raises(RuntimeError, match="Model not loaded"):
            runner.predict({"image": np.zeros((64, 64, 3), dtype=np.uint8)})

    def test_predict_onnx(self, tmp_path):
        from threewe.ai.vla_runner import VLARunner

        runner = VLARunner(str(tmp_path))
        runner._config["runtime"] = "onnx"

        mock_session = MagicMock()
        mock_session.run.return_value = [np.array([[0.1, -0.2, 0.3]], dtype=np.float32)]
        runner._model = mock_session

        obs = {"image": np.zeros((64, 64, 3), dtype=np.uint8)}
        action = runner.predict(obs)

        assert action.shape == (3,)
        assert action.dtype == np.float32
        np.testing.assert_allclose(action, [0.1, -0.2, 0.3], atol=1e-6)

    def test_action_dim_default(self, tmp_path):
        from threewe.ai.vla_runner import VLARunner

        runner = VLARunner(str(tmp_path / "test"))
        assert runner.action_dim == 3
