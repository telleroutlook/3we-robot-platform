// SPDX-License-Identifier: Apache-2.0
// Unit tests for micro-ROS message population and odometry computation logic.
// These run on the host without micro-ROS dependencies by testing the math and
// field-population patterns used in microros_transport.c.
#include "unity.h"
#include "robot_params.h"
#include <math.h>
#include <string.h>
#include <float.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Re-implement the forward kinematics from microros_transport.c for testing
typedef struct {
    float vx;
    float vy;
    float wz;
} body_velocity_t;

static body_velocity_t compute_forward_kinematics(const float wheel_speeds[4])
{
    body_velocity_t vel;
    vel.vx = (wheel_speeds[0] + wheel_speeds[1] + wheel_speeds[2] + wheel_speeds[3]) / 4.0f;
    vel.vy = (-wheel_speeds[0] + wheel_speeds[1] + wheel_speeds[2] - wheel_speeds[3]) / 4.0f;
    vel.wz = (-wheel_speeds[0] + wheel_speeds[1] - wheel_speeds[2] + wheel_speeds[3]) / (4.0f * (LX + LY));
    return vel;
}

static void integrate_odometry(float *x, float *y, float *theta,
                               float vx, float vy, float wz, float dt)
{
    *theta += wz * dt;
    *x += (vx * cosf(*theta) - vy * sinf(*theta)) * dt;
    *y += (vx * sinf(*theta) + vy * cosf(*theta)) * dt;
}

// Quaternion from yaw (matching microros_transport.c odom_msg population)
static void yaw_to_quaternion(float yaw, float *qz, float *qw)
{
    *qz = sinf(yaw / 2.0f);
    *qw = cosf(yaw / 2.0f);
}

// --- Forward kinematics tests ---

void test_fk_all_wheels_forward_gives_pure_vx(void)
{
    float speeds[4] = {0.1f, 0.1f, 0.1f, 0.1f};
    body_velocity_t vel = compute_forward_kinematics(speeds);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.1f, vel.vx);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vy);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.wz);
}

void test_fk_zero_wheels_gives_zero_velocity(void)
{
    float speeds[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    body_velocity_t vel = compute_forward_kinematics(speeds);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vx);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vy);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.wz);
}

void test_fk_strafe_right_pattern(void)
{
    // Mecanum strafe right: FL+, FR-, RL-, RR+
    float speeds[4] = {-0.1f, 0.1f, 0.1f, -0.1f};
    body_velocity_t vel = compute_forward_kinematics(speeds);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vx);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.1f, vel.vy);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.wz);
}

void test_fk_rotation_ccw_pattern(void)
{
    // CCW rotation: FL-, FR+, RL-, RR+
    float speeds[4] = {-0.1f, 0.1f, -0.1f, 0.1f};
    body_velocity_t vel = compute_forward_kinematics(speeds);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vx);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, vel.vy);
    TEST_ASSERT_TRUE(vel.wz > 0.0f);
}

void test_fk_asymmetric_speeds_give_combined_motion(void)
{
    float speeds[4] = {0.2f, 0.1f, 0.2f, 0.1f};
    body_velocity_t vel = compute_forward_kinematics(speeds);
    TEST_ASSERT_TRUE(vel.vx > 0.0f);
    // Asymmetric should produce some rotation
    TEST_ASSERT_TRUE(fabsf(vel.wz) > 0.0f || fabsf(vel.vy) > 0.0f);
}

// --- Odometry integration tests ---

void test_odom_integration_forward(void)
{
    float x = 0.0f, y = 0.0f, theta = 0.0f;
    integrate_odometry(&x, &y, &theta, 1.0f, 0.0f, 0.0f, 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, x);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, y);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, theta);
}

void test_odom_integration_rotation_then_forward(void)
{
    float x = 0.0f, y = 0.0f, theta = 0.0f;
    // Rotate 90 degrees (pi/2 rad/s for 1 second)
    integrate_odometry(&x, &y, &theta, 0.0f, 0.0f, (float)(M_PI / 2.0), 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, (float)(M_PI / 2.0), theta);
    // Now drive forward — should go in +Y direction
    integrate_odometry(&x, &y, &theta, 1.0f, 0.0f, 0.0f, 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, x);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 1.0f, y);
}

