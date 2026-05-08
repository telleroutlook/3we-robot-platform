// SPDX-License-Identifier: Apache-2.0

import type { Imu, Quaternion } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .imu-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm, 8px);
    padding: var(--space-sm, 8px);
    height: 100%;
  }

  .imu-header {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .imu-content {
    display: flex;
    gap: var(--space-md, 16px);
    align-items: center;
    flex: 1;
  }

  .horizon-container {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    border: 2px solid var(--color-border, #2d3f5e);
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
  }

  .horizon-sky {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, rgba(59,130,246,0.2) 0%, rgba(59,130,246,0.05) 100%);
    transition: transform 0.15s ease;
    transform-origin: center center;
  }

  .horizon-ground {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 50%;
    background: linear-gradient(to bottom, rgba(139,92,46,0.15) 0%, rgba(139,92,46,0.3) 100%);
    transition: transform 0.15s ease;
    transform-origin: center top;
  }

  .horizon-center {
    position: absolute;
    top: 50%;
    left: 10%;
    right: 10%;
    height: 2px;
    background: rgba(245, 158, 11, 0.6);
    transform: translateY(-50%);
  }

  .horizon-wings {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 24px;
    height: 2px;
    background: var(--color-text-primary, #e2e8f0);
    border-radius: 1px;
  }

  .horizon-wings::before,
  .horizon-wings::after {
    content: '';
    position: absolute;
    top: -4px;
    width: 2px;
    height: 10px;
    background: var(--color-text-primary, #e2e8f0);
    border-radius: 1px;
  }

  .horizon-wings::before {
    left: 0;
  }

  .horizon-wings::after {
    right: 0;
  }

  .attitude-values {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs, 4px);
    flex: 1;
  }

  .attitude-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .attitude-label {
    font-size: var(--text-2xs, 10px);
    font-weight: 600;
    text-transform: uppercase;
    color: var(--color-text-muted, #7a8ba5);
  }

  .attitude-value {
    font-size: var(--text-sm, 13px);
    font-weight: 600;
    font-family: var(--font-mono, monospace);
    font-variant-numeric: tabular-nums;
    color: var(--color-text-secondary, #94a3b8);
  }
</style>

<div class="imu-card">
  <span class="imu-header">IMU Attitude</span>
  <div class="imu-content">
    <div class="horizon-container">
      <div class="horizon-sky" id="horizonSky"></div>
      <div class="horizon-ground" id="horizonGround"></div>
      <div class="horizon-center"></div>
      <div class="horizon-wings"></div>
    </div>
    <div class="attitude-values">
      <div class="attitude-row">
        <span class="attitude-label">Roll</span>
        <span class="attitude-value" id="rollValue">0.0&deg;</span>
      </div>
      <div class="attitude-row">
        <span class="attitude-label">Pitch</span>
        <span class="attitude-value" id="pitchValue">0.0&deg;</span>
      </div>
      <div class="attitude-row">
        <span class="attitude-label">Yaw</span>
        <span class="attitude-value" id="yawValue">0.0&deg;</span>
      </div>
    </div>
  </div>
</div>
`;

export class RobotImuAttitude extends HTMLElement {
  private horizonSky!: HTMLElement;
  private horizonGround!: HTMLElement;
  private rollEl!: HTMLElement;
  private pitchEl!: HTMLElement;
  private yawEl!: HTMLElement;
  private unsubscribe: (() => void) | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot!.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    this.horizonSky = this.shadowRoot!.getElementById('horizonSky')!;
    this.horizonGround = this.shadowRoot!.getElementById('horizonGround')!;
    this.rollEl = this.shadowRoot!.getElementById('rollValue')!;
    this.pitchEl = this.shadowRoot!.getElementById('pitchValue')!;
    this.yawEl = this.shadowRoot!.getElementById('yawValue')!;

    this.unsubscribe = connection.subscribe<Imu>(
      '/imu/data',
      'sensor_msgs/Imu',
      (msg) => this.onImuData(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  private onImuData(msg: Imu): void {
    const { roll, pitch, yaw } = this.quaternionToEuler(msg.orientation);

    const rollDeg = this.radToDeg(roll);
    const pitchDeg = this.radToDeg(pitch);
    const yawDeg = this.radToDeg(yaw);

    this.rollEl.textContent = `${rollDeg.toFixed(1)}°`;
    this.pitchEl.textContent = `${pitchDeg.toFixed(1)}°`;
    this.yawEl.textContent = `${yawDeg.toFixed(1)}°`;

    // Update horizon indicator
    // Clamp pitch for visual offset, roll for rotation
    const pitchOffset = Math.max(-30, Math.min(30, pitchDeg));
    const rollClamped = Math.max(-45, Math.min(45, rollDeg));

    this.horizonSky.style.transform = `rotate(${rollClamped}deg) translateY(${pitchOffset}%)`;
    this.horizonGround.style.transform = `rotate(${rollClamped}deg) translateY(${-pitchOffset}%)`;
  }

  private quaternionToEuler(q: Quaternion): { roll: number; pitch: number; yaw: number } {
    const { x, y, z, w } = q;

    // Roll (x-axis rotation)
    const sinrCosp = 2.0 * (w * x + y * z);
    const cosrCosp = 1.0 - 2.0 * (x * x + y * y);
    const roll = Math.atan2(sinrCosp, cosrCosp);

    // Pitch (y-axis rotation)
    const sinp = 2.0 * (w * y - z * x);
    let pitch: number;
    if (Math.abs(sinp) >= 1) {
      pitch = Math.sign(sinp) * (Math.PI / 2);
    } else {
      pitch = Math.asin(sinp);
    }

    // Yaw (z-axis rotation)
    const sinyCosp = 2.0 * (w * z + x * y);
    const cosyCosp = 1.0 - 2.0 * (y * y + z * z);
    const yaw = Math.atan2(sinyCosp, cosyCosp);

    return { roll, pitch, yaw };
  }

  private radToDeg(rad: number): number {
    return rad * (180 / Math.PI);
  }
}

customElements.define('robot-imu-attitude', RobotImuAttitude);
