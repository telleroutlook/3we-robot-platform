// SPDX-License-Identifier: Apache-2.0

import type { z } from 'zod';
import type {
  ConnectionState,
  ConnectionEvent,
  RosbridgeSubscribe,
  RosbridgePublish,
  RosbridgeCallService,
} from './types';

import { rosbridgeMessageSchema } from './schemas';

type TopicCallback = (msg: unknown) => void;

interface ServicePending {
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
}

/**
 * Rosbridge WebSocket client with auto-reconnect and typed messaging.
 */
export class RosbridgeConnection extends EventTarget {
  private ws: WebSocket | null = null;
  private url = '';
  private state: ConnectionState = 'disconnected';
  private subscribers = new Map<string, { type: string; callbacks: Set<TopicCallback> }>();
  private pendingServices = new Map<string, ServicePending>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private baseReconnectDelay = 1000;
  private serviceIdCounter = 0;
  private intentionalClose = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private missedPongs = 0;
  private readonly heartbeatIntervalMs = 10000;
  private readonly maxMissedPongs = 3;

  get connectionState(): ConnectionState {
    return this.state;
  }

  connect(url: string): void {
    if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
      this.setState('error');
      return;
    }
    if (url.startsWith('ws://') && !url.includes('localhost') && !url.includes('127.0.0.1')) {
      // eslint-disable-next-line no-console
      console.warn(
        '[RosbridgeConnection] Unencrypted ws:// connection to a non-localhost host. Use wss:// for robot control over a network.'
      );
    }
    this.intentionalClose = false;
    this.url = url;
    this.clearReconnectTimer();
    this.stopHeartbeat();

    if (this.ws) {
      const old = this.ws;
      this.ws = null;
      old.onopen = null;
      old.onclose = null;
      old.onerror = null;
      old.onmessage = null;
      old.close();
    }

    this.setState('connecting');

    try {
      this.ws = new WebSocket(url);
    } catch {
      this.setState('error');
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setState('connected');
      this.resubscribeAll();
      this.startHeartbeat();
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.stopHeartbeat();
      if (!this.intentionalClose) {
        this.setState('connecting');
        this.scheduleReconnect();
      } else {
        this.setState('disconnected');
      }
    };

    this.ws.onerror = () => {
      this.setState('error');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      if (typeof event.data !== 'string') return;
      this.handleMessage(event.data);
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    this.stopHeartbeat();
    this.reconnectAttempts = 0;
    for (const [, pending] of this.pendingServices) {
      pending.reject(new Error('Disconnected'));
    }
    this.pendingServices.clear();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState('disconnected');
  }

  subscribe<T>(topic: string, type: string, callback: (msg: T) => void): () => void {
    let entry = this.subscribers.get(topic);
    if (!entry) {
      entry = { type, callbacks: new Set() };
      this.subscribers.set(topic, entry);
    }
    entry.callbacks.add(callback as TopicCallback);

    if (this.isConnected()) {
      this.sendSubscribe(topic, type);
    }

    return () => {
      const current = this.subscribers.get(topic);
      if (!current) return;
      current.callbacks.delete(callback as TopicCallback);
      if (current.callbacks.size === 0) {
        this.subscribers.delete(topic);
        this.sendUnsubscribe(topic);
      }
    };
  }

  safeSubscribe<T>(
    topic: string,
    type: string,
    schema: z.ZodType<T>,
    callback: (msg: T) => void
  ): () => void {
    return this.subscribe<unknown>(topic, type, (raw) => {
      const result = schema.safeParse(raw);
      if (result.success) {
        callback(result.data);
      }
    });
  }

  publish(topic: string, type: string, msg: unknown): void {
    if (!this.isConnected()) return;

    const payload: RosbridgePublish = { op: 'publish', topic, type, msg };
    this.ws?.send(JSON.stringify(payload));
  }

  async callService<TArgs = unknown, TResult = unknown>(
    service: string,
    type: string,
    args?: TArgs
  ): Promise<TResult> {
    if (!this.isConnected()) {
      throw new Error('Not connected to rosbridge');
    }

    const id = `svc_${++this.serviceIdCounter}_${Date.now()}`;

    const promise = new Promise<unknown>((resolve, reject) => {
      this.pendingServices.set(id, { resolve, reject });

      setTimeout(() => {
        if (this.pendingServices.has(id)) {
          this.pendingServices.delete(id);
          reject(new Error(`Service call to ${service} timed out`));
        }
      }, 10000);
    });

    const payload: RosbridgeCallService = { op: 'call_service', service, type, args, id };
    this.ws?.send(JSON.stringify(payload));

    return promise as Promise<TResult>;
  }

  private isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  private setState(newState: ConnectionState): void {
    this.state = newState;
    const event: ConnectionEvent = { state: newState, url: this.url };
    this.dispatchEvent(new CustomEvent<ConnectionEvent>('statechange', { detail: event }));
  }

  private handleMessage(raw: string): void {
    let json: unknown;
    try {
      json = JSON.parse(raw);
    } catch {
      return;
    }

    const result = rosbridgeMessageSchema.safeParse(json);
    if (!result.success) {
      return;
    }

    const msg = result.data;

    if (msg.op === 'publish') {
      const entry = this.subscribers.get(msg.topic);
      if (entry) {
        for (const cb of entry.callbacks) {
          cb(msg.msg);
        }
      }
    } else if (msg.op === 'service_response') {
      if (!msg.id) return;
      const pending = this.pendingServices.get(msg.id);
      if (pending) {
        this.pendingServices.delete(msg.id);
        if (msg.result) {
          pending.resolve(msg.values);
        } else {
          pending.reject(new Error(`Service call failed: ${JSON.stringify(msg.values)}`));
        }
      }
    } else if (msg.op === 'pong') {
      this.missedPongs = 0;
    }
  }

  private sendSubscribe(topic: string, type: string): void {
    if (!this.isConnected()) return;
    const payload: RosbridgeSubscribe = { op: 'subscribe', topic, type };
    this.ws?.send(JSON.stringify(payload));
  }

  private sendUnsubscribe(topic: string): void {
    if (!this.isConnected()) return;
    this.ws?.send(JSON.stringify({ op: 'unsubscribe', topic }));
  }

  private resubscribeAll(): void {
    for (const [topic, entry] of this.subscribers) {
      this.sendSubscribe(topic, entry.type);
    }
  }

  private scheduleReconnect(): void {
    this.clearReconnectTimer();
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      if (this.state !== 'connected' && !this.intentionalClose) {
        this.connect(this.url);
      }
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.missedPongs = 0;
    this.heartbeatTimer = setInterval(() => {
      if (!this.isConnected()) return;
      if (this.missedPongs >= this.maxMissedPongs) {
        this.stopHeartbeat();
        this.ws?.close();
        return;
      }
      this.ws?.send(JSON.stringify({ op: 'ping' }));
      this.missedPongs++;
    }, this.heartbeatIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

/** Singleton connection instance */
export const connection = new RosbridgeConnection();
