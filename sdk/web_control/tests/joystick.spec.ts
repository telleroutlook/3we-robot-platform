// SPDX-License-Identifier: Apache-2.0
import { test, expect } from '@playwright/test';
import { setupMockRosbridge } from './mock-rosbridge';

test.describe('Joystick component', () => {
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

  test('component renders with canvas element', async ({ page }) => {
    const joystick = page.locator('robot-joystick');
    await expect(joystick).toBeVisible();

    const canvas = joystick.locator('canvas#canvas');
    await expect(canvas).toBeVisible();
  });

  test('velocity readout displays initial zero values', async ({ page }) => {
    const joystick = page.locator('robot-joystick');

    const vx = joystick.locator('#vxValue');
    const vz = joystick.locator('#vzValue');

    await expect(vx).toHaveText('0.00');
    await expect(vz).toHaveText('0.00');
  });

  test('joystick publishes cmd_vel on pointer interaction', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    // Dispatch pointer events directly on the shadow DOM canvas
    await page.evaluate(() => {
      const joystick = document.querySelector('robot-joystick')!;
      const canvas = joystick.shadowRoot!.getElementById('canvas')!;
      const rect = canvas.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;

      canvas.dispatchEvent(new PointerEvent('pointerdown', {
        clientX: cx, clientY: cy, bubbles: true, pointerId: 1
      }));
      canvas.dispatchEvent(new PointerEvent('pointermove', {
        clientX: cx, clientY: cy - rect.height * 0.3, bubbles: true, pointerId: 1
      }));
    });

    await page.waitForTimeout(100);

    // Look for a cmd_vel publish message with non-zero linear.x
    const cmdVel = await mock.waitForMessage((msg: unknown) => {
      const m = msg as { op?: string; topic?: string; msg?: { linear?: { x?: number } } };
      return (
        m.op === 'publish' &&
        m.topic === '/cmd_vel' &&
        m.msg?.linear?.x !== undefined &&
        m.msg.linear.x !== 0
      );
    });

    expect(cmdVel).toBeTruthy();

    await page.evaluate(() => {
      const joystick = document.querySelector('robot-joystick')!;
      const canvas = joystick.shadowRoot!.getElementById('canvas')!;
      canvas.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 1 }));
    });
  });

  test('releasing joystick sends zero velocity', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    const canvas = page.locator('robot-joystick').locator('canvas#canvas');
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();

    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    // Drag joystick up
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx, cy - box!.height * 0.3);
    await page.waitForTimeout(60);

    // Release
    await page.mouse.up();
    await page.waitForTimeout(100); // wait for publish cycle after release

    // The last cmd_vel messages after release should be zero
    const zeroMsg = mock.messages
      .filter((msg: unknown) => {
        const m = msg as { op?: string; topic?: string };
        return m.op === 'publish' && m.topic === '/cmd_vel';
      })
      .pop() as { msg: { linear: { x: number }; angular: { z: number } } } | undefined;

    expect(zeroMsg).toBeTruthy();
    expect(zeroMsg!.msg.linear.x).toBe(0);
    expect(zeroMsg!.msg.angular.z).toBe(0);
  });

  test('dead zone prevents publishing non-zero velocity for small movements', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    const canvas = page.locator('robot-joystick').locator('canvas#canvas');
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();

    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    // Clear messages before this interaction
    mock.messages.length = 0;

    // Very small movement (within dead zone of 0.08)
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    // Move only 1-2 pixels — well within dead zone
    await page.mouse.move(cx + 1, cy - 1);
    await page.waitForTimeout(100);
    await page.mouse.up();
    await page.waitForTimeout(60);

    // All cmd_vel messages should have zero linear.x and angular.z
    const cmdVelMsgs = mock.messages.filter((msg: unknown) => {
      const m = msg as { op?: string; topic?: string };
      return m.op === 'publish' && m.topic === '/cmd_vel';
    });

    for (const msg of cmdVelMsgs) {
      const m = msg as { msg: { linear: { x: number }; angular: { z: number } } };
      expect(m.msg.linear.x).toBe(0);
      expect(m.msg.angular.z).toBe(0);
    }
  });

  test('linear velocity is capped at maxLinearVel (0.35 m/s)', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    const canvas = page.locator('robot-joystick').locator('canvas#canvas');
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();

    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    // Drag joystick all the way to the top edge (maximum displacement)
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx, box!.y); // top edge of canvas
    await page.waitForTimeout(100);

    // Find cmd_vel messages and verify linear.x is within bounds
    const cmdVelMsgs = mock.messages.filter((msg: unknown) => {
      const m = msg as { op?: string; topic?: string };
      return m.op === 'publish' && m.topic === '/cmd_vel';
    });

    for (const msg of cmdVelMsgs) {
      const m = msg as { msg: { linear: { x: number } } };
      expect(Math.abs(m.msg.linear.x)).toBeLessThanOrEqual(0.35 + 0.001);
    }

    await page.mouse.up();
  });

  test('angular velocity is capped at maxAngularVel (2.5 rad/s)', async ({ page }) => {
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;

    const canvas = page.locator('robot-joystick').locator('canvas#canvas');
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();

    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    // Drag joystick all the way to the left edge (maximum angular displacement)
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(box!.x, cy); // left edge of canvas
    await page.waitForTimeout(100);

    // Find cmd_vel messages and verify angular.z is within bounds
    const cmdVelMsgs = mock.messages.filter((msg: unknown) => {
      const m = msg as { op?: string; topic?: string };
      return m.op === 'publish' && m.topic === '/cmd_vel';
    });

    for (const msg of cmdVelMsgs) {
      const m = msg as { msg: { angular: { z: number } } };
      expect(Math.abs(m.msg.angular.z)).toBeLessThanOrEqual(2.5 + 0.001);
    }

    await page.mouse.up();
  });

  test('no non-zero cmd_vel published when disconnected', async ({ page }) => {
    // Disconnect first
    const disconnectBtn = page.locator('#disconnectBtn');
    if (await disconnectBtn.isVisible()) {
      await disconnectBtn.click();
    }
    await page.waitForTimeout(50);

    // Now interact with joystick
    const mock = (page as unknown as { __mock: ReturnType<typeof setupMockRosbridge> extends Promise<infer T> ? T : never }).__mock;
    mock.messages.length = 0;

    const canvas = page.locator('robot-joystick').locator('canvas#canvas');
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();

    const cx = box!.x + box!.width / 2;
    const cy = box!.y + box!.height / 2;

    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx, cy - box!.height * 0.3);
    await page.waitForTimeout(100);
    await page.mouse.up();

    // No cmd_vel messages should have been sent (ws.send throws when not connected)
    const cmdVelMsgs = mock.messages.filter((msg: unknown) => {
      const m = msg as { op?: string; topic?: string; msg?: { linear?: { x?: number } } };
      return m.op === 'publish' && m.topic === '/cmd_vel' && m.msg?.linear?.x !== 0;
    });

    expect(cmdVelMsgs.length).toBe(0);
  });

  test('velocity readout updates with current values during interaction', async ({ page }) => {
    const vx = page.locator('robot-joystick').locator('#vxValue');
    const vz = page.locator('robot-joystick').locator('#vzValue');

    // Initial state
    await expect(vx).toHaveText('0.00');
    await expect(vz).toHaveText('0.00');

    // Dispatch pointer events directly on shadow DOM canvas
    await page.evaluate(() => {
      const joystick = document.querySelector('robot-joystick')!;
      const canvas = joystick.shadowRoot!.getElementById('canvas')!;
      const rect = canvas.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;

      canvas.dispatchEvent(new PointerEvent('pointerdown', {
        clientX: cx, clientY: cy, bubbles: true, pointerId: 1
      }));
      canvas.dispatchEvent(new PointerEvent('pointermove', {
        clientX: cx + rect.width * 0.2, clientY: cy - rect.height * 0.3, bubbles: true, pointerId: 1
      }));
    });

    await page.waitForTimeout(50);

    // Readout should now show non-zero values
    const vxText = await vx.textContent();
    const vzText = await vz.textContent();
    const vxNum = parseFloat(vxText ?? '0');
    const vzNum = parseFloat(vzText ?? '0');

    // At least one of them should be non-zero after significant drag
    expect(Math.abs(vxNum) + Math.abs(vzNum)).toBeGreaterThan(0);

    await page.evaluate(() => {
      const joystick = document.querySelector('robot-joystick')!;
      const canvas = joystick.shadowRoot!.getElementById('canvas')!;
      canvas.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 1 }));
    });
  });
});
