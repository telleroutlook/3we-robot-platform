// SPDX-License-Identifier: Apache-2.0

import type {
  ConnectionState,
  ConnectionEvent,
  RosbridgeMessage,
  RosbridgeSubscribe,
  RosbridgePublish,
  RosbridgeCallService,
  RosbridgeServiceResponse,
} from './types';

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

  get connectionState(): ConnectionState {
    return this.state;
  }

  connect(url: string): void {
    this.intentionalClose = false;
    this.url = url;
    this.clearReconnectTimer();
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
    };

    this.ws.onclose = () => {
      this.ws = null;
      if (!this.intentionalClose) {
        this.setState('disconnected');
        this.scheduleReconnect();
      } else {
        this.setState('disconnected');
      }
    };

    this.ws.onerror = () => {
      this.setState('error');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.handleMessage(event.data as string);
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.clearReconnectTimer();
    this.reconnectAttempts = 0;
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
      entry!.callbacks.delete(callback as TopicCallback);
      if (entry!.callbacks.size === 0) {
        this.subscribers.delete(topic);
        this.sendUnsubscribe(topic);
      }
    };
  }

  publish(topic: string, type: string, msg: unknown): void {
    if (!this.isConnected()) return;

    const payload: RosbridgePublish = { op: 'publish', topic, type, msg };
    this.ws!.send(JSON.stringify(payload));
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
    this.ws!.send(JSON.stringify(payload));

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
    let msg: RosbridgeMessage;
    try {
      msg = JSON.parse(raw) as RosbridgeMessage;
    } catch {
      return;
    }

    if (msg.op === 'publish' && msg.topic) {
      const entry = this.subscribers.get(msg.topic);
      if (entry) {
        for (const cb of entry.callbacks) {
          cb(msg.msg);
        }
      }
    } else if (msg.op === 'service_response') {
      const resp = msg as unknown as RosbridgeServiceResponse;
      const pending = this.pendingServices.get(resp.id ?? '');
      if (pending) {
        this.pendingServices.delete(resp.id ?? '');
        if (resp.result) {
          pending.resolve(resp.values);
        } else {
          pending.reject(new Error(`Service call failed: ${JSON.stringify(resp.values)}`));
        }
      }
    }
  }

  private sendSubscribe(topic: string, type: string): void {
    if (!this.isConnected()) return;
    const payload: RosbridgeSubscribe = { op: 'subscribe', topic, type };
    this.ws!.send(JSON.stringify(payload));
  }

  private sendUnsubscribe(topic: string): void {
    if (!this.isConnected()) return;
    this.ws!.send(JSON.stringify({ op: 'unsubscribe', topic }));
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
}

/** Singleton connection instance */
export const connection = new RosbridgeConnection();