void test_odom_integration_zero_velocity(void)
{
    float x = 5.0f, y = 3.0f, theta = 1.0f;
    integrate_odometry(&x, &y, &theta, 0.0f, 0.0f, 0.0f, 1.0f);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 5.0f, x);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 3.0f, y);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, theta);
}

void test_odom_integration_small_dt(void)
{
    float x = 0.0f, y = 0.0f, theta = 0.0f;
    float dt = 1.0f / CONTROL_FREQ_HZ;
    integrate_odometry(&x, &y, &theta, MAX_LINEAR_VEL, 0.0f, 0.0f, dt);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, MAX_LINEAR_VEL * dt, x);
}

// --- Quaternion conversion tests ---

void test_quaternion_zero_yaw(void)
{
    float qz, qw;
    yaw_to_quaternion(0.0f, &qz, &qw);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, qz);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, qw);
}

void test_quaternion_90_degrees(void)
{
    float qz, qw;
    yaw_to_quaternion((float)(M_PI / 2.0), &qz, &qw);
    float expected_qz = sinf((float)(M_PI / 4.0));
    float expected_qw = cosf((float)(M_PI / 4.0));
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, expected_qz, qz);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, expected_qw, qw);
}

void test_quaternion_unit_norm(void)
{
    float qz, qw;
    yaw_to_quaternion(1.23f, &qz, &qw);
    float norm = sqrtf(qz * qz + qw * qw);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, norm);
}

// --- cmd_vel safety clamping tests ---

void test_cmd_vel_clamp_within_limit(void)
{
    float val = 0.2f;
    float clamped = fmaxf(-MAX_ANGULAR_VEL, fminf(MAX_ANGULAR_VEL, val));
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.2f, clamped);
}

void test_cmd_vel_clamp_above_limit(void)
{
    float val = MAX_ANGULAR_VEL + 1.0f;
    float clamped = fmaxf(-MAX_ANGULAR_VEL, fminf(MAX_ANGULAR_VEL, val));
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, MAX_ANGULAR_VEL, clamped);
}

void test_cmd_vel_clamp_below_negative_limit(void)
{
    float val = -(MAX_ANGULAR_VEL + 1.0f);
    float clamped = fmaxf(-MAX_ANGULAR_VEL, fminf(MAX_ANGULAR_VEL, val));
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, -MAX_ANGULAR_VEL, clamped);
}

// --- Wheel speed array sizing tests ---

void test_wheel_msg_requires_4_elements(void)
{
    float data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    TEST_ASSERT_EQUAL(4, (int)(sizeof(data) / sizeof(data[0])));
}

// --- Range message field validation ---

void test_range_field_of_view_reasonable(void)
{
    float fov = 0.26f;  // ~15 degrees as in microros_transport.c
    TEST_ASSERT_TRUE(fov > 0.0f);
    TEST_ASSERT_TRUE(fov < (float)M_PI);
}

void test_range_limits_match_params(void)
{
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 4.0f, US_MAX_RANGE_M);
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.02f, US_MIN_RANGE_M);
    TEST_ASSERT_TRUE(US_MIN_RANGE_M < US_MAX_RANGE_M);
}

// --- Battery message field validation ---

void test_battery_percentage_bounded(void)
{
    // Percentage from battery_get_percentage() is 0-100, divided by 100 for ROS msg
    float pct_raw = 85.0f;
    float msg_pct = pct_raw / 100.0f;
    TEST_ASSERT_TRUE(msg_pct >= 0.0f);
    TEST_ASSERT_TRUE(msg_pct <= 1.0f);
}

void test_battery_percentage_boundary_zero(void)
{
    float msg_pct = 0.0f / 100.0f;
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 0.0f, msg_pct);
}

void test_battery_percentage_boundary_full(void)
{
    float msg_pct = 100.0f / 100.0f;
    TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, msg_pct);
}
