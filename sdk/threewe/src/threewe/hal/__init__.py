# SPDX-License-Identifier: Apache-2.0
"""Hardware Abstraction Layer — supports multiple chassis platforms.

The HAL enables the same threewe SDK to control different robot hardware
(3we Standard, AgileX Scout, TurtleBot4, Unitree Go2) by abstracting
wheel geometry, sensor layout, and kinematic limits.
"""

from threewe.hal.interface import HardwareProfile, load_hardware_profile

__all__ = ["HardwareProfile", "load_hardware_profile"]
