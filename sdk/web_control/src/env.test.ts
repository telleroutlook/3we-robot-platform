// SPDX-License-Identifier: Apache-2.0

import { describe, it, expect } from 'vitest';
import { validateEnv } from './env';

describe('validateEnv', () => {
  it('accepts valid ws:// URL', () => {
    const env = validateEnv({ VITE_ROSBRIDGE_URL: 'ws://192.168.1.100:9090' });
    expect(env.VITE_ROSBRIDGE_URL).toBe('ws://192.168.1.100:9090');
  });

  it('accepts valid wss:// URL', () => {
    const env = validateEnv({ VITE_ROSBRIDGE_URL: 'wss://robot.example.com:9090' });
    expect(env.VITE_ROSBRIDGE_URL).toBe('wss://robot.example.com:9090');
  });

  it('defaults to ws://localhost:9090 when override is absent', () => {
    const env = validateEnv();
    expect(env.VITE_ROSBRIDGE_URL).toBe('ws://localhost:9090');
  });

  it('rejects http:// protocol', () => {
    expect(() => validateEnv({ VITE_ROSBRIDGE_URL: 'http://localhost:9090' })).toThrow(
      'ws:// or wss://'
    );
  });

  it('rejects empty string', () => {
    expect(() => validateEnv({ VITE_ROSBRIDGE_URL: '' })).toThrow();
  });
});
