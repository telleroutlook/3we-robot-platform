# SPDX-License-Identifier: Apache-2.0
# State machine status for the ball collection demo.
std_msgs/Header header

uint8 IDLE=0
uint8 SEARCHING=1
uint8 APPROACHING=2
uint8 PICKING=3
uint8 RETURNING=4
uint8 DUMPING=5

uint8 state
uint8 balls_in_basket
uint8 total_collected
string error_message
