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

  describe('callService', () => {
    it('sends service call message and resolves on response', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const ws = MockWebSocket.instances[0];
      const resultPromise = conn.callService('/get_map', 'nav_msgs/GetMap', {});

      const svcMsg = ws.sent.find((s) => JSON.parse(s).op === 'call_service');
      expect(svcMsg).toBeDefined();
      const parsed = JSON.parse(svcMsg as string);
      expect(parsed.service).toBe('/get_map');

      ws.simulateMessage(
        JSON.stringify({
          op: 'service_response',
          service: '/get_map',
          id: parsed.id,
          result: true,
          values: { map: 'data' },
        })
      );

      const result = await resultPromise;
      expect(result).toEqual({ map: 'data' });
    });

    it('rejects on failed service response', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const ws = MockWebSocket.instances[0];
      const resultPromise = conn.callService('/fail_svc', 'std_srvs/Trigger', {});

      const svcMsg = ws.sent.find((s) => JSON.parse(s).op === 'call_service');
      const parsed = JSON.parse(svcMsg as string);

      ws.simulateMessage(
        JSON.stringify({
          op: 'service_response',
          service: '/fail_svc',
          id: parsed.id,
          result: false,
          values: { message: 'failed' },
        })
      );

      await expect(resultPromise).rejects.toThrow('Service call failed');
    });

    it('throws when not connected', async () => {
      await expect(conn.callService('/test', 'std_srvs/Trigger', {})).rejects.toThrow(
        'Not connected'
      );
    });

    it('times out after 10s', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      const resultPromise = conn.callService('/slow', 'std_srvs/Trigger', {});
      vi.advanceTimersByTime(10001);

      await expect(resultPromise).rejects.toThrow('timed out');
    });
  });

  describe('reconnection', () => {
    it('schedules reconnect on unexpected close', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      const ws = MockWebSocket.instances[0];
      ws.readyState = WebSocket.CLOSED;
      ws.onclose?.();

      expect(conn.connectionState).toBe('connecting');

      vi.advanceTimersByTime(1000);
      expect(MockWebSocket.instances.length).toBe(2);
    });

    it('does not reconnect on intentional disconnect', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      conn.disconnect();
      expect(conn.connectionState).toBe('disconnected');

      vi.advanceTimersByTime(5000);
      expect(MockWebSocket.instances.length).toBe(1);
    });

    it('resubscribes topics after reconnect', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      conn.subscribe('/battery', 'sensor_msgs/BatteryState', () => {});

      const ws1 = MockWebSocket.instances[0];
      ws1.readyState = WebSocket.CLOSED;
      ws1.onclose?.();

      vi.advanceTimersByTime(1000);
      await vi.advanceTimersByTimeAsync(1);

      const ws2 = MockWebSocket.instances[1];
      const subMsgs = ws2.sent.filter((s) => JSON.parse(s).op === 'subscribe');
      expect(subMsgs.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('heartbeat', () => {
    it('sends ping messages periodically', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      const ws = MockWebSocket.instances[0];
      ws.sent.length = 0;

      vi.advanceTimersByTime(10000);

      const pings = ws.sent.filter((s) => JSON.parse(s).op === 'ping');
      expect(pings.length).toBe(1);
    });

    it('resets missed pongs on pong response', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      const ws = MockWebSocket.instances[0];

      vi.advanceTimersByTime(10000);
      ws.simulateMessage(JSON.stringify({ op: 'pong' }));

      vi.advanceTimersByTime(10000);
      ws.simulateMessage(JSON.stringify({ op: 'pong' }));

      vi.advanceTimersByTime(10000);
      ws.simulateMessage(JSON.stringify({ op: 'pong' }));

      expect(ws.readyState).toBe(WebSocket.OPEN);
    });

    it('closes WebSocket after max missed pongs', async () => {
      vi.useFakeTimers();

      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await vi.advanceTimersByTimeAsync(1);
      await connected;

      vi.advanceTimersByTime(30001);

      const ws = MockWebSocket.instances[0];
      expect(ws.readyState).toBe(WebSocket.CLOSED);
    });
  });

  describe('WebSocket error handling', () => {
    it('transitions to error state on WebSocket error', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      const states: string[] = [];
      conn.addEventListener('statechange', ((e: CustomEvent) => {
        states.push(e.detail.state);
      }) as EventListener);

      const ws = MockWebSocket.instances[0];
      ws.simulateError();

      expect(states).toContain('error');
    });

    it('rejects pending services on disconnect', async () => {
      const connected = new Promise<void>((resolve) => {
        conn.addEventListener('statechange', ((e: CustomEvent) => {
          if (e.detail.state === 'connected') resolve();
        }) as EventListener);
      });

      conn.connect('ws://localhost:9090');
      await connected;

      vi.useFakeTimers();
      const svcPromise = conn.callService('/test', 'std_srvs/Trigger', {});
      conn.disconnect();

      await expect(svcPromise).rejects.toThrow('Disconnected');
    });
  });

  describe('non-localhost ws:// warning', () => {
    it('warns on insecure non-localhost connection', async () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      conn.connect('ws://192.168.1.100:9090');

      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Unencrypted ws://'));
      warnSpy.mockRestore();
    });
  });
});
