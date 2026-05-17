// SPDX-License-Identifier: Apache-2.0

import type { Twist } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 240px;
  }

  .joystick-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: var(--space-sm, 8px);
  }

  .joystick-label {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  canvas {
    touch-action: none;
    border-radius: 50%;
    cursor: grab;
  }

  canvas:active {
    cursor: grabbing;
  }

  .velocity-readout {
    display: flex;
    gap: var(--space-md, 16px);
    font-size: var(--text-xs, 11px);
    font-family: var(--font-mono, 'IBM Plex Mono', 'SF Mono', monospace);
    color: var(--color-text-secondary, #94a3b8);
  }

  .velocity-readout span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .vel-label {
    color: var(--color-text-muted, #7a8ba5);
  }
</style>

<div class="joystick-container">
  <span class="joystick-label">Teleop</span>
  <canvas id="canvas" width="220" height="220"></canvas>
  <div class="velocity-readout">
    <span><span class="vel-label">Vx:</span> <span id="vxValue">0.00</span></span>
    <span><span class="vel-label">Vz:</span> <span id="vzValue">0.00</span></span>
  </div>
</div>
`;

export class RobotJoystick extends HTMLElement {
  private canvas!: HTMLCanvasElement;
  private ctx!: CanvasRenderingContext2D;
  private vxEl!: HTMLElement;
  private vzEl!: HTMLElement;

  private centerX = 110;
  private centerY = 110;
  private baseRadius = 90;
  private knobRadius = 28;
  private deadZone = 0.08;

  private knobX = 0;
  private knobY = 0;
  private alive = false;
  private active = false;
  private publishTimer: ReturnType<typeof setInterval> | null = null;
  private animFrame: number | null = null;

  private currentVx = 0;
  private currentOmega = 0;

  private maxLinearVel = 0.5;
  private maxAngularVel = 1.0;

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    shadow.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    this.alive = true;
    const shadow = this.shadowRoot;
    if (!shadow) return;
    this.canvas = shadow.getElementById('canvas') as HTMLCanvasElement;
    const ctx = this.canvas.getContext('2d');
    if (!ctx) return;
    this.ctx = ctx;
    this.vxEl = shadow.getElementById('vxValue') as HTMLElement;
    this.vzEl = shadow.getElementById('vzValue') as HTMLElement;

    this.canvas.addEventListener('pointerdown', this.onPointerDown);
    this.canvas.addEventListener('pointermove', this.onPointerMove);
    this.canvas.addEventListener('pointerup', this.onPointerEnd);
    this.canvas.addEventListener('pointercancel', this.onPointerEnd);
    this.canvas.addEventListener('pointerleave', this.onPointerEnd);

    document.addEventListener('robot-estop', this.onEstop);

    this.startPublishing();
    if (this.animFrame !== null) {
      cancelAnimationFrame(this.animFrame);
      this.animFrame = null;
    }
    this.draw();
  }

  private onEstop = (): void => {
    this.stop();
  };

  public stop(): void {
    this.active = false;
    this.knobX = 0;
    this.knobY = 0;
    this.currentVx = 0;
    this.currentOmega = 0;
    this.updateReadout();
  }

  disconnectedCallback(): void {
    this.alive = false;
    this.stopPublishing();
    if (this.animFrame !== null) {
      cancelAnimationFrame(this.animFrame);
      this.animFrame = null;
    }
    document.removeEventListener('robot-estop', this.onEstop);
    this.canvas.removeEventListener('pointerdown', this.onPointerDown);
    this.canvas.removeEventListener('pointermove', this.onPointerMove);
    this.canvas.removeEventListener('pointerup', this.onPointerEnd);
    this.canvas.removeEventListener('pointercancel', this.onPointerEnd);
    this.canvas.removeEventListener('pointerleave', this.onPointerEnd);
  }

  private onPointerDown = (e: PointerEvent): void => {
    this.active = true;
    this.canvas.setPointerCapture(e.pointerId);
    this.updateKnob(e);
  };

  private onPointerMove = (e: PointerEvent): void => {
    if (!this.active) return;
    this.updateKnob(e);
  };

  private onPointerEnd = (): void => {
    this.active = false;
    this.knobX = 0;
    this.knobY = 0;
    this.currentVx = 0;
    this.currentOmega = 0;
    this.updateReadout();
    this.publishZero();
  };

  private updateKnob(e: PointerEvent): void {
    const rect = this.canvas.getBoundingClientRect();
    const scaleX = this.canvas.width / rect.width;
    const scaleY = this.canvas.height / rect.height;

    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;

    let dx = px - this.centerX;
    let dy = py - this.centerY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const maxDist = this.baseRadius - this.knobRadius;

    if (dist > maxDist) {
      dx = (dx / dist) * maxDist;
      dy = (dy / dist) * maxDist;
    }

    this.knobX = dx / maxDist;
    this.knobY = dy / maxDist;

    // Apply dead zone
    const mag = Math.sqrt(this.knobX * this.knobX + this.knobY * this.knobY);
    if (mag < this.deadZone) {
      this.knobX = 0;
      this.knobY = 0;
    }

    // Map: Y-up = forward (linear.x), X-right = turn right (negative angular.z)
    this.currentVx = -this.knobY * this.maxLinearVel;
    this.currentOmega = -this.knobX * this.maxAngularVel;
    this.updateReadout();
  }

  private updateReadout(): void {
    this.vxEl.textContent = this.currentVx.toFixed(2);
    this.vzEl.textContent = this.currentOmega.toFixed(2);
  }

  private draw = (): void => {
    if (!this.alive) return;
    this.animFrame = requestAnimationFrame(this.draw);
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Base ring
    ctx.beginPath();
    ctx.arc(this.centerX, this.centerY, this.baseRadius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(100, 140, 200, 0.15)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Cross hairs
    ctx.beginPath();
    ctx.moveTo(this.centerX, this.centerY - this.baseRadius + 10);
    ctx.lineTo(this.centerX, this.centerY + this.baseRadius - 10);
    ctx.moveTo(this.centerX - this.baseRadius + 10, this.centerY);
    ctx.lineTo(this.centerX + this.baseRadius - 10, this.centerY);
    ctx.strokeStyle = 'rgba(100, 140, 200, 0.08)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Knob position
    const maxDist = this.baseRadius - this.knobRadius;
    const kx = this.centerX + this.knobX * maxDist;
    const ky = this.centerY + this.knobY * maxDist;

    // Line from center to knob
    if (this.active) {
      ctx.beginPath();
      ctx.moveTo(this.centerX, this.centerY);
      ctx.lineTo(kx, ky);
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Knob
    const gradient = ctx.createRadialGradient(kx, ky, 0, kx, ky, this.knobRadius);
    if (this.active) {
      gradient.addColorStop(0, 'rgba(59, 130, 246, 0.9)');
      gradient.addColorStop(1, 'rgba(37, 99, 235, 0.7)');
    } else {
      gradient.addColorStop(0, 'rgba(100, 140, 200, 0.5)');
      gradient.addColorStop(1, 'rgba(80, 120, 180, 0.3)');
    }

    ctx.beginPath();
    ctx.arc(kx, ky, this.knobRadius, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.strokeStyle = this.active ? 'rgba(59, 130, 246, 0.8)' : 'rgba(100, 140, 200, 0.3)';
    ctx.lineWidth = 2;
    ctx.stroke();
  };

  private publishZero(): void {
    const msg: Twist = {
      linear: { x: 0, y: 0, z: 0 },
      angular: { x: 0, y: 0, z: 0 },
    };
    connection.publish('/cmd_vel', 'geometry_msgs/Twist', msg);
  }

  private startPublishing(): void {
    this.stopPublishing();
    // Publish at 20 Hz
    this.publishTimer = setInterval(() => {
      if (!this.active && this.currentVx === 0 && this.currentOmega === 0) return;
      const msg: Twist = {
        linear: { x: this.currentVx, y: 0, z: 0 },
        angular: { x: 0, y: 0, z: this.currentOmega },
      };
      connection.publish('/cmd_vel', 'geometry_msgs/Twist', msg);
    }, 50);
  }

  private stopPublishing(): void {
    if (this.publishTimer !== null) {
      clearInterval(this.publishTimer);
      this.publishTimer = null;
    }
  }
}

customElements.define('robot-joystick', RobotJoystick);
