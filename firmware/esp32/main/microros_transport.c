// SPDX-License-Identifier: Apache-2.0
#include "microros_transport.h"
#include "motor_control.h"
#include "encoder.h"
#include "ultrasonic.h"
#include "imu.h"
#include "battery.h"
#include "safety.h"
#include "pin_definitions.h"
#include "robot_params.h"

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <nav_msgs/msg/odometry.h>
#include <geometry_msgs/msg/twist.h>
#include <sensor_msgs/msg/range.h>
#include <sensor_msgs/msg/battery_state.h>
#include <std_msgs/msg/float32_multi_array.h>

#include <micro_ros_utilities/type_utilities.h>
#include <micro_ros_utilities/string_utilities.h>

#include "esp_log.h"
#include <math.h>

static const char *TAG = "uros";

static rcl_allocator_t allocator;
static rclc_support_t support;
static rcl_node_t node;
static rclc_executor_t executor;

// Publishers
static rcl_publisher_t odom_pub;
static rcl_publisher_t range_pub[US_COUNT];
static rcl_publisher_t battery_pub;
static rcl_publisher_t wheel_speed_pub;

// Subscribers
static rcl_subscription_t cmd_vel_sub;

// Messages
static nav_msgs__msg__Odometry odom_msg;
static geometry_msgs__msg__Twist cmd_vel_msg;
static sensor_msgs__msg__Range range_msg;
static sensor_msgs__msg__BatteryState battery_msg;
static std_msgs__msg__Float32MultiArray wheel_msg;

// Timers
static rcl_timer_t odom_timer;
static rcl_timer_t range_timer;
static rcl_timer_t battery_timer;

// Odometry state
static float odom_x = 0.0f;
static float odom_y = 0.0f;
static float odom_theta = 0.0f;
static int64_t last_cmd_vel_time = 0;

static void cmd_vel_callback(const void *msg_in)
{
    const geometry_msgs__msg__Twist *msg = (const geometry_msgs__msg__Twist *)msg_in;

    if (safety_is_estopped()) return;

    cmd_vel_t cmd = {
        .vx = safety_clamp_speed((float)msg->linear.x),
        .vy = safety_clamp_speed((float)msg->linear.y),
        .omega = fmaxf(-MAX_ANGULAR_VEL, fminf(MAX_ANGULAR_VEL, (float)msg->angular.z)),
    };
    motor_mecanum_drive(&cmd);
    last_cmd_vel_time = esp_timer_get_time();
    safety_feed_watchdog();
}

static void odom_timer_callback(rcl_timer_t *timer, int64_t last_call_time)
{
    (void)timer; (void)last_call_time;

    // Check cmd_vel timeout
    int64_t elapsed = esp_timer_get_time() - last_cmd_vel_time;
    if (last_cmd_vel_time > 0 && elapsed > (CMD_VEL_TIMEOUT_MS * 1000LL)) {
        motor_stop_all();
    }

    encoder_update();

    // Compute wheel linear velocities
    float v[MOTOR_COUNT];
    for (int i = 0; i < MOTOR_COUNT; i++) {
        v[i] = encoder_get_speed_rps((motor_id_t)i) * 2.0f * M_PI * WHEEL_RADIUS;
    }

    // Forward kinematics (mecanum)
    float vx = (v[0] + v[1] + v[2] + v[3]) / 4.0f;
    float vy = (-v[0] + v[1] + v[2] - v[3]) / 4.0f;
    float wz = (-v[0] + v[1] - v[2] + v[3]) / (4.0f * (LX + LY));

    // Fuse with IMU yaw if available
    euler_t euler;
    if (imu_read_euler(&euler) == ESP_OK) {
        odom_theta = euler.yaw;
    } else {
        odom_theta += wz * (1.0f / CONTROL_FREQ_HZ);
    }

    // Integrate position
    float dt = 1.0f / CONTROL_FREQ_HZ;
    odom_x += (vx * cosf(odom_theta) - vy * sinf(odom_theta)) * dt;
    odom_y += (vx * sinf(odom_theta) + vy * cosf(odom_theta)) * dt;

    // Populate odometry message
    odom_msg.pose.pose.position.x = odom_x;
    odom_msg.pose.pose.position.y = odom_y;
    odom_msg.pose.pose.orientation.z = sinf(odom_theta / 2.0f);
    odom_msg.pose.pose.orientation.w = cosf(odom_theta / 2.0f);
    odom_msg.twist.twist.linear.x = vx;
    odom_msg.twist.twist.linear.y = vy;
    odom_msg.twist.twist.angular.z = wz;

    rcl_publish(&odom_pub, &odom_msg, NULL);

    // Publish wheel speeds
    if (wheel_msg.data.data) {
        wheel_msg.data.data[0] = v[0];
        wheel_msg.data.data[1] = v[1];
        wheel_msg.data.data[2] = v[2];
        wheel_msg.data.data[3] = v[3];
        rcl_publish(&wheel_speed_pub, &wheel_msg, NULL);
    }
}

