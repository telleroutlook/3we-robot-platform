// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Connection layer', () => {
  test('initial state shows disconnected', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');

    const status = page.locator('.indicator-label');
    await expect(status).toHaveText('Disconnected');

    const connectBtn = page.locator('#connectBtn');
    await expect(connectBtn).toHaveText('Connect');
  });

  test('connecting with valid URL transitions to connected', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');

    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    // Wait for mock WebSocket to open (auto-opens after 10ms)
    await page.waitForTimeout(50);

    const status = page.locator('.indicator-label');
    await expect(status).toHaveText('Connected');

    const connectBtn = page.locator('#connectBtn');
    await expect(connectBtn).toHaveText('Disconnect');
  });

  test('connecting with invalid URL shows error state', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');

    // Use a URL that doesn't start with ws:// or wss://
    await page.fill('#wsUrlInput', 'http://localhost:9090');
    await page.click('#connectBtn');

    await page.waitForTimeout(50);

    const status = page.locator('.indicator-label');
    await expect(status).toHaveText('Error');

    const connectBtn = page.locator('#connectBtn');
    await expect(connectBtn).toHaveText('Retry');
  });

  test('topic subscription sends rosbridge subscribe message', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');

    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    // Subscribe to a custom topic via the connection singleton
    await page.evaluate(async () => {
      const { connection } = await import('/src/connection.ts');
      connection.subscribe('/test_topic', 'std_msgs/String', () => {});
    });

    // Verify the subscribe message was sent through the mock WebSocket
    const subMsg = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; topic?: string };
      return m.op === 'subscribe' && m.topic === '/test_topic';
    });

    const sub = subMsg as { op: string; topic: string; type: string };
    expect(sub.op).toBe('subscribe');
    expect(sub.topic).toBe('/test_topic');
    expect(sub.type).toBe('std_msgs/String');
  });

  test('publishing a message sends correct rosbridge format', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');

    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    // Publish a message via the connection singleton
    await page.evaluate(async () => {
      const { connection } = await import('/src/connection.ts');
      connection.publish('/cmd_vel', 'geometry_msgs/Twist', {
        linear: { x: 1.0, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: 0.5 },
      });
    });

    // Verify the publish message format in the mock (match on non-zero linear.x to avoid joystick zero-velocity messages)
    const pubMsg = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; topic?: string; msg?: { linear?: { x?: number } } };
      return m.op === 'publish' && m.topic === '/cmd_vel' && m.msg?.linear?.x === 1.0;
    });

    const pub = pubMsg as {
      op: string;
      topic: string;
      type: string;
      msg: { linear: { x: number; y: number; z: number }; angular: { x: number; y: number; z: number } };
    };
    expect(pub.op).toBe('publish');
    expect(pub.topic).toBe('/cmd_vel');
    expect(pub.type).toBe('geometry_msgs/Twist');
    expect(pub.msg.linear.x).toBe(1.0);
    expect(pub.msg.angular.z).toBe(0.5);
  });

  test('service call sends correct format and resolves on response', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');

    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    // Call a service from the page context
    const resultPromise = page.evaluate(async () => {
      const { connection } = await import('/src/connection.ts');
      return connection.callService<{ data: boolean }, { success: boolean; message: string }>(
        '/test_service',
        'std_srvs/SetBool',
        { data: true }
      );
    });

    // Wait for the service call message to arrive at the mock
    const svcMsg = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; service?: string };
      return m.op === 'call_service' && m.service === '/test_service';
    });

    const svc = svcMsg as { op: string; service: string; type: string; args: { data: boolean }; id: string };
    expect(svc.op).toBe('call_service');
    expect(svc.service).toBe('/test_service');
    expect(svc.type).toBe('std_srvs/SetBool');
    expect(svc.args.data).toBe(true);

    // Send a successful service response back via the mock
    await mock.sendToClient({
      op: 'service_response',
      service: '/test_service',
      id: svc.id,
      values: { success: true, message: 'OK' },
      result: true,
    });

    // Verify the promise resolves with the response values
    const result = await resultPromise;
    expect(result).toEqual({ success: true, message: 'OK' });
  });

  test('service call times out if no response', async ({ page }) => {
    await setupMockRosbridge(page);

    // Install fake timers before page navigation so setTimeout can be controlled
    await page.clock.install();
    await page.goto('/');

    // Manually advance time for the mock WebSocket open (10ms) and app init
    await page.clock.fastForward(50);

    // Connect via direct API since fake timers prevent real setTimeout-based UI flows
    await page.evaluate(async () => {
      const { connection } = await import('/src/connection.ts');
      connection.connect('ws://localhost:9090');
    });

    // Advance past the mock WebSocket open delay
    await page.clock.fastForward(50);

    // Start a service call that will never receive a response
    const errorPromise = page.evaluate(async () => {
      const { connection } = await import('/src/connection.ts');
      try {
        await connection.callService('/slow_service', 'std_srvs/Trigger', {});
        return 'no_error';
      } catch (err: unknown) {
        return (err as Error).message;
      }
    });

    // Advance time past the internal 10000ms service timeout
    await page.clock.fastForward(11000);

    const errorMessage = await errorPromise;
    expect(errorMessage).toContain('timed out');
  });

  test('disconnect method closes WebSocket and shows disconnected state', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');

    // Connect first
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    const status = page.locator('.indicator-label');
    await expect(status).toHaveText('Connected');

    // Click disconnect (same button toggles when connected)
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    await expect(status).toHaveText('Disconnected');

    const connectBtn = page.locator('#connectBtn');
    await expect(connectBtn).toHaveText('Connect');
  });
});
