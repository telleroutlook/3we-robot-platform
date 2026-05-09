// SPDX-License-Identifier: Apache-2.0

import { describe, it, expect } from 'vitest';
import { rosbridgeMessageSchema } from './schemas';

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
