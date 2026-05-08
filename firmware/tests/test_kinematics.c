// SPDX-License-Identifier: Apache-2.0
// Unit tests for mecanum kinematics (motor_mecanum_drive)
#include "unity.h"
#include "motor_control.h"
#include "robot_params.h"
#include <math.h>

#define FLOAT_TOLERANCE 0.001f

void test_mecanum_zero_input_gives_zero_output(void)
{
    cmd_vel_t cmd = { .vx = 0.0f, .vy = 0.0f, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, out.speeds[i]);
    }
}

void test_mecanum_pure_forward(void)
{
    cmd_vel_t cmd = { .vx = MAX_LINEAR_VEL, .vy = 0.0f, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    // All wheels should spin forward at full speed
    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, out.speeds[i]);
    }
}

void test_mecanum_pure_backward(void)
{
    cmd_vel_t cmd = { .vx = -MAX_LINEAR_VEL, .vy = 0.0f, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[i]);
    }
}

void test_mecanum_pure_strafe_left(void)
{
    // vy positive = left strafe
    // Mecanum formula: FL = vx - vy, FR = vx + vy, RL = vx + vy, RR = vx - vy
    cmd_vel_t cmd = { .vx = 0.0f, .vy = MAX_LINEAR_VEL, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    // FL and RR should be negative (backward), FR and RL positive (forward)
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_FL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_FR]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_RL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_RR]);
}

void test_mecanum_pure_strafe_right(void)
{
    cmd_vel_t cmd = { .vx = 0.0f, .vy = -MAX_LINEAR_VEL, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_FL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_FR]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_RL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_RR]);
}

void test_mecanum_rotation_ccw(void)
{
    float k = LX + LY;
    cmd_vel_t cmd = { .vx = 0.0f, .vy = 0.0f, .omega = MAX_LINEAR_VEL / k };
    motor_output_t out = motor_mecanum_drive(&cmd);

    // CCW rotation: FL negative, FR positive, RL negative, RR positive
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_FL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_FR]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, -1.0f, out.speeds[MOTOR_RL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE,  1.0f, out.speeds[MOTOR_RR]);
}

void test_mecanum_normalization(void)
{
    // Command exceeding max velocity — should be normalized to [-1, 1]
    cmd_vel_t cmd = { .vx = MAX_LINEAR_VEL * 2.0f, .vy = 0.0f, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, out.speeds[i]);
    }
}

void test_mecanum_half_speed_forward(void)
{
    cmd_vel_t cmd = { .vx = MAX_LINEAR_VEL * 0.5f, .vy = 0.0f, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    for (int i = 0; i < MOTOR_COUNT; i++) {
        TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.5f, out.speeds[i]);
    }
}

void test_mecanum_diagonal_motion(void)
{
    // Forward + left strafe: FL should be 0, FR max, RL max, RR 0
    cmd_vel_t cmd = { .vx = MAX_LINEAR_VEL, .vy = MAX_LINEAR_VEL, .omega = 0.0f };
    motor_output_t out = motor_mecanum_drive(&cmd);

    // raw: FL = vx - vy = 0, FR = vx + vy = 2*max, RL = vx + vy = 2*max, RR = vx - vy = 0
    // After normalization (max_val = 2*max > MAX): scale = MAX/(2*max) = 0.5
    // Speeds: FL = 0, FR = 1.0, RL = 1.0, RR = 0
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, out.speeds[MOTOR_FL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, out.speeds[MOTOR_FR]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 1.0f, out.speeds[MOTOR_RL]);
    TEST_ASSERT_FLOAT_WITHIN(FLOAT_TOLERANCE, 0.0f, out.speeds[MOTOR_RR]);
}