static void range_timer_callback(rcl_timer_t *timer, int64_t last_call_time)
{
    (void)timer; (void)last_call_time;

    static const char *frame_ids[] = {
        "ultrasonic_front", "ultrasonic_back",
        "ultrasonic_left", "ultrasonic_right"
    };

    for (int i = 0; i < US_COUNT; i++) {
        range_msg.radiation_type = sensor_msgs__msg__Range__ULTRASOUND;
        range_msg.field_of_view = 0.26f;  // ~15 degrees
        range_msg.min_range = US_MIN_RANGE_M;
        range_msg.max_range = US_MAX_RANGE_M;
        range_msg.range = ultrasonic_get_last((ultrasonic_id_t)i);
        range_msg.header.frame_id.data = (char *)frame_ids[i];
        range_msg.header.frame_id.size = strlen(frame_ids[i]);

        rcl_publish(&range_pub[i], &range_msg, NULL);
    }
}

static void battery_timer_callback(rcl_timer_t *timer, int64_t last_call_time)
{
    (void)timer; (void)last_call_time;

    battery_msg.voltage = battery_read_voltage();
    battery_msg.percentage = battery_get_percentage() / 100.0f;
    battery_msg.present = true;

    switch (battery_get_state()) {
        case BATT_OK:       battery_msg.power_supply_status = 2; break; // DISCHARGING
        case BATT_LOW:      battery_msg.power_supply_status = 2; break;
        case BATT_CRITICAL: battery_msg.power_supply_status = 4; break; // NOT_CHARGING
    }

    rcl_publish(&battery_pub, &battery_msg, NULL);
}

esp_err_t microros_init(void)
{
    allocator = rcl_get_default_allocator();

    // Transport initialization is handled by micro_ros_espidf_component
    // (configured via menuconfig or idf_component.yml)
    rcl_init_options_t init_options = rcl_get_zero_initialized_init_options();
    rcl_init_options_init(&init_options, allocator);

    rclc_support_init_with_options(&support, 0, NULL, &init_options, &allocator);
    rclc_node_init_default(&node, "robot_base", "", &support);

    // Publishers
    rclc_publisher_init_default(&odom_pub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry), "/odom");
    rclc_publisher_init_default(&wheel_speed_pub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Float32MultiArray), "/wheel_speeds");
    rclc_publisher_init_default(&battery_pub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, BatteryState), "/battery_state");

    const char *range_topics[] = {
        "/ultrasonic/front", "/ultrasonic/back",
        "/ultrasonic/left", "/ultrasonic/right"
    };
    for (int i = 0; i < US_COUNT; i++) {
        rclc_publisher_init_default(&range_pub[i], &node,
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, Range), range_topics[i]);
    }

    // Subscriber
    rclc_subscription_init_default(&cmd_vel_sub, &node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist), "/cmd_vel");

    // Timers
    rclc_timer_init_default(&odom_timer, &support,
        RCL_MS_TO_NS(1000 / ODOM_PUBLISH_HZ), odom_timer_callback);
    rclc_timer_init_default(&range_timer, &support,
        RCL_MS_TO_NS(1000 / ULTRASONIC_PUBLISH_HZ), range_timer_callback);
    rclc_timer_init_default(&battery_timer, &support,
        RCL_MS_TO_NS(1000 / BATTERY_PUBLISH_HZ), battery_timer_callback);

    // Executor
    rclc_executor_init(&executor, &support.context, 5, &allocator);
    rclc_executor_add_subscription(&executor, &cmd_vel_sub, &cmd_vel_msg,
        &cmd_vel_callback, ON_NEW_DATA);
    rclc_executor_add_timer(&executor, &odom_timer);
    rclc_executor_add_timer(&executor, &range_timer);
    rclc_executor_add_timer(&executor, &battery_timer);

    // Allocate wheel speed array
    wheel_msg.data.capacity = 4;
    wheel_msg.data.size = 4;
    wheel_msg.data.data = (float *)allocator.allocate(4 * sizeof(float), allocator.state);

    ESP_LOGI(TAG, "micro-ROS initialized (UART %d baud)", UROS_BAUD);
    return ESP_OK;
}

void microros_task(void *params)
{
    while (1) {
        rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
