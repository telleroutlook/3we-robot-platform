# SPDX-License-Identifier: Apache-2.0
"""Hailo-8L NPU inference runner.

Provides an interface for running VLA/VLM models on the Hailo-8L accelerator
commonly paired with Raspberry Pi 5 for edge AI inference.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _ensure_hailo_available() -> Any:
    """Check that the Hailo runtime is installed."""
    try:
        import hailo_platform  # type: ignore[import-not-found]

        return hailo_platform
    except ImportError as e:
        raise ImportError(
            "hailo_platform is required for Hailo-8L inference. "
            "Install the Hailo SDK following: "
            "https://hailo.ai/developer-zone/documentation/\n"
            "On Raspberry Pi 5: sudo apt install hailo-all"
        ) from e


class HailoRunner:
    """Run compiled HEF models on the Hailo-8L NPU.

    HEF (Hailo Executable Format) files are compiled neural networks
    optimized for the Hailo-8L architecture.

    Usage:
        runner = HailoRunner.from_hef("model.hef")
        output = runner.infer({"input": image_array})
    """

    def __init__(self, hef_path: str, device_id: int = 0) -> None:
        self._hef_path = Path(hef_path)
        self._device_id = device_id
        self._device: Any = None
        self._network_group: Any = None
        self._input_vstreams_params: Any = None
        self._output_vstreams_params: Any = None

    @classmethod
    def from_hef(cls, hef_path: str, device_id: int = 0) -> HailoRunner:
        """Load a compiled HEF model for Hailo-8L inference.

        Args:
            hef_path: Path to the .hef model file.
            device_id: Hailo device index (default 0).

        Raises:
            ImportError: If hailo_platform is not installed.
            FileNotFoundError: If HEF file doesn't exist.
        """
        _ensure_hailo_available()

        path = Path(hef_path)
        if not path.exists():
            raise FileNotFoundError(f"HEF model not found: {hef_path}")

        runner = cls(hef_path, device_id)
        runner._initialize()
        return runner

    def _initialize(self) -> None:
        """Initialize the Hailo device and load the network."""
        hailo = _ensure_hailo_available()

        self._device = hailo.Device()
        hef = hailo.Hef(str(self._hef_path))
        self._network_group = self._device.configure(hef)[0]
        self._input_vstreams_params = hailo.InputVStreamParams.make(self._network_group)
        self._output_vstreams_params = hailo.OutputVStreamParams.make(self._network_group)

    def infer(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        """Run inference on the Hailo-8L.

        Args:
            inputs: Dict mapping input layer names to numpy arrays.

        Returns:
            Dict mapping output layer names to result numpy arrays.
        """
        if self._network_group is None:
            raise RuntimeError("Hailo device not initialized. Use from_hef().")

        hailo = _ensure_hailo_available()

        with hailo.InferVStreams(
            self._network_group,
            self._input_vstreams_params,
            self._output_vstreams_params,
        ) as pipeline:
            results = pipeline.infer(inputs)

        return {k: v.astype(np.float32) for k, v in results.items()}

    def get_input_shapes(self) -> dict[str, tuple[int, ...]]:
        """Get expected input shapes for each input layer."""
        if self._network_group is None:
            raise RuntimeError("Hailo device not initialized.")

        hailo = _ensure_hailo_available()
        params = hailo.InputVStreamParams.make(self._network_group)
        return {p.name: tuple(p.shape) for p in params}

    def get_output_shapes(self) -> dict[str, tuple[int, ...]]:
        """Get output shapes for each output layer."""
        if self._network_group is None:
            raise RuntimeError("Hailo device not initialized.")

        hailo = _ensure_hailo_available()
        params = hailo.OutputVStreamParams.make(self._network_group)
        return {p.name: tuple(p.shape) for p in params}

    def close(self) -> None:
        """Release Hailo device resources."""
        self._network_group = None
        self._device = None
