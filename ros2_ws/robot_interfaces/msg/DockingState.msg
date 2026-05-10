# SPDX-License-Identifier: Apache-2.0
# Docking state message — published by the docking controller

uint8 IDLE=0
uint8 APPROACH=1
uint8 VISUAL_SERVO_COARSE=2
uint8 VISUAL_SERVO_FINE=3
uint8 CONTACT_VERIFY=4
uint8 DOCKED=5
uint8 UNDOCKING=6
uint8 FAILED=7

uint8 stage
float32 progress            # 0.0-1.0 overall progress estimate
string error_message        # Non-empty when stage==FAILED
float64 distance_to_dock    # Meters (from visual estimate), -1 if unknown
