# SPDX-License-Identifier: Apache-2.0
"""
OTA (Over-The-Air) update manager node for Raspberry Pi side.

Listens for update notifications via MQTT topic or ROS2 service,
downloads update packages, verifies integrity (SHA256 signature),
and applies updates for:
  - ROS2 packages (colcon build + systemd restart)
  - AI models (.hef files for Hailo accelerator)
  - System configuration

Configuration via ROS2 parameters:
  - update_check_url: HTTPS endpoint for update manifest
  - model_dir: Directory for AI model files
  - download_dir: Temporary directory for downloads
  - auto_apply: Whether to apply updates automatically (default: false)
  - rollback_enabled: Keep previous version for rollback (default: true)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def _safe_extractall(tar: tarfile.TarFile, path: str) -> None:
    """Extract tar archive safely, guarding against path traversal."""

    if sys.version_info >= (3, 12):
        tar.extractall(path=path, filter="data")
    else:
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name.split("/"):
                raise ValueError(f"Unsafe path in archive: {member.name}")
        tar.extractall(path=path)


class OtaManagerNode(Node):
    """Manages OTA updates for the Raspberry Pi compute module."""

    def __init__(self) -> None:
        super().__init__("ota_manager")

        self.declare_parameter("update_check_url", "")
        self.declare_parameter("model_dir", "/opt/robot/models")
        self.declare_parameter("download_dir", "/tmp/robot_ota")
        self.declare_parameter("auto_apply", False)
        self.declare_parameter("rollback_enabled", True)
        self.declare_parameter("check_interval_sec", 3600.0)
        self.declare_parameter("public_key_path", "/opt/robot/keys/ota_public.pem")

        self._update_check_url = self.get_parameter("update_check_url").value
        self._model_dir = Path(self.get_parameter("model_dir").value)
        self._download_dir = Path(self.get_parameter("download_dir").value)
        self._auto_apply = self.get_parameter("auto_apply").value
        self._rollback_enabled = self.get_parameter("rollback_enabled").value
        self._check_interval = self.get_parameter("check_interval_sec").value
        self._public_key_path = Path(self.get_parameter("public_key_path").value)

        self._current_versions: dict[str, str] = {}
        self._update_in_progress = False

        self._load_current_versions()

        self._status_pub = self.create_publisher(String, "/ota/status", 10)
        self._update_sub = self.create_subscription(
            String, "/ota/trigger", self._on_update_trigger, 10
        )

        if self._update_check_url:
            self._check_timer = self.create_timer(
                self._check_interval, self._periodic_check
            )

        self._publish_status("idle", "OTA manager initialized")
        self.get_logger().info(
            f"OTA manager started (model_dir={self._model_dir}, "
            f"auto_apply={self._auto_apply})"
        )

    def _load_current_versions(self) -> None:
        """Load currently installed versions from manifest file."""
        manifest_path = self._model_dir / "versions.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    self._current_versions = json.load(f)
                self.get_logger().info(
                    f"Loaded version manifest: {self._current_versions}"
                )
            except (json.JSONDecodeError, OSError) as e:
                self.get_logger().warning(f"Failed to load version manifest: {e}")

    def _save_current_versions(self) -> None:
        """Persist the current version manifest."""
        manifest_path = self._model_dir / "versions.json"
        self._model_dir.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(self._current_versions, f, indent=2)

    def _publish_status(self, state: str, message: str) -> None:
        """Publish OTA status update."""
        msg = String()
        msg.data = json.dumps(
            {
                "state": state,
                "message": message,
                "versions": self._current_versions,
            }
        )
        self._status_pub.publish(msg)

    def _on_update_trigger(self, msg: String) -> None:
        """Handle manual update trigger from MQTT bridge or CLI."""
        if self._update_in_progress:
            self.get_logger().warning("Update already in progress, ignoring trigger")
            return

        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError:
            self.get_logger().error("Invalid update trigger payload")
            return

        update_type = payload.get("type", "")
        url = payload.get("url", "")
        expected_sha256 = payload.get("sha256", "")
        version = payload.get("version", "unknown")

        if not url:
            self.get_logger().error("Update trigger missing 'url' field")
            return

        self.get_logger().info(
            f"Update triggered: type={update_type}, version={version}"
        )
        self._apply_update(update_type, url, expected_sha256, version)

    def _periodic_check(self) -> None:
        """Periodically check for available updates."""
        if self._update_in_progress or not self._update_check_url:
            return

        try:
            import urllib.request

            req = urllib.request.Request(
                self._update_check_url,
                headers={"User-Agent": "robot-ota/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                manifest = json.loads(resp.read().decode())
        except Exception as e:
            self.get_logger().debug(f"Update check failed: {e}")
            return

        for update in manifest.get("updates", []):
            component = update.get("component", "")
            available_version = update.get("version", "")
            current = self._current_versions.get(component, "")

            if available_version and available_version != current:
                self.get_logger().info(
                    f"Update available: {component} {current} → {available_version}"
                )
                self._publish_status(
                    "update_available",
                    f"{component}: {current} → {available_version}",
                )

                if self._auto_apply:
                    self._apply_update(
                        update.get("type", component),
                        update["url"],
                        update.get("sha256", ""),
                        available_version,
                    )

    def _apply_update(
        self, update_type: str, url: str, expected_sha256: str, version: str
    ) -> None:
        """Download, verify, and apply an update."""
        self._update_in_progress = True
        self._publish_status("downloading", f"Downloading {update_type} v{version}")

        try:
            local_path = self._download_file(url)
            if not local_path:
                self._publish_status("error", "Download failed")
                return

            if not expected_sha256:
                self._publish_status("error", "SHA256 hash required but not provided")
                self.get_logger().error("OTA rejected: missing sha256 field")
                return

            if not self._verify_sha256(local_path, expected_sha256):
                self._publish_status("error", "SHA256 verification failed")
                os.unlink(local_path)
                return

            if not self._verify_signature(local_path, url):
                self._publish_status("error", "Ed25519 signature verification failed")
                os.unlink(local_path)
                return

            self._publish_status("applying", f"Applying {update_type} v{version}")

            if update_type == "model":
                success = self._apply_model_update(local_path, version)
            elif update_type == "ros2":
                success = self._apply_ros2_update(local_path, version)
            elif update_type == "config":
                success = self._apply_config_update(local_path, version)
            else:
                self.get_logger().error(f"Unknown update type: {update_type}")
                success = False

            if success:
                self._current_versions[update_type] = version
                self._save_current_versions()
                self._publish_status("complete", f"{update_type} updated to v{version}")
                self.get_logger().info(f"Update complete: {update_type} v{version}")
            else:
                self._publish_status("error", f"Failed to apply {update_type} update")

        except Exception as e:
            self.get_logger().error(f"Update failed: {e}")
            self._publish_status("error", str(e))
        finally:
            self._update_in_progress = False

    def _download_file(self, url: str) -> str | None:
        """Download a file from URL to temporary directory."""
        import urllib.request

        self._download_dir.mkdir(parents=True, exist_ok=True)
        local_path = self._download_dir / os.path.basename(url)

        try:
            urllib.request.urlretrieve(url, str(local_path))
            self.get_logger().info(f"Downloaded: {local_path}")
            return str(local_path)
        except Exception as e:
            self.get_logger().error(f"Download failed: {e}")
            return None

    def _verify_sha256(self, file_path: str, expected: str) -> bool:
        """Verify file SHA256 hash."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual = sha256.hexdigest()
        if actual != expected:
            self.get_logger().error(
                f"SHA256 mismatch: expected={expected}, actual={actual}"
            )
            return False
        return True

    def _verify_signature(self, file_path: str, url: str) -> bool:
        """Verify Ed25519 signature of the downloaded file.

        Expects a .sig file alongside the payload (downloaded from url + '.sig').
        The .sig file contains the raw 64-byte Ed25519 signature.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.exceptions import InvalidSignature

        if not self._public_key_path.exists():
            self.get_logger().error(
                f"Public key not found at {self._public_key_path} — "
                "refusing to apply unsigned update"
            )
            return False

        sig_url = url + ".sig"
        sig_path = self._download_file(sig_url)
        if not sig_path:
            self.get_logger().error(
                f"Signature file not found at {sig_url} — "
                "refusing to apply unsigned update"
            )
            return False

        try:
            with open(self._public_key_path, "rb") as kf:
                public_key = load_pem_public_key(kf.read())

            if not isinstance(public_key, Ed25519PublicKey):
                self.get_logger().error("Public key is not Ed25519")
                return False

            with open(sig_path, "rb") as sf:
                signature = sf.read()

            with open(file_path, "rb") as pf:
                payload = pf.read()

            public_key.verify(signature, payload)
            self.get_logger().info("Ed25519 signature verification passed")
            return True

        except InvalidSignature:
            self.get_logger().error(
                "Ed25519 signature verification FAILED — payload may be tampered"
            )
            return False
        except Exception as e:
            self.get_logger().error(f"Signature verification error: {e}")
            return False
        finally:
            if sig_path and os.path.exists(sig_path):
                os.unlink(sig_path)

    def _apply_model_update(self, file_path: str, version: str) -> bool:
        """Apply AI model (.hef) update with rollback support."""
        model_name = Path(file_path).stem
        target = self._model_dir / f"{model_name}.hef"

        if self._rollback_enabled and target.exists():
            backup = self._model_dir / f"{model_name}.hef.prev"
            shutil.copy2(str(target), str(backup))
            self.get_logger().info(f"Backed up previous model to {backup}")

        self._model_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(file_path, str(target))
        self.get_logger().info(f"Model updated: {target}")
        return True

    def _apply_ros2_update(self, file_path: str, version: str) -> bool:
        """Apply ROS2 package update (tar.gz → extract → colcon build → restart)."""
        workspace = Path("/opt/robot/ros2_ws")
        extract_dir = Path(tempfile.mkdtemp(prefix="ros2_update_"))

        try:
            with tarfile.open(file_path, "r:gz") as tar:
                _safe_extractall(tar, str(extract_dir))

            src_dir = extract_dir / "src"
            if not src_dir.exists():
                src_dir = extract_dir

            target_src = workspace / "src"
            target_src.mkdir(parents=True, exist_ok=True)

            for item in src_dir.iterdir():
                dest = target_src / item.name
                if self._rollback_enabled and dest.exists():
                    backup = Path(str(dest) + ".prev")
                    if backup.exists():
                        shutil.rmtree(str(backup))
                    shutil.copytree(str(dest), str(backup))
                if dest.exists():
                    shutil.rmtree(str(dest))
                shutil.copytree(str(item), str(dest))

            result = subprocess.run(
                ["colcon", "build", "--symlink-install"],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                self.get_logger().error(f"colcon build failed: {result.stderr}")
                return False

            subprocess.run(
                ["systemctl", "--user", "restart", "robot.service"],
                capture_output=True,
                timeout=30,
            )
            return True

        except Exception as e:
            self.get_logger().error(f"ROS2 update failed: {e}")
            return False
        finally:
            shutil.rmtree(str(extract_dir), ignore_errors=True)
            if os.path.exists(file_path):
                os.unlink(file_path)

    def _apply_config_update(self, file_path: str, version: str) -> bool:
        """Apply configuration update (YAML files)."""
        config_dir = Path("/opt/robot/config")
        config_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(file_path, "r:gz") as tar:
                _safe_extractall(tar, str(config_dir))
            return True
        except Exception as e:
            self.get_logger().error(f"Config update failed: {e}")
            return False
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)


def main(args=None) -> None:
    """Entry point for ros2 run."""
    rclpy.init(args=args)
    node = OtaManagerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
