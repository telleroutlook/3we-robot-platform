// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('IMU Attitude component', () => {
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

  test('component renders attitude indicator', async ({ page }) => {
    const imu = page.locator('robot-imu-attitude');
    await expect(imu).toBeVisible();

    // Verify the horizon container and attitude values are rendered
    const horizonContainer = imu.locator('.horizon-container');
    await expect(horizonContainer).toBeVisible();

    const rollValue = imu.locator('#rollValue');
    const pitchValue = imu.locator('#pitchValue');
    const yawValue = imu.locator('#yawValue');

    await expect(rollValue).toBeVisible();
    await expect(pitchValue).toBeVisible();
    await expect(yawValue).toBeVisible();
  });

  test('shows default orientation initially (0/0/0)', async ({ page }) => {
    const imu = page.locator('robot-imu-attitude');

    const rollValue = imu.locator('#rollValue');
    const pitchValue = imu.locator('#pitchValue');
    const yawValue = imu.locator('#yawValue');

    await expect(rollValue).toHaveText('0.0°');
    await expect(pitchValue).toHaveText('0.0°');
    await expect(yawValue).toHaveText('0.0°');
  });

  test('updates display on /imu/data topic with quaternion (~45 deg yaw)', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const imu = page.locator('robot-imu-attitude');

    // Send IMU data with ~45 degree yaw (quaternion z=0.383, w=0.924)
    await mock.sendToClient({
      op: 'publish',
      topic: '/imu/data',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'imu_link' },
        orientation: { x: 0, y: 0, z: 0.383, w: 0.924 },
        orientation_covariance: [-1, 0, 0, 0, 0, 0, 0, 0, 0],
        angular_velocity: { x: 0, y: 0, z: 0.1 },
        angular_velocity_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
        linear_acceleration: { x: 0, y: 0, z: 9.81 },
        linear_acceleration_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
      },
    });

    await page.waitForTimeout(50);

    // Yaw should be approximately 45 degrees
    const yawValue = imu.locator('#yawValue');
    const yawText = await yawValue.textContent();
    const yawDeg = parseFloat(yawText!.replace('°', ''));
    expect(yawDeg).toBeCloseTo(45.0, 0);

    // Roll and pitch should remain near zero
    const rollValue = imu.locator('#rollValue');
    const rollText = await rollValue.textContent();
    const rollDeg = parseFloat(rollText!.replace('°', ''));
    expect(rollDeg).toBeCloseTo(0, 0);

    const pitchValue = imu.locator('#pitchValue');
    const pitchText = await pitchValue.textContent();
    const pitchDeg = parseFloat(pitchText!.replace('°', ''));
    expect(pitchDeg).toBeCloseTo(0, 0);
  });

  test('updates horizon indicator transform on pitch and roll', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const imu = page.locator('robot-imu-attitude');

    // Send IMU data with roll (rotation around x-axis)
    // quaternion for ~30 deg roll: x=0.259, w=0.966
    await mock.sendToClient({
      op: 'publish',
      topic: '/imu/data',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'imu_link' },
        orientation: { x: 0.259, y: 0, z: 0, w: 0.966 },
        orientation_covariance: [-1, 0, 0, 0, 0, 0, 0, 0, 0],
        angular_velocity: { x: 0, y: 0, z: 0 },
        angular_velocity_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
        linear_acceleration: { x: 0, y: 0, z: 9.81 },
        linear_acceleration_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
      },
    });

    await page.waitForTimeout(50);

    // The horizon sky element should have a transform with a rotation
    const horizonSky = imu.locator('#horizonSky');
    const style = await horizonSky.getAttribute('style');
    expect(style).toContain('rotate(');
    expect(style).toContain('translateY(');
  });

  test('handles identity quaternion (w=1, x=0, y=0, z=0)', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    const imu = page.locator('robot-imu-attitude');

    // Send identity quaternion — should result in all zeros
    await mock.sendToClient({
      op: 'publish',
      topic: '/imu/data',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: 'imu_link' },
        orientation: { x: 0, y: 0, z: 0, w: 1 },
        orientation_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
        angular_velocity: { x: 0, y: 0, z: 0 },
        angular_velocity_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
        linear_acceleration: { x: 0, y: 0, z: 9.81 },
        linear_acceleration_covariance: [0, 0, 0, 0, 0, 0, 0, 0, 0],
      },
    });

    await page.waitForTimeout(50);

    const rollValue = imu.locator('#rollValue');
    const pitchValue = imu.locator('#pitchValue');
    const yawValue = imu.locator('#yawValue');

    await expect(rollValue).toHaveText('0.0°');
    await expect(pitchValue).toHaveText('0.0°');
    await expect(yawValue).toHaveText('0.0°');
  });
});
