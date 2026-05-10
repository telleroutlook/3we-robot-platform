# SPDX-License-Identifier: Apache-2.0
"""
Shared platform constants.

Battery thresholds are expressed as fractions (0.0–1.0).
Both the SDK client and ROS2 diagnostics node consume these
to ensure consistent state classification across the stack.
"""

BATTERY_THRESHOLD_LOW: float = 0.20
BATTERY_THRESHOLD_CRITICAL: float = 0.10
