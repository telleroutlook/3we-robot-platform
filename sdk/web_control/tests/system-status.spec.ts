// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('System status component', () => {
  test.beforeEach(async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');

    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');
    await page.waitForTimeout(50);

    (page as unknown as { __mock: typeof mock }).__mock = mock;
  });

  test('component renders with title', async ({ page }) => {
    const status = page.locator('robot-system-status');
    await expect(status).toBeVisible();

    const title = status.locator('.system-status__title');
    await expect(title).toHaveText('System Health');
  });

  test('grid is empty before first diagnostics message', async ({ page }) => {
    const status = page.locator('robot-system-status');
    const grid = status.locator('.system-status__grid');
    await expect(grid).toBeAttached();

    const items = status.locator('.system-status__item');
    await expect(items).toHaveCount(0);
  });

  test('renders diagnostic items on topic message', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: {
        status: [
          { name: '/motors/left', level: 0, message: 'Running', values: {} },
          { name: '/sensors/imu', level: 1, message: 'Degraded', values: {} },
          { name: '/battery/pack1', level: 2, message: 'Critical voltage', values: {} },
        ],
      },
    });

    const status = page.locator('robot-system-status');
    const items = status.locator('.system-status__item');
    await expect(items).toHaveCount(3);

    const firstItem = items.nth(0);
    await expect(firstItem.locator('.system-status__name')).toHaveText('left');
    await expect(firstItem.locator('.system-status__message')).toHaveText('Running');
    await expect(firstItem).toHaveAttribute('data-level', 'ok');

    const secondItem = items.nth(1);
    await expect(secondItem.locator('.system-status__name')).toHaveText('imu');
    await expect(secondItem.locator('.system-status__message')).toHaveText('Degraded');
    await expect(secondItem).toHaveAttribute('data-level', 'warn');

    const thirdItem = items.nth(2);
    await expect(thirdItem.locator('.system-status__name')).toHaveText('pack1');
    await expect(thirdItem.locator('.system-status__message')).toHaveText('Critical voltage');
    await expect(thirdItem).toHaveAttribute('data-level', 'error');
  });

  test('updates display when new diagnostics arrive', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: {
        status: [{ name: '/motors/left', level: 0, message: 'OK', values: {} }],
      },
    });

    const status = page.locator('robot-system-status');
    await expect(status.locator('.system-status__item')).toHaveCount(1);

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: {
        status: [
          { name: '/motors/left', level: 2, message: 'Overheating', values: {} },
          { name: '/motors/right', level: 0, message: 'OK', values: {} },
        ],
      },
    });

    await expect(status.locator('.system-status__item')).toHaveCount(2);
    const firstItem = status.locator('.system-status__item').nth(0);
    await expect(firstItem).toHaveAttribute('data-level', 'error');
    await expect(firstItem.locator('.system-status__message')).toHaveText('Overheating');
  });

  test('marks stale after no updates for 5 seconds', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: {
        status: [{ name: '/motors/left', level: 0, message: 'OK', values: {} }],
      },
    });

    const status = page.locator('robot-system-status');
    await expect(status).not.toHaveAttribute('data-stale', 'true');

    // Wait for stale detection (5s timeout + 2s interval margin)
    await page.waitForTimeout(7500);
    await expect(status).toHaveAttribute('data-stale', 'true');
  });

  test('removes stale attribute when new message arrives', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: { status: [{ name: '/imu', level: 0, message: 'OK', values: {} }] },
    });

    await page.waitForTimeout(7500);
    const status = page.locator('robot-system-status');
    await expect(status).toHaveAttribute('data-stale', 'true');

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: { status: [{ name: '/imu', level: 0, message: 'Still OK', values: {} }] },
    });

    await expect(status).not.toHaveAttribute('data-stale', 'true');
  });

  test('handles stale level (level 3) correctly', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/diagnostics',
      msg: {
        status: [{ name: '/sensor/lidar', level: 3, message: 'No data', values: {} }],
      },
    });

    const status = page.locator('robot-system-status');
    const item = status.locator('.system-status__item').nth(0);
    await expect(item).toHaveAttribute('data-level', 'stale');
  });
});
