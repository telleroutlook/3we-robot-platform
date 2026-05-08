// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Sensor Radar component', () => {
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

  test('component renders with SVG radar visualization', async ({ page }) => {
    const radar = page.locator('robot-sensor-radar');
    await expect(radar).toBeVisible();

    // Verify SVG is rendered inside shadow DOM
    const svg = radar.locator('.radar-svg');
    await expect(svg).toBeVisible();
    await expect(svg).toHaveAttribute('viewBox', '0 0 200 200');
  });

  test('shows no obstacles initially with dashes for labels', async ({ page }) => {
    const radar = page.locator('robot-sensor-radar');

    // All distance labels should show "--" (max range / no obstacles)
    const labelFront = radar.locator('#labelFront');
    const labelBack = radar.locator('#labelBack');
    const labelLeft = radar.locator('#labelLeft');
    const labelRight = radar.locator('#labelRight');

    await expect(labelFront).toHaveText('--');
    await expect(labelBack).toHaveText('--');
    await expect(labelLeft).toHaveText('--');
    await expect(labelRight).toHaveText('--');
  });

  test('updates display on /ultrasonic/front topic message', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const radar = page.locator('robot-sensor-radar');

    // Send a range reading for front sensor at 0.5m
    await mock.sendToClient({
      op: 'publish',
      topic: '/ultrasonic/front',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'front_ultrasonic' },
        radiation_type: 0,
        field_of_view: 0.26,
        min_range: 0.02,
        max_range: 4.0,
        range: 0.5,
      },
    });

    // Wait for requestAnimationFrame render cycle
    await page.waitForTimeout(50);

    // Front label should show the distance value
    const labelFront = radar.locator('#labelFront');
    await expect(labelFront).toHaveText('0.50');
  });

  test('highlights obstacles within close threshold distance with warning color', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const radar = page.locator('robot-sensor-radar');

    // Send a very close range reading (< 0.15m triggers red)
    await mock.sendToClient({
      op: 'publish',
      topic: '/ultrasonic/front',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'front_ultrasonic' },
        radiation_type: 0,
        field_of_view: 0.26,
        min_range: 0.02,
        max_range: 4.0,
        range: 0.10,
      },
    });

    await page.waitForTimeout(50);

    // Cone should have red fill color indicating danger
    const coneFront = radar.locator('#coneFront');
    const fill = await coneFront.getAttribute('fill');
    expect(fill).toContain('239,68,68'); // red color
  });

  test('handles max range values by showing dashes', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const radar = page.locator('robot-sensor-radar');

    // Send a reading at exactly max range (4.0m)
    await mock.sendToClient({
      op: 'publish',
      topic: '/ultrasonic/left',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'left_ultrasonic' },
        radiation_type: 0,
        field_of_view: 0.26,
        min_range: 0.02,
        max_range: 4.0,
        range: 4.0,
      },
    });

    await page.waitForTimeout(50);

    // At max range, label shows "--"
    const labelLeft = radar.locator('#labelLeft');
    await expect(labelLeft).toHaveText('--');
  });

  test('handles NaN or invalid range readings gracefully', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const radar = page.locator('robot-sensor-radar');

    // Send an invalid reading (Infinity is used for NaN internally)
    await mock.sendToClient({
      op: 'publish',
      topic: '/ultrasonic/right',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'right_ultrasonic' },
        radiation_type: 0,
        field_of_view: 0.26,
        min_range: 0.02,
        max_range: 4.0,
        range: -1,
      },
    });

    await page.waitForTimeout(50);

    // Invalid range should not crash component; SVG should still exist
    const svg = radar.locator('.radar-svg');
    await expect(svg).toBeVisible();

    // The cone path should still be valid (not cause render errors)
    const coneRight = radar.locator('#coneRight');
    const d = await coneRight.getAttribute('d');
    expect(d).toBeTruthy();
  });
});
