// SPDX-License-Identifier: Apache-2.0

import { describe, it, expect } from 'vitest';
import {
  rosbridgeMessageSchema,
  batteryStateSchema,
  rangeSchema,
  imuSchema,
  wheelSpeedsSchema,
  payloadStateSchema,
  emergencyStopStateSchema,
  twistSchema,
  headerSchema,
} from './schemas';

describe('rosbridgeMessageSchema', () => {
  describe('publish messages', () => {
    it('validates a well-formed publish message', () => {
      const msg = { op: 'publish', topic: '/cmd_vel', msg: { linear: { x: 1 } } };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.op).toBe('publish');
      }
    });

    it('rejects publish with empty topic', () => {
      const msg = { op: 'publish', topic: '', msg: {} };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });

    it('rejects publish missing topic field', () => {
      const msg = { op: 'publish', msg: {} };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });

    it('accepts publish with null msg value', () => {
      const msg = { op: 'publish', topic: '/status', msg: null };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(true);
    });
  });

  describe('service_response messages', () => {
    it('validates a successful service response', () => {
      const msg = {
        op: 'service_response',
        service: '/set_power',
        values: { success: true },
        result: true,
        id: 'svc_1',
      };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(true);
    });

    it('validates a failed service response', () => {
      const msg = {
        op: 'service_response',
        service: '/set_power',
        values: { error: 'timeout' },
        result: false,
      };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(true);
    });

    it('rejects service_response with empty service name', () => {
      const msg = {
        op: 'service_response',
        service: '',
        values: {},
        result: true,
      };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });

    it('rejects service_response without result boolean', () => {
      const msg = {
        op: 'service_response',
        service: '/test',
        values: {},
      };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });
  });

  describe('pong messages', () => {
    it('validates a pong message', () => {
      const msg = { op: 'pong' };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(true);
    });
  });

  describe('invalid messages', () => {
    it('rejects unknown op types', () => {
      const msg = { op: 'unknown_op', data: 'test' };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });

    it('rejects non-object input', () => {
      expect(rosbridgeMessageSchema.safeParse('string').success).toBe(false);
      expect(rosbridgeMessageSchema.safeParse(42).success).toBe(false);
      expect(rosbridgeMessageSchema.safeParse(null).success).toBe(false);
    });

    it('rejects object without op field', () => {
      const msg = { topic: '/test', msg: {} };
      const result = rosbridgeMessageSchema.safeParse(msg);
      expect(result.success).toBe(false);
    });
  });
});

const validHeader = { stamp: { sec: 100, nanosec: 500 }, frame_id: 'base_link' };

describe('headerSchema', () => {
  it('validates a well-formed header', () => {
    expect(headerSchema.safeParse(validHeader).success).toBe(true);
  });

  it('rejects header with missing stamp fields', () => {
    expect(headerSchema.safeParse({ stamp: { sec: 1 }, frame_id: '' }).success).toBe(false);
  });

  it('rejects header without frame_id', () => {
    expect(headerSchema.safeParse({ stamp: { sec: 1, nanosec: 0 } }).success).toBe(false);
  });
});

describe('batteryStateSchema', () => {
  const validBattery = {
    header: validHeader,
    voltage: 12.6,
    current: 1.2,
    charge: 4.0,
    capacity: 5.0,
    design_capacity: 5.2,
    percentage: 0.8,
    power_supply_status: 2,
    power_supply_health: 1,
    power_supply_technology: 3,
    present: true,
  };

  it('validates a complete BatteryState message', () => {
    expect(batteryStateSchema.safeParse(validBattery).success).toBe(true);
  });

  it('rejects BatteryState with missing percentage', () => {
    const { percentage: _percentage, ...incomplete } = validBattery;
    void _percentage;
    expect(batteryStateSchema.safeParse(incomplete).success).toBe(false);
  });

  it('rejects BatteryState with non-boolean present', () => {
    expect(batteryStateSchema.safeParse({ ...validBattery, present: 1 }).success).toBe(false);
  });
});

