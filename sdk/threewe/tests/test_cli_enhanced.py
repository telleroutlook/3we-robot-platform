# SPDX-License-Identifier: Apache-2.0
"""Tests for enhanced CLI (Sprint 20)."""

from __future__ import annotations

import subprocess
import sys


class TestCLITestSubcommand:
    def test_test_sim2real_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "threewe.cli", "test", "sim2real", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--backend" in result.stdout
        assert "--scene" in result.stdout
        assert "--tests" in result.stdout

    def test_test_no_subcommand(self):
        result = subprocess.run(
            [sys.executable, "-m", "threewe.cli", "test"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "sim2real" in result.stdout or "sim2real" in result.stderr

    def test_test_sim2real_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "threewe.cli", "test", "sim2real", "--backend", "gazebo"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "sim2real" in result.stdout.lower() or "transfer" in result.stdout.lower()


class TestCLILaunchIsaac:
    def test_launch_isaac_no_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "threewe.cli", "launch", "--backend", "isaac_sim"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Isaac Sim" in result.stdout

    def test_launch_isaac_with_num_envs(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "threewe.cli",
                "launch",
                "--backend",
                "isaac_sim",
                "--num-envs",
                "16",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "16 envs" in result.stdout


class TestCLIBenchmarkObjectNav:
    def test_benchmark_run_help_includes_objectnav(self):
        result = subprocess.run(
            [sys.executable, "-m", "threewe.cli", "benchmark", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "objectnav" in result.stdout
