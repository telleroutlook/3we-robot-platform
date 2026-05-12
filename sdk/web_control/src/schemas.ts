// SPDX-License-Identifier: Apache-2.0

import { z } from 'zod';

// --- Rosbridge protocol envelope schemas ---

const rosbridgePublishSchema = z.object({
  op: z.literal('publish'),
  topic: z.string().min(1),
  msg: z.unknown(),
});

const rosbridgeServiceResponseSchema = z.object({
  op: z.literal('service_response'),
  service: z.string().min(1),
  values: z.unknown(),
  result: z.boolean(),
  id: z.string().optional(),
});

const rosbridgePongSchema = z.object({
  op: z.literal('pong'),
});

export const rosbridgeMessageSchema = z.discriminatedUnion('op', [
  rosbridgePublishSchema,
  rosbridgeServiceResponseSchema,
  rosbridgePongSchema,
]);

export type ValidatedPublish = z.infer<typeof rosbridgePublishSchema>;
export type ValidatedServiceResponse = z.infer<typeof rosbridgeServiceResponseSchema>;
export type ValidatedMessage = z.infer<typeof rosbridgeMessageSchema>;

// --- ROS message payload schemas ---

export const headerSchema = z.object({
  stamp: z.object({ sec: z.number(), nanosec: z.number() }),
  frame_id: z.string(),
});

export const vector3Schema = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
});

export const quaternionSchema = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
  w: z.number(),
});

export const twistSchema = z.object({
  linear: vector3Schema,
  angular: vector3Schema,
});

export const batteryStateSchema = z.object({
  header: headerSchema,
  voltage: z.number(),
  current: z.number(),
  charge: z.number(),
  capacity: z.number(),
  design_capacity: z.number(),
  percentage: z.number().min(0).max(1),
  power_supply_status: z.number(),
  power_supply_health: z.number(),
  power_supply_technology: z.number(),
  present: z.boolean(),
});

export const rangeSchema = z.object({
  header: headerSchema,
  radiation_type: z.number(),
  field_of_view: z.number(),
  min_range: z.number(),
  max_range: z.number(),
  range: z.number(),
});

export const imuSchema = z.object({
  header: headerSchema,
  orientation: quaternionSchema,
  orientation_covariance: z.array(z.number()),
  angular_velocity: vector3Schema,
  angular_velocity_covariance: z.array(z.number()),
  linear_acceleration: vector3Schema,
  linear_acceleration_covariance: z.array(z.number()),
});

export const wheelSpeedsSchema = z.object({
  header: headerSchema,
  front_left: z.number(),
  front_right: z.number(),
  rear_left: z.number(),
  rear_right: z.number(),
});

export const payloadStateSchema = z.object({
  header: headerSchema,
  payload_id: z.string(),
  name: z.string(),
  connected: z.boolean(),
  power_5v_active: z.boolean(),
  power_12v_active: z.boolean(),
  power_vbat_active: z.boolean(),
  current_5v: z.number(),
  current_12v: z.number(),
  power_consumption_watts: z.number(),
  status: z.number(),
});

export const emergencyStopStateSchema = z.object({
  header: headerSchema,
  stopped: z.boolean(),
  state: z.number(),
  reason: z.string(),
});

export const payloadPowerResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export const emergencyStopResponseSchema = z.object({
  success: z.boolean(),
  current_state: z.number(),
  message: z.string(),
});

export const collectionStateSchema = z.object({
  header: headerSchema,
  state: z.number().int().min(0).max(5),
  balls_in_basket: z.number().int().min(0),
  total_collected: z.number().int().min(0),
  error_message: z.string(),
});
