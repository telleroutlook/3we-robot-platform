# SPDX-License-Identifier: Apache-2.0
"""
Shared platform constants.

Battery thresholds match firmware cell-voltage thresholds in robot_params.h:
  - Pack LOW  = 2 × 3.3V = 6.6V  (approx 25% SOC for typical 2S LiPo)
  - Pack CRIT = 2 × 3.0V = 6.0V  (approx 0% SOC, firmware triggers shutdown)

These are expressed as pack voltage (V) for direct comparison with
BatteryState.voltage from the ROS2 topic. The SDK and diagnostics node
should compare measured voltage against these constants.
"""

BATTERY_CELLS_SERIES: int = 2

BATTERY_CELL_FULL_V: float = 4.2
BATTERY_CELL_NOMINAL_V: float = 3.7
BATTERY_CELL_LOW_V: float = 3.3
BATTERY_CELL_CRITICAL_V: float = 3.0

BATTERY_PACK_FULL_V: float = BATTERY_CELLS_SERIES * BATTERY_CELL_FULL_V
BATTERY_PACK_LOW_V: float = BATTERY_CELLS_SERIES * BATTERY_CELL_LOW_V
BATTERY_PACK_CRITICAL_V: float = BATTERY_CELLS_SERIES * BATTERY_CELL_CRITICAL_V

# Legacy SOC fraction thresholds (derived from voltage curve)
BATTERY_THRESHOLD_LOW: float = 0.25
BATTERY_THRESHOLD_CRITICAL: float = 0.05
