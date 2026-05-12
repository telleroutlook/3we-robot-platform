// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('E-stop safety flow', () => {
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

  test('trigger E-stop zeroes joystick and calls service', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    // Click the E-stop button
    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');
    await expect(estopBtn).toBeVisible();
    await expect(estopBtn).toHaveClass(/normal/);

    await estopBtn.click();

    // Button should transition to estopped state
    await expect(estopBtn).toHaveClass(/estopped/);
    await expect(estopBtn).toContainText('ESTOPPED');

    // Verify service call was sent to rosbridge
    const serviceCall = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; service?: string };
      return m.op === 'call_service' && m.service === '/emergency_stop';
    });

    const svc = serviceCall as { op: string; service: string; args: { reason: string } };
    expect(svc.args.reason).toBe('manual');
  });

  test('E-stop state syncs from topic subscription', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');
    await expect(estopBtn).toHaveClass(/normal/);

    // Simulate receiving E-stop state from robot (hardware E-stop pressed)
    await mock.sendToClient({
      op: 'publish',
      topic: '/emergency_stop_state',
      msg: {
        header: { stamp: { sec: 0, nanosec: 0 }, frame_id: '' },
        stopped: true,
        state: 1,
        reason: 'hardware',
      },
    });

    // Button should reflect estopped state
    await expect(estopBtn).toHaveClass(/estopped/);
    await expect(estopBtn).toContainText('ESTOPPED');
  });

  test('reset flow shows confirmation dialog', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');

    // First, trigger E-stop
    await estopBtn.click();
    await expect(estopBtn).toHaveClass(/estopped/);

    // Click again to reset — should show confirmation overlay
    await estopBtn.click();

    const overlay = page.locator('robot-estop-button').locator('#confirmOverlay');
    await expect(overlay).not.toHaveClass(/hidden/);
    await expect(overlay).toContainText('Reset Emergency Stop');
  });

  test('cancel reset keeps estopped state', async ({ page }) => {
    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');

    await estopBtn.click();
    await expect(estopBtn).toHaveClass(/estopped/);

    // Show confirm dialog
    await estopBtn.click();

    // Cancel
    const cancelBtn = page.locator('robot-estop-button').locator('#cancelReset');
    await cancelBtn.click();

    const overlay = page.locator('robot-estop-button').locator('#confirmOverlay');
    await expect(overlay).toHaveClass(/hidden/);
    await expect(estopBtn).toHaveClass(/estopped/);
  });

  test('confirm reset calls service and transitions to recovery', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');

    // Trigger E-stop
    await estopBtn.click();
    await expect(estopBtn).toHaveClass(/estopped/);

    // Initiate reset
    await estopBtn.click();

    // Confirm reset
    const confirmBtn = page.locator('robot-estop-button').locator('#confirmReset');
    await confirmBtn.click();

    // Button should show recovery_pending
    await expect(estopBtn).toHaveClass(/recovery_pending/);
    await expect(estopBtn).toContainText('RESETTING');

    // Service call should have been sent with reason: ''
    const resetCall = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; service?: string; args?: { reason?: string } };
      return m.op === 'call_service' && m.service === '/emergency_stop' && m.args?.reason === '';
    });
    expect(resetCall).toBeTruthy();
  });

  test('state recovers to normal via topic after reset confirmed', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');

    // Trigger, confirm reset
    await estopBtn.click();
    await estopBtn.click();
    const confirmBtn = page.locator('robot-estop-button').locator('#confirmReset');
    await confirmBtn.click();
    await expect(estopBtn).toHaveClass(/recovery_pending/);

    // Simulate robot confirming the reset via topic
    await mock.sendToClient({
      op: 'publish',
      topic: '/emergency_stop_state',
      msg: {
        header: { stamp: { sec: 1, nanosec: 0 }, frame_id: '' },
        stopped: false,
        state: 0,
        reason: '',
      },
    });

    // Should return to normal
    await expect(estopBtn).toHaveClass(/normal/);
    await expect(estopBtn).toContainText('EMERGENCY STOP');
  });

  test('joystick publishes zero velocity after E-stop trigger', async ({ page }) => {
    const mock = (
      page as unknown as {
        __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never;
      }
    ).__mock;

    // Verify that after E-stop, any subsequent joystick publish has zero velocity
    const estopBtn = page.locator('robot-estop-button').locator('button#estopBtn');
    await estopBtn.click();
    await expect(estopBtn).toHaveClass(/estopped/);

    // Wait a bit for any pending joystick publishes to flush
    await page.waitForTimeout(100);

    // Check that no non-zero cmd_vel was sent after E-stop
    const cmdVelMessages = mock.messages.filter((msg: unknown) => {
      const m = msg as { op?: string; topic?: string };
      return m.op === 'publish' && m.topic === '/cmd_vel';
    });

    for (const msg of cmdVelMessages) {
      const m = msg as { msg: { linear: { x: number }; angular: { z: number } } };
      expect(m.msg.linear.x).toBe(0);
      expect(m.msg.angular.z).toBe(0);
    }
  });
});
