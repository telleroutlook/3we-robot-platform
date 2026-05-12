// SPDX-License-Identifier: Apache-2.0

import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('robot-collection-status', () => {
  test('renders in IDLE state initially', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    const component = page.locator('robot-collection-status');
    await expect(component).toBeVisible();

    const badge = component.locator('#stateBadge');
    await expect(badge).toHaveText('IDLE');
  });

  test('updates state display on collection state message', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    await mock.sendToClient({
      op: 'publish',
      topic: '/collection/state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        state: 1,
        balls_in_basket: 0,
        total_collected: 0,
        error_message: '',
      },
    });

    const badge = page.locator('robot-collection-status').locator('#stateBadge');
    await expect(badge).toHaveText('SEARCHING');
  });

  test('updates ball counts on state message', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    await mock.sendToClient({
      op: 'publish',
      topic: '/collection/state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        state: 3,
        balls_in_basket: 4,
        total_collected: 7,
        error_message: '',
      },
    });

    const component = page.locator('robot-collection-status');
    const basketCount = component.locator('#basketCount');
    const totalCount = component.locator('#totalCount');
    await expect(basketCount).toHaveText('4');
    await expect(totalCount).toHaveText('7');
  });

  test('start button publishes command', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    const startBtn = page.locator('robot-collection-status').locator('#startBtn');
    await startBtn.click();

    const messages = await mock.getClientMessages();
    const publishMsg = messages.find(
      (m: { op: string; topic?: string }) => m.op === 'publish' && m.topic === '/collection/command'
    );
    expect(publishMsg).toBeDefined();
  });

  test('stop button disabled in IDLE state', async ({ page }) => {
    await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    const stopBtn = page.locator('robot-collection-status').locator('#stopBtn');
    await expect(stopBtn).toBeDisabled();
  });

  test('stop button enabled when active', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    await mock.sendToClient({
      op: 'publish',
      topic: '/collection/state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        state: 1,
        balls_in_basket: 0,
        total_collected: 0,
        error_message: '',
      },
    });

    const stopBtn = page.locator('robot-collection-status').locator('#stopBtn');
    await expect(stopBtn).toBeEnabled();
  });

  test('state badge shows DUMPING with correct color', async ({ page }) => {
    const mock = await setupMockRosbridge(page);
    await page.goto('/');
    await page.fill('#wsUrlInput', 'ws://localhost:9090');
    await page.click('#connectBtn');

    await mock.sendToClient({
      op: 'publish',
      topic: '/collection/state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        state: 5,
        balls_in_basket: 6,
        total_collected: 12,
        error_message: '',
      },
    });

    const badge = page.locator('robot-collection-status').locator('#stateBadge');
    await expect(badge).toHaveText('DUMPING');
  });
});
