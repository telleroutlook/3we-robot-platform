// SPDX-License-Identifier: Apache-2.0

import type { BatteryState } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .battery-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm, 8px);
    padding: var(--space-sm, 8px);
    height: 100%;
  }

  .battery-header {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .battery-visual {
    display: flex;
    align-items: center;
    gap: var(--space-sm, 8px);
  }

  .battery-icon {
    position: relative;
    width: 48px;
    height: 24px;
    border: 2px solid var(--color-border, #2d3f5e);
    border-radius: 4px;
  }

  .battery-icon::after {
    content: '';
    position: absolute;
    right: -5px;
    top: 6px;
    width: 3px;
    height: 10px;
    background: var(--color-border, #2d3f5e);
    border-radius: 0 2px 2px 0;
  }

  .battery-fill {
    position: absolute;
    left: 2px;
    top: 2px;
    bottom: 2px;
    border-radius: 2px;
    transition: width 0.3s ease, background 0.3s ease;
    width: 0%;
    background: var(--color-success, #22c55e);
  }

  .battery-fill.low {
    background: var(--color-warning, #f59e0b);
  }

  .battery-fill.critical {
    background: var(--color-danger, #ef4444);
  }

  .battery-pct {
    font-size: var(--text-lg, 20px);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-primary, #e2e8f0);
  }

  .battery-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-xs, 4px);
  }

  .detail-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .detail-label {
    font-size: var(--text-2xs, 10px);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .detail-value {
    font-size: var(--text-sm, 13px);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--color-text-secondary, #94a3b8);
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: var(--text-2xs, 10px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .status-badge.ok {
    background: rgba(34, 197, 94, 0.12);
    color: var(--color-success, #22c55e);
  }

  .status-badge.low {
    background: rgba(245, 158, 11, 0.12);
    color: var(--color-warning, #f59e0b);
  }

  .status-badge.critical {
    background: rgba(239, 68, 68, 0.12);
    color: var(--color-danger, #ef4444);
  }
</style>

<div class="battery-card">
  <span class="battery-header">Battery</span>
  <div class="battery-visual">
    <div class="battery-icon">
      <div class="battery-fill" id="batteryFill"></div>
    </div>
    <span class="battery-pct" id="batteryPct">--%</span>
    <span class="status-badge ok" id="statusBadge">OK</span>
  </div>
  <div class="battery-details">
    <div class="detail-item">
      <span class="detail-label">Voltage</span>
      <span class="detail-value" id="voltage">--</span>
    </div>
    <div class="detail-item">
      <span class="detail-label">Current</span>
      <span class="detail-value" id="current">--</span>
    </div>
  </div>
</div>
`;

export class RobotBatteryGauge extends HTMLElement {
  private fillEl!: HTMLElement;
  private pctEl!: HTMLElement;
  private statusEl!: HTMLElement;
  private voltageEl!: HTMLElement;
  private currentEl!: HTMLElement;
  private unsubscribe: (() => void) | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot!.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    this.fillEl = this.shadowRoot!.getElementById('batteryFill')!;
    this.pctEl = this.shadowRoot!.getElementById('batteryPct')!;
    this.statusEl = this.shadowRoot!.getElementById('statusBadge')!;
    this.voltageEl = this.shadowRoot!.getElementById('voltage')!;
    this.currentEl = this.shadowRoot!.getElementById('current')!;

    this.unsubscribe = connection.subscribe<BatteryState>(
      '/battery_state',
      'sensor_msgs/BatteryState',
      (msg) => this.onBatteryUpdate(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  private onBatteryUpdate(msg: BatteryState): void {
    const pct = Math.round((msg.percentage ?? 0) * 100);
    const voltage = msg.voltage ?? 0;
    const current = msg.current ?? 0;

    this.pctEl.textContent = `${pct}%`;
    this.voltageEl.textContent = `${voltage.toFixed(1)} V`;
    this.currentEl.textContent = `${current.toFixed(2)} A`;

    // Fill bar — max width is container width minus 4px padding
    const fillPct = Math.max(0, Math.min(100, pct));
    this.fillEl.style.width = `${fillPct}%`;

    // Status classification
    this.fillEl.classList.remove('low', 'critical');
    this.statusEl.classList.remove('ok', 'low', 'critical');

    if (pct <= 10) {
      this.fillEl.classList.add('critical');
      this.statusEl.classList.add('critical');
      this.statusEl.textContent = 'CRITICAL';
    } else if (pct <= 25) {
      this.fillEl.classList.add('low');
      this.statusEl.classList.add('low');
      this.statusEl.textContent = 'LOW';
    } else {
      this.statusEl.classList.add('ok');
      this.statusEl.textContent = 'OK';
    }
  }
}

customElements.define('robot-battery-gauge', RobotBatteryGauge);
