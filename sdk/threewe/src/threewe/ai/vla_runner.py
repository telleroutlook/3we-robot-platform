# SPDX-License-Identifier: Apache-2.0
"""VLA (Vision-Language-Action) model runner.

Supports loading pre-trained VLA models for end-to-end robot control.
Compatible with LeRobot model format and HuggingFace Hub.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class VLARunner:
    """Run VLA models for end-to-end robot control.

    A VLA model takes observations (image + state) and optionally a language
    instruction, and directly outputs action vectors (velocities/joint commands).
    """

    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self._model_path = model_path
        self._device = device
        self._model: Any = None
        self._config: dict = {}
        self._text_encoder: Any = None

    @classmethod
    def from_pretrained(cls, model_id: str, device: str = "cpu") -> VLARunner:
        """Load a VLA model from HuggingFace Hub.

        Args:
            model_id: HuggingFace model identifier (e.g., "lerobot/act_3we_nav")
            device: Target device ("cpu", "cuda", "mps")
        """
        try:
            from huggingface_hub import snapshot_download
        except ImportError as e:
            raise ImportError(
                "huggingface_hub is required to download VLA models. "
                "Install with: pip install huggingface-hub"
            ) from e

        local_dir = snapshot_download(repo_id=model_id)
        return cls._load_from_dir(local_dir, device)

    @classmethod
    def from_local(cls, path: str, device: str = "cpu") -> VLARunner:
        """Load a local VLA model (ONNX, PyTorch, or Hailo HEF).

        Args:
            path: Path to model directory or file
            device: Target device ("cpu", "cuda", "mps", "hailo")
        """
        if device == "hailo":
            return cls._load_hailo(path)
        return cls._load_from_dir(path, device)

    @classmethod
    def _load_from_dir(cls, path: str, device: str) -> VLARunner:
        """Load model from a local directory."""
        model_dir = Path(path)
        runner = cls(str(model_dir), device)

        onnx_path = model_dir / "model.onnx"
        if onnx_path.exists():
            runner._load_onnx(onnx_path)
            return runner

        pt_path = model_dir / "model.pt"
        if not pt_path.exists():
            pt_path = model_dir / "pytorch_model.bin"
        if pt_path.exists():
            runner._load_pytorch(pt_path)
            return runner

        raise FileNotFoundError(
            f"No model file found in {model_dir}. "
            "Expected model.onnx, model.pt, or pytorch_model.bin"
        )

    @classmethod
    def _load_hailo(cls, path: str) -> VLARunner:
        """Load a HEF model for Hailo-8L inference."""
        from threewe.ai.hailo import HailoRunner

        runner = cls(path, "hailo")
        runner._model = HailoRunner.from_hef(path)
        runner._config["runtime"] = "hailo"
        return runner

    def _load_onnx(self, path: Path) -> None:
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise ImportError(
                "onnxruntime is required for ONNX VLA models. Install with: pip install onnxruntime"
            ) from e

        providers = ["CPUExecutionProvider"]
        if self._device == "cuda":
            providers.insert(0, "CUDAExecutionProvider")

        self._model = ort.InferenceSession(str(path), providers=providers)
        self._config["runtime"] = "onnx"

    def _load_pytorch(self, path: Path) -> None:
        try:
            import torch
        except ImportError as e:
            raise ImportError(
                "PyTorch is required for PyTorch VLA models. Install with: pip install torch"
            ) from e

        self._model = torch.load(str(path), map_location=self._device, weights_only=False)
        if hasattr(self._model, "eval"):
            self._model.eval()
        self._config["runtime"] = "pytorch"

    def predict(self, obs: dict[str, np.ndarray], instruction: str = "") -> np.ndarray:
        """Predict action from observation.

        Args:
            obs: Observation dict with keys like "image", "state", "lidar"
            instruction: Optional language instruction for conditioned policies

        Returns:
            Action vector as numpy array. Shape depends on model
            (typically (3,) for [vx, vy, omega] or (7,) for arm joints).
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Use from_pretrained() or from_local().")

        runtime = self._config.get("runtime", "")

        if runtime == "onnx":
            return self._predict_onnx(obs, instruction)
        elif runtime == "pytorch":
            return self._predict_pytorch(obs, instruction)
        elif runtime == "hailo":
            return self._predict_hailo(obs, instruction)
        else:
            raise RuntimeError(f"Unknown runtime: {runtime}")

    def _encode_instruction(self, instruction: str) -> np.ndarray:
        """Encode a language instruction into a fixed-size embedding."""
        if self._text_encoder is None:
            from threewe.ai.text_encoder import TextEncoder

            self._text_encoder = TextEncoder(method="tfidf", dim=64)
        return self._text_encoder.encode(instruction)

    def _predict_onnx(self, obs: dict[str, np.ndarray], instruction: str) -> np.ndarray:
        feed = {}
        for key, value in obs.items():
            if isinstance(value, np.ndarray):
                if value.ndim == 3:
                    feed[key] = value[np.newaxis].astype(np.float32) / 255.0
                else:
                    feed[key] = value[np.newaxis].astype(np.float32)

        if instruction:
            feed["instruction_embedding"] = self._encode_instruction(instruction)[
                np.newaxis
            ].astype(np.float32)

        outputs = self._model.run(None, feed)
        return outputs[0][0].astype(np.float32)

    def _predict_pytorch(self, obs: dict[str, np.ndarray], instruction: str) -> np.ndarray:
        import torch

        with torch.no_grad():
            tensors = {}
            for key, value in obs.items():
                if isinstance(value, np.ndarray):
                    t = torch.from_numpy(value).float().to(self._device)
                    if t.ndim == 3:
                        t = t.permute(2, 0, 1).unsqueeze(0) / 255.0
                    else:
                        t = t.unsqueeze(0)
                    tensors[key] = t

            if hasattr(self._model, "forward"):
                output = self._model(**tensors)
            else:
                output = self._model(tensors)

            if isinstance(output, torch.Tensor):
                return output[0].cpu().numpy().astype(np.float32)
            return np.zeros(3, dtype=np.float32)

    @property
    def action_dim(self) -> int:
        """Expected output action dimension."""
        return self._config.get("action_dim", 3)

    def _predict_hailo(self, obs: dict[str, np.ndarray], instruction: str) -> np.ndarray:
        """Run inference on Hailo-8L NPU."""
        feed = {}
        for key, value in obs.items():
            if isinstance(value, np.ndarray):
                if value.ndim == 3:
                    feed[key] = (value.astype(np.float32) / 255.0)[np.newaxis]
                else:
                    feed[key] = value[np.newaxis].astype(np.float32)

        if instruction:
            feed["instruction_embedding"] = self._encode_instruction(instruction)[
                np.newaxis
            ].astype(np.float32)

        results = self._model.infer(feed)
        first_output = next(iter(results.values()))
        return first_output[0].astype(np.float32)