describe('rangeSchema', () => {
  const validRange = {
    header: validHeader,
    radiation_type: 0,
    field_of_view: 0.44,
    min_range: 0.02,
    max_range: 4.0,
    range: 1.5,
  };

  it('validates a complete Range message', () => {
    expect(rangeSchema.safeParse(validRange).success).toBe(true);
  });

  it('rejects Range with string range value', () => {
    expect(rangeSchema.safeParse({ ...validRange, range: 'far' }).success).toBe(false);
  });
});

describe('imuSchema', () => {
  const validImu = {
    header: validHeader,
    orientation: { x: 0, y: 0, z: 0, w: 1 },
    orientation_covariance: Array(9).fill(0),
    angular_velocity: { x: 0, y: 0, z: 0 },
    angular_velocity_covariance: Array(9).fill(0),
    linear_acceleration: { x: 0, y: 0, z: 9.81 },
    linear_acceleration_covariance: Array(9).fill(0),
  };

  it('validates a complete Imu message', () => {
    expect(imuSchema.safeParse(validImu).success).toBe(true);
  });

  it('rejects Imu with missing orientation.w', () => {
    const bad = { ...validImu, orientation: { x: 0, y: 0, z: 0 } };
    expect(imuSchema.safeParse(bad).success).toBe(false);
  });

  it('rejects Imu with non-array covariance', () => {
    const bad = { ...validImu, orientation_covariance: 'none' };
    expect(imuSchema.safeParse(bad).success).toBe(false);
  });
});

describe('wheelSpeedsSchema', () => {
  const validWheels = {
    header: validHeader,
    front_left: 1.0,
    front_right: 1.0,
    rear_left: 0.9,
    rear_right: 0.9,
  };

  it('validates a complete WheelSpeeds message', () => {
    expect(wheelSpeedsSchema.safeParse(validWheels).success).toBe(true);
  });

  it('rejects WheelSpeeds with missing wheel', () => {
    const { rear_right: _rear_right, ...bad } = validWheels;
    void _rear_right;
    expect(wheelSpeedsSchema.safeParse(bad).success).toBe(false);
  });
});

describe('payloadStateSchema', () => {
  const validPayload = {
    header: validHeader,
    payload_id: 'PL001',
    name: 'Lidar',
    connected: true,
    power_5v_active: true,
    power_12v_active: false,
    power_vbat_active: false,
    current_5v: 0.3,
    current_12v: 0.0,
    power_consumption_watts: 1.5,
    status: 0,
  };

  it('validates a complete PayloadState message', () => {
    expect(payloadStateSchema.safeParse(validPayload).success).toBe(true);
  });

  it('rejects PayloadState with non-string payload_id', () => {
    expect(payloadStateSchema.safeParse({ ...validPayload, payload_id: 42 }).success).toBe(false);
  });
});

describe('emergencyStopStateSchema', () => {
  const validEstop = {
    header: validHeader,
    stopped: true,
    state: 2,
    reason: 'manual_trigger',
  };

  it('validates a complete EmergencyStopState message', () => {
    expect(emergencyStopStateSchema.safeParse(validEstop).success).toBe(true);
  });

  it('rejects EmergencyStopState with missing reason', () => {
    const { reason: _reason, ...bad } = validEstop;
    void _reason;
    expect(emergencyStopStateSchema.safeParse(bad).success).toBe(false);
  });
});

describe('twistSchema', () => {
  it('validates a complete Twist message', () => {
    const valid = { linear: { x: 0.5, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 0.1 } };
    expect(twistSchema.safeParse(valid).success).toBe(true);
  });

  it('rejects Twist with missing angular', () => {
    expect(twistSchema.safeParse({ linear: { x: 0, y: 0, z: 0 } }).success).toBe(false);
  });
});
