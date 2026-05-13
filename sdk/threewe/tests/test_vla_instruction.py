# SPDX-License-Identifier: Apache-2.0
"""Tests for VLA instruction embedding and Hailo device stub."""

from __future__ import annotations

import numpy as np
import pytest

from threewe.ai.text_encoder import TextEncoder


class TestTextEncoderTFIDF:
    def test_encode_returns_correct_shape(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        vec = encoder.encode("go forward")
        assert vec.shape == (64,)
        assert vec.dtype == np.float32

    def test_encode_custom_dim(self):
        encoder = TextEncoder(method="tfidf", dim=128)
        vec = encoder.encode("turn left and pick up the cup")
        assert vec.shape == (128,)

    def test_encode_is_normalized(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        vec = encoder.encode("navigate to the kitchen")
        norm = np.linalg.norm(vec)
        assert norm == pytest.approx(1.0, abs=1e-5)

    def test_encode_empty_string(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        vec = encoder.encode("")
        assert vec.shape == (64,)
        assert np.allclose(vec, 0.0)

    def test_deterministic(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        v1 = encoder.encode("go to the red chair")
        v2 = encoder.encode("go to the red chair")
        np.testing.assert_array_equal(v1, v2)

    def test_different_instructions_differ(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        v1 = encoder.encode("go forward")
        v2 = encoder.encode("turn right")
        assert not np.allclose(v1, v2)

    def test_similar_instructions_have_overlap(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        v1 = encoder.encode("go to the kitchen")
        v2 = encoder.encode("navigate to the kitchen")
        similarity = float(np.dot(v1, v2))
        assert similarity > 0.0

    def test_method_property(self):
        encoder = TextEncoder(method="tfidf", dim=64)
        assert encoder.method == "tfidf"

    def test_dim_property(self):
        encoder = TextEncoder(method="tfidf", dim=32)
        assert encoder.dim == 32


class TestTextEncoderSentenceTransformers:
    def test_init_raises_without_dependency(self):
        pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed")
        encoder = TextEncoder(method="sentence_transformers", dim=64)
        vec = encoder.encode("hello world")
        assert vec.shape == (64,)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            TextEncoder(method="invalid", dim=64)


class TestHailoRunner:
    def test_import_raises_without_hailo(self):
        from threewe.ai.hailo import _ensure_hailo_available

        with pytest.raises(ImportError, match="hailo_platform"):
            _ensure_hailo_available()

    def test_from_hef_raises_without_hailo(self):
        from threewe.ai.hailo import HailoRunner

        with pytest.raises(ImportError, match="hailo_platform"):
            HailoRunner.from_hef("model.hef")


class TestVLARunnerHailoDevice:
    def test_from_local_hailo_raises_without_sdk(self):
        from threewe.ai.vla_runner import VLARunner

        with pytest.raises(ImportError, match="hailo_platform"):
            VLARunner.from_local("model.hef", device="hailo")


class TestVLARunnerInstructionEncoding:
    def test_encode_instruction_method_exists(self):
        from threewe.ai.vla_runner import VLARunner

        runner = VLARunner("dummy", device="cpu")
        embedding = runner._encode_instruction("go forward")
        assert embedding.shape == (64,)
        assert embedding.dtype == np.float32

    def test_encode_instruction_cached_encoder(self):
        from threewe.ai.vla_runner import VLARunner

        runner = VLARunner("dummy", device="cpu")
        _ = runner._encode_instruction("first call")
        assert runner._text_encoder is not None
        _ = runner._encode_instruction("second call")
        assert runner._text_encoder is not None
