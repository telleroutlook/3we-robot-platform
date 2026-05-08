// SPDX-License-Identifier: Apache-2.0

import type { WheelSpeeds } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .wheel-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm, 8px);
    padding: var(--space-sm, 8px);
    height: 100%;
  }

  .wheel-header {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .wheel-bars {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs, 4px);
    flex: 1;
    justify-content: center;
  }

  .wheel-row {
    display: flex;
    align-items: center;
    gap: var(--space-sm, 8px);
  }

  .wheel-label {
    font-size: var(--text-2xs, 10px);
    font-weight: 600;
    color: var(--color-text-muted, #7a8ba5);
    width: 20px;
    text-align: right;
    font-family: var(--font-mono, monospace);
  }

  .bar-track {
    flex: 1;
    height: 12px;
    background: var(--color-surface-alt, #1e293b);
    border-radius: 3px;
    position: relative;
    overflow: hidden;
  }

  .bar-center {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--color-border, #2d3f5e);
  }

  .bar-fill {
    position: absolute;
    top: 1px;
    bottom: 1px;
    border-radius: 2px;
    transition: left 0.1s ease, width 0.1s ease, background 0.1s ease;
  }

  .bar-fill.forward {
    background: var(--color-accent, #3b82f6);
  }

  .bar-fill.reverse {
    background: var(--color-warning, #f59e0b);
  }

  .wheel-value {
    font-size: var(--text-2xs, 10px);
    font-weight: 600;
    font-family: var(--font-mono, monospace);
    color: var(--color-text-secondary, #94a3b8);
    width: 36px;
    text-align: left;
    font-variant-numeric: tabular-nums;
  }
</style>

<div class="wheel-card">
  <span class="wheel-header">Wheel Speeds</span>
  <div class="wheel-bars">
    <div class="wheel-row">
      <span class="wheel-label">FL</span>
      <div class="bar-track"><div class="bar-center"></div><div class="bar-fill" id="barFL"></div></div>
      <span class="wheel-value" id="valFL">0.00</span>
    </div>
    <div class="wheel-row">
      <span class="wheel-label">FR</span>
      <div class="bar-track"><div class="bar-center"></div><div class="bar-fill" id="barFR"></div></div>
      <span class="wheel-value" id="valFR">0.00</span>
    </div>
    <div class="wheel-row">
      <span class="wheel-label">RL</span>
      <div class="bar-track"><div class="bar-center"></div><div class="bar-fill" id="barRL"></div></div>
      <span class="wheel-value" id="valRL">0.00</span>
    </div>
    <div class="wheel-row">
      <span class="wheel-label">RR</span>
      <div class="bar-track"><div class="bar-center"></div><div class="bar-fill" id="barRR"></div></div>
      <span class="wheel-value" id="valRR">0.00</span>
    </div>
  </div>
</div>
`;

export class RobotWheelSpeeds extends HTMLElement {
  private bars: Record<string, HTMLElement> = {};
  private values: Record<string, HTMLElement> = {};
  private unsubscribe: (() => void) | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot!.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    const wheels = ['FL', 'FR', 'RL', 'RR'];
    for (const w of wheels) {
      this.bars[w] = this.shadowRoot!.getElementById(`bar${w}`)!;
      this.values[w] = this.shadowRoot!.getElementById(`val${w}`)!;
    }

    this.unsubscribe = connection.subscribe<WheelSpeeds>(
      '/wheel_speeds',
      'robot_interfaces/WheelSpeeds',
      (msg) => this.onWheelSpeeds(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  private onWheelSpeeds(msg: WheelSpeeds): void {
    this.updateBar('FL', msg.front_left);
    this.updateBar('FR', msg.front_right);
    this.updateBar('RL', msg.rear_left);
    this.updateBar('RR', msg.rear_right);
  }

  private updateBar(wheel: string, speed: number): void {
    const bar = this.bars[wheel];
    const val = this.values[wheel];
    if (!bar || !val) return;

    // Clamp to [-1, 1]
    const clamped = Math.max(-1, Math.min(1, speed));
    val.textContent = clamped.toFixed(2);

    // Calculate position: center is 50%, positive goes right, negative goes left
    const absWidth = Math.abs(clamped) * 50; // percentage of half-width

    bar.classList.remove('forward', 'reverse');

    if (clamped >= 0) {
      bar.classList.add('forward');
      bar.style.left = '50%';
      bar.style.width = `${absWidth}%`;
    } else {
      bar.classList.add('reverse');
      bar.style.left = `${50 - absWidth}%`;
      bar.style.width = `${absWidth}%`;
    }
  }
}

customElements.define('robot-wheel-speeds', RobotWheelSpeeds);
