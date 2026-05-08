// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Battery gauge component', () => {
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

  test('component renders battery visual elements', async ({ page }) => {
    const gauge = page.locator('robot-battery-gauge');
    await expect(gauge).toBeVisible();

    const batteryFill = gauge.locator('#batteryFill');
    await expect(batteryFill).toBeAttached();

    const pct = gauge.locator('#batteryPct');
    await expect(pct).toBeVisible();

    const statusBadge = gauge.locator('#statusBadge');
    await expect(statusBadge).toBeVisible();
  });

  test('shows default placeholder before first topic message', async ({ page }) => {
    const gauge = page.locator('robot-battery-gauge');

    const pct = gauge.locator('#batteryPct');
    await expect(pct).toHaveText('--%');

    const voltage = gauge.locator('#voltage');
    await expect(voltage).toHaveText('--');

    const current = gauge.locator('#current');
    await expect(current).toHaveText('--');
  });

  test('updates percentage on battery state topic message', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/battery_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        voltage: 25.2,
        current: -1.5,
        charge: 0,
        capacity: 0,
        design_capacity: 0,
        percentage: 0.85,
        power_supply_status: 0,
        power_supply_health: 0,
        power_supply_technology: 0,
        present: true,
      },
    });

    const gauge = page.locator('robot-battery-gauge');
    const pct = gauge.locator('#batteryPct');
    await expect(pct).toHaveText('85%');

    const voltage = gauge.locator('#voltage');
    await expect(voltage).toHaveText('25.2 V');

    const current = gauge.locator('#current');
    await expect(current).toHaveText('-1.50 A');
  });

  test('shows LOW warning state at percentage <= 25%', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/battery_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        voltage: 22.0,
        current: -0.8,
        charge: 0,
        capacity: 0,
        design_capacity: 0,
        percentage: 0.20,
        power_supply_status: 0,
        power_supply_health: 0,
        power_supply_technology: 0,
        present: true,
      },
    });

    const gauge = page.locator('robot-battery-gauge');
    const pct = gauge.locator('#batteryPct');
    await expect(pct).toHaveText('20%');

    const statusBadge = gauge.locator('#statusBadge');
    await expect(statusBadge).toHaveText('LOW');
    await expect(statusBadge).toHaveClass(/low/);

    const fill = gauge.locator('#batteryFill');
    await expect(fill).toHaveClass(/low/);
  });

  test('shows CRITICAL state at percentage <= 10%', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/battery_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        voltage: 20.5,
        current: -0.3,
        charge: 0,
        capacity: 0,
        design_capacity: 0,
        percentage: 0.08,
        power_supply_status: 0,
        power_supply_health: 0,
        power_supply_technology: 0,
        present: true,
      },
    });

    const gauge = page.locator('robot-battery-gauge');
    const pct = gauge.locator('#batteryPct');
    await expect(pct).toHaveText('8%');

    const statusBadge = gauge.locator('#statusBadge');
    await expect(statusBadge).toHaveText('CRITICAL');
    await expect(statusBadge).toHaveClass(/critical/);

    const fill = gauge.locator('#batteryFill');
    await expect(fill).toHaveClass(/critical/);
  });

  test('shows OK state at full charge (100%)', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    await mock.sendToClient({
      op: 'publish',
      topic: '/battery_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        voltage: 28.8,
        current: 0.0,
        charge: 0,
        capacity: 0,
        design_capacity: 0,
        percentage: 1.0,
        power_supply_status: 0,
        power_supply_health: 0,
        power_supply_technology: 0,
        present: true,
      },
    });

    const gauge = page.locator('robot-battery-gauge');
    const pct = gauge.locator('#batteryPct');
    await expect(pct).toHaveText('100%');

    const statusBadge = gauge.locator('#statusBadge');
    await expect(statusBadge).toHaveText('OK');
    await expect(statusBadge).toHaveClass(/ok/);

    const fill = gauge.locator('#batteryFill');
    await expect(fill).not.toHaveClass(/low/);
    await expect(fill).not.toHaveClass(/critical/);
  });
});
