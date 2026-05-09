// SPDX-License-Identifier: Apache-2.0

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RosbridgeConnection } from './connection';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  readyState = WebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.();
    }, 0);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }

  simulateMessage(data: string): void {
    this.onmessage?.({ data });
  }

  simulateError(): void {
    this.onerror?.();
  }

  static reset(): void {
    MockWebSocket.instances = [];
  }
}

describe('RosbridgeConnection', () => {
  let conn: RosbridgeConnection;

  beforeEach(() => {
    MockWebSocket.reset();
    vi.stubGlobal('WebSocket', MockWebSocket);
    conn = new RosbridgeConnection();
  });

  afterEach(() => {
    conn.disconnect();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  describe('connect', () => {
    it('transitions to connecting state', () => {
      const states: string[] = [];
      conn.addEventListener('statechange', ((e: CustomEvent) => {
        states.push(e.detail.state);
      }) as EventListener);

      conn.connect('ws://localhost:9090');
      expect(states).toContain('connecting');
    });

    it('rejects invalid URLs', () => {
      const states: string[] = [];
      conn.addEventListener('statechange', ((e: CustomEvent) => {
        states.push(e.detail.state);
      }) as EventListener);

      conn.connect('http://invalid');
      expect(states).toContain('error');
    });

    it('transitions to connected after WebSocket opens', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;
      expect(conn.connectionState).toBe('connected');
    });
  });

  describe('disconnect', () => {
    it('transitions to disconnected state', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      conn.disconnect();
      expect(conn.connectionState).toBe('disconnected');
    });
  });

  describe('subscribe', () => {
    it('sends subscribe message when connected', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      conn.subscribe('/battery', 'sensor_msgs/BatteryState', () => {});

      const ws = MockWebSocket.instances[0];
      const subMsg = ws.sent.find((s) => JSON.parse(s).op === 'subscribe');
      expect(subMsg).toBeDefined();

      const parsed = JSON.parse(subMsg as string);
      expect(parsed.topic).toBe('/battery');
      expect(parsed.type).toBe('sensor_msgs/BatteryState');
    });

    it('returns unsubscribe function', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const unsub = conn.subscribe('/test', 'std_msgs/String', () => {});
      unsub();

      const ws = MockWebSocket.instances[0];
      const unsubMsg = ws.sent.find((s) => JSON.parse(s).op === 'unsubscribe');
      expect(unsubMsg).toBeDefined();
    });
  });

  describe('publish', () => {
    it('sends publish message when connected', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      conn.publish('/cmd_vel', 'geometry_msgs/Twist', {
        linear: { x: 0.5, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: 0.1 },
      });

      const ws = MockWebSocket.instances[0];
      const pubMsg = ws.sent.find((s) => JSON.parse(s).op === 'publish');
      expect(pubMsg).toBeDefined();

      const parsed = JSON.parse(pubMsg as string);
      expect(parsed.topic).toBe('/cmd_vel');
      expect(parsed.msg.linear.x).toBe(0.5);
    });

    it('does not send when disconnected', () => {
      conn.publish('/cmd_vel', 'geometry_msgs/Twist', {});
      expect(MockWebSocket.instances).toHaveLength(0);
    });
  });

  describe('message handling', () => {
    it('dispatches topic messages to subscribers', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const received: unknown[] = [];
      conn.subscribe('/battery', 'sensor_msgs/BatteryState', (msg) => {
        received.push(msg);
      });

      const ws = MockWebSocket.instances[0];
      ws.simulateMessage(
        JSON.stringify({
          op: 'publish',
          topic: '/battery',
          msg: { percentage: 0.85 },
        })
      );

      expect(received).toHaveLength(1);
      expect(received[0]).toEqual({ percentage: 0.85 });
    });

    it('ignores messages for unsubscribed topics', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const received: unknown[] = [];
      conn.subscribe('/battery', 'sensor_msgs/BatteryState', (msg) => {
        received.push(msg);
      });

      const ws = MockWebSocket.instances[0];
      ws.simulateMessage(
        JSON.stringify({
          op: 'publish',
          topic: '/other_topic',
          msg: { data: 'test' },
        })
      );

      expect(received).toHaveLength(0);
    });

    it('handles malformed JSON gracefully', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const ws = MockWebSocket.instances[0];
      expect(() => ws.simulateMessage('not json')).not.toThrow();
    });
  });
});
