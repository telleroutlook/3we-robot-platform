// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Wheel speeds component', () => {
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

  test('component renders 4 wheel indicators', async ({ page }) => {
    const wheelSpeeds = page.locator('robot-wheel-speeds');
    await expect(wheelSpeeds).toBeVisible();

    // Verify all 4 wheel rows exist
    for (const wheel of ['FL', 'FR', 'RL', 'RR']) {
      const bar = wheelSpeeds.locator(`#bar${wheel}`);
      await expect(bar).toBeAttached();

      const val = wheelSpeeds.locator(`#val${wheel}`);
      await expect(val).toBeAttached();
    }
  });

  test('shows zero speed initially', async ({ page }) => {
    const wheelSpeeds = page.locator('robot-wheel-speeds');

    for (const wheel of ['FL', 'FR', 'RL', 'RR']) {
      const val = wheelSpeeds.locator(`#val${wheel}`);
      await expect(val).toHaveText('0.00');
    }
  });

  test('updates displayed values on wheel_speeds topic', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/wheel_speeds',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        front_left: 0.75,
        front_right: -0.50,
        rear_left: 0.80,
        rear_right: -0.45,
      },
    });

    const wheelSpeeds = page.locator('robot-wheel-speeds');

    await expect(wheelSpeeds.locator('#valFL')).toHaveText('0.75');
    await expect(wheelSpeeds.locator('#valFR')).toHaveText('-0.50');
    await expect(wheelSpeeds.locator('#valRL')).toHaveText('0.80');
    await expect(wheelSpeeds.locator('#valRR')).toHaveText('-0.45');
  });

  test('displays forward/reverse direction indicators on bars', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/wheel_speeds',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        front_left: 0.6,
        front_right: -0.4,
        rear_left: 0.6,
        rear_right: -0.4,
      },
    });

    const wheelSpeeds = page.locator('robot-wheel-speeds');

    // Positive speed = forward class
    const barFL = wheelSpeeds.locator('#barFL');
    await expect(barFL).toHaveClass(/forward/);

    // Negative speed = reverse class
    const barFR = wheelSpeeds.locator('#barFR');
    await expect(barFR).toHaveClass(/reverse/);

    const barRL = wheelSpeeds.locator('#barRL');
    await expect(barRL).toHaveClass(/forward/);

    const barRR = wheelSpeeds.locator('#barRR');
    await expect(barRR).toHaveClass(/reverse/);
  });

  test('values are clamped to [-1, 1] range in display', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    // Send values exceeding the [-1, 1] range
    await mock.sendToClient({
      op: 'publish',
      topic: '/wheel_speeds',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        front_left: 2.5,
        front_right: -1.8,
        rear_left: 1.0,
        rear_right: -1.0,
      },
    });

    const wheelSpeeds = page.locator('robot-wheel-speeds');

    // Values should be clamped to [-1, 1]
    await expect(wheelSpeeds.locator('#valFL')).toHaveText('1.00');
    await expect(wheelSpeeds.locator('#valFR')).toHaveText('-1.00');
    await expect(wheelSpeeds.locator('#valRL')).toHaveText('1.00');
    await expect(wheelSpeeds.locator('#valRR')).toHaveText('-1.00');
  });
});
