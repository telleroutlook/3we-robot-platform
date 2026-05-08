// SPDX-License-Identifier: Apache-2.0
import type { Page } from '@playwright/test';

export interface MockRosbridge {
  messages: unknown[];
  sendToClient: (msg: unknown) => Promise<void>;
  waitForMessage: (predicate: (msg: unknown) => boolean, timeout?: number) => Promise<unknown>;
}

export async function setupMockRosbridge(page: Page, port = 9090): Promise<MockRosbridge> {
  const messages: unknown[] = [];

  await page.exposeFunction('__mockWsSend', (data: string) => {
    messages.push(JSON.parse(data));
  });

  await page.addInitScript(`
    (function() {
      const OriginalWebSocket = window.WebSocket;
      const mockSockets = [];

      window.__mockWsSockets = mockSockets;
      window.__mockWsSendToClient = function(data) {
        for (const sock of mockSockets) {
          if (sock.readyState === 1) {
            const event = new MessageEvent('message', { data: JSON.stringify(data) });
            sock.dispatchEvent(event);
          }
        }
      };

      class MockWebSocket extends EventTarget {
        static CONNECTING = 0;
        static OPEN = 1;
        static CLOSING = 2;
        static CLOSED = 3;

        readyState = 0;
        url = '';
        protocol = '';
        extensions = '';
        bufferedAmount = 0;
        binaryType = 'blob';
        onopen = null;
        onclose = null;
        onerror = null;
        onmessage = null;

        constructor(url) {
          super();
          this.url = url;
          mockSockets.push(this);

          setTimeout(() => {
            this.readyState = 1;
            const event = new Event('open');
            this.dispatchEvent(event);
            if (this.onopen) this.onopen(event);
          }, 10);
        }

        send(data) {
          if (this.readyState !== 1) throw new Error('WebSocket not open');
          window.__mockWsSend(data);
        }

        close() {
          this.readyState = 3;
          const event = new CloseEvent('close', { code: 1000, reason: '' });
          this.dispatchEvent(event);
          if (this.onclose) this.onclose(event);
          const idx = mockSockets.indexOf(this);
          if (idx >= 0) mockSockets.splice(idx, 1);
        }

        addEventListener(type, listener, options) {
          super.addEventListener(type, listener, options);
        }

        dispatchEvent(event) {
          const handler = this['on' + event.type];
          if (handler) handler.call(this, event);
          return super.dispatchEvent(event);
        }
      }

      Object.defineProperty(MockWebSocket, 'CONNECTING', { value: 0 });
      Object.defineProperty(MockWebSocket, 'OPEN', { value: 1 });
      Object.defineProperty(MockWebSocket, 'CLOSING', { value: 2 });
      Object.defineProperty(MockWebSocket, 'CLOSED', { value: 3 });

      window.WebSocket = MockWebSocket;
    })();
  `);

  const sendToClient = async (msg: unknown) => {
    await page.evaluate((data) => {
      (window as unknown as { __mockWsSendToClient: (d: unknown) => void }).__mockWsSendToClient(data);
    }, msg);
  };

  const waitForMessage = async (predicate: (msg: unknown) => boolean, timeout = 5000): Promise<unknown> => {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const found = messages.find(predicate);
      if (found) return found;
      await page.waitForTimeout(50);
    }
    throw new Error('Timed out waiting for matching WebSocket message');
  };

  return { messages, sendToClient, waitForMessage };
}
