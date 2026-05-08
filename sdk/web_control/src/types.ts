// SPDX-License-Identifier: Apache-2.0

/**
 * ROS message types and custom robot platform interfaces.
 */

// --- Standard ROS message types ---

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Quaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

export interface Header {
  stamp: { sec: number; nanosec: number };
  frame_id: string;
}

export interface Twist {
  linear: Vector3;
  angular: Vector3;
}

export interface BatteryState {
  header: Header;
  voltage: number;
  current: number;
  charge: number;
  capacity: number;
  design_capacity: number;
  percentage: number;
  power_supply_status: number;
  power_supply_health: number;
  power_supply_technology: number;
  present: boolean;
}

export interface Range {
  header: Header;
  radiation_type: number;
  field_of_view: number;
  min_range: number;
  max_range: number;
  range: number;
}

export interface Imu {
  header: Header;
  orientation: Quaternion;
  orientation_covariance: number[];
  angular_velocity: Vector3;
  angular_velocity_covariance: number[];
  linear_acceleration: Vector3;
  linear_acceleration_covariance: number[];
}

// --- Custom robot platform types ---

export interface WheelSpeeds {
  header: Header;
  front_left: number;
  front_right: number;
  rear_left: number;
  rear_right: number;
}

export interface PayloadState {
  name: string;
  vendor: string;
  connected: boolean;
  power_5v_active: boolean;
  power_12v_active: boolean;
  power_vbat_active: boolean;
  power_consumption_watts: number;
}

export interface EmergencyStop {
  stopped: boolean;
  reason: string;
}

export interface PayloadPowerRequest {
  rail: 'RAIL_5V' | 'RAIL_12V' | 'RAIL_VBAT';
  enable: boolean;
}

export interface PayloadPowerResponse {
  success: boolean;
  message: string;
}

// --- Connection state ---

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface ConnectionEvent {
  state: ConnectionState;
  url?: string;
  error?: string;
}

// --- Rosbridge protocol types ---

export interface RosbridgeSubscribe {
  op: 'subscribe';
  topic: string;
  type: string;
  id?: string;
}

export interface RosbridgeUnsubscribe {
  op: 'unsubscribe';
  topic: string;
  id?: string;
}

export interface RosbridgePublish {
  op: 'publish';
  topic: string;
  type?: string;
  msg: unknown;
}

export interface RosbridgeCallService {
  op: 'call_service';
  service: string;
  type?: string;
  args?: unknown;
  id?: string;
}

export interface RosbridgeServiceResponse {
  op: 'service_response';
  service: string;
  values: unknown;
  result: boolean;
  id?: string;
}

export interface RosbridgeMessage {
  op: string;
  topic?: string;
  msg?: unknown;
  service?: string;
  values?: unknown;
  result?: boolean;
  id?: string;
}
