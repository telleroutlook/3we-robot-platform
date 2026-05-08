// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Payload Panel component', () => {
  test.beforeEach(async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');

    // Connect to mock rosbridge
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    // Wait for WebSocket to "connect" (mock opens after 10ms)
    await page.waitForTimeout(50);

    // Store mock on page for access in tests
    (page as unknown as { __mock: typeof mock }).__mock = mock;
  });

  test('renders in disconnected/no-payload state initially', async ({ page }) => {
    const panel = page.locator('robot-payload-panel');
    await expect(panel).toBeVisible();

    // "No payload connected" should be visible
    const noPayload = panel.locator('#noPayload');
    await expect(noPayload).toBeVisible();
    await expect(noPayload).toContainText('No payload connected');

    // Payload info and rail toggles should be hidden
    const payloadInfo = panel.locator('#payloadInfo');
    await expect(payloadInfo).toHaveClass(/hidden/);

    const railToggles = panel.locator('#railToggles');
    await expect(railToggles).toHaveClass(/hidden/);

    // Connection dot should not have "connected" class
    const connectionDot = panel.locator('#connectionDot');
    await expect(connectionDot).not.toHaveClass(/connected/);
  });

  test('updates display on /payload_state topic when connected', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: true,
        power_12v_active: false,
        power_vbat_active: false,
        current_5v: 0.8,
        current_12v: 0.0,
        power_consumption_watts: 4.0,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    // Connection dot should be connected
    const connectionDot = panel.locator('#connectionDot');
    await expect(connectionDot).toHaveClass(/connected/);

    // No payload message should be hidden
    const noPayload = panel.locator('#noPayload');
    await expect(noPayload).toHaveClass(/hidden/);

    // Payload info should be visible
    const payloadInfo = panel.locator('#payloadInfo');
    await expect(payloadInfo).not.toHaveClass(/hidden/);
  });

  test('shows payload ID and name when connected', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: true,
        power_12v_active: true,
        power_vbat_active: false,
        current_5v: 0.8,
        current_12v: 0.2,
        power_consumption_watts: 6.4,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    const payloadName = panel.locator('#payloadName');
    await expect(payloadName).toHaveText('Lidar Module');

    const payloadId = panel.locator('#payloadId');
    await expect(payloadId).toHaveText('LIDAR_V2');
  });

  test('shows power consumption', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: true,
        power_12v_active: false,
        power_vbat_active: false,
        current_5v: 0.8,
        current_12v: 0.0,
        power_consumption_watts: 4.0,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    const payloadPower = panel.locator('#payloadPower');
    await expect(payloadPower).toHaveText('4.0 W');
  });

  test('shows power rail toggle states correctly', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: true,
        power_12v_active: false,
        power_vbat_active: true,
        current_5v: 0.8,
        current_12v: 0.0,
        power_consumption_watts: 4.0,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    // 5V toggle should be active
    const toggle5v = panel.locator('#toggle5v');
    await expect(toggle5v).toHaveClass(/active/);
    await expect(toggle5v).toHaveAttribute('aria-checked', 'true');

    // 12V toggle should be inactive
    const toggle12v = panel.locator('#toggle12v');
    await expect(toggle12v).not.toHaveClass(/active/);
    await expect(toggle12v).toHaveAttribute('aria-checked', 'false');

    // VBAT toggle should be active
    const toggleVbat = panel.locator('#toggleVbat');
    await expect(toggleVbat).toHaveClass(/active/);
    await expect(toggleVbat).toHaveAttribute('aria-checked', 'true');
  });

  test('power toggle calls /payload_power service', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    // First connect a payload so toggles are visible
    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: false,
        power_12v_active: false,
        power_vbat_active: false,
        current_5v: 0.0,
        current_12v: 0.0,
        power_consumption_watts: 0.0,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    // Click the 5V toggle to enable it
    const toggle5v = panel.locator('#toggle5v');
    await toggle5v.click();

    // Verify service call was sent
    const serviceCall = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; service?: string };
      return m.op === 'call_service' && m.service === '/payload_power';
    });

    const svc = serviceCall as { op: string; service: string; args: { payload_id: string; rail: string; enable: boolean } };
    expect(svc.args.payload_id).toBe('LIDAR_V2');
    expect(svc.args.rail).toBe('5V');
    expect(svc.args.enable).toBe(true);
  });

  test('returns to no-payload state when disconnected message received', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const panel = page.locator('robot-payload-panel');

    // First connect a payload
    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        payload_id: 'LIDAR_V2',
        name: 'Lidar Module',
        connected: true,
        power_5v_active: true,
        power_12v_active: false,
        power_vbat_active: false,
        current_5v: 0.8,
        current_12v: 0.0,
        power_consumption_watts: 4.0,
        status: 2,
      },
    });

    await page.waitForTimeout(50);

    // Verify connected state
    const payloadInfo = panel.locator('#payloadInfo');
    await expect(payloadInfo).not.toHaveClass(/hidden/);

    // Now send disconnected state
    await mock.sendToClient({
      op: 'publish',
      topic: '/payload_state',
      msg: {
        header: { stamp: { sec: 1, nanosec: 0 }, frame_id: '' },
        payload_id: '',
        name: '',
        connected: false,
        power_5v_active: false,
        power_12v_active: false,
        power_vbat_active: false,
        current_5v: 0.0,
        current_12v: 0.0,
        power_consumption_watts: 0.0,
        status: 0,
      },
    });

    await page.waitForTimeout(50);

    // Should revert to no-payload state
    const noPayload = panel.locator('#noPayload');
    await expect(noPayload).not.toHaveClass(/hidden/);
    await expect(payloadInfo).toHaveClass(/hidden/);

    const connectionDot = panel.locator('#connectionDot');
    await expect(connectionDot).not.toHaveClass(/connected/);
  });
});
