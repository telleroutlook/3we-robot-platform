// SPDX-License-Identifier: Apache-2.0

import type { PayloadState, PayloadPowerRequest, PayloadPowerResponse } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .payload-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm, 8px);
    padding: var(--space-sm, 8px);
    height: 100%;
  }

  .payload-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .payload-title {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .connection-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-text-muted, #7a8ba5);
    transition: background 0.3s ease;
  }

  .connection-dot.connected {
    background: var(--color-success, #22c55e);
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
  }

  .payload-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .payload-name {
    font-size: var(--text-sm, 13px);
    font-weight: 600;
    color: var(--color-text-primary, #e2e8f0);
  }

  .payload-id {
    font-size: var(--text-2xs, 10px);
    color: var(--color-text-muted, #7a8ba5);
    font-family: var(--font-mono, monospace);
  }

  .payload-power-info {
    font-size: var(--text-2xs, 10px);
    color: var(--color-text-secondary, #94a3b8);
    font-family: var(--font-mono, monospace);
  }

  .rail-toggles {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs, 4px);
    margin-top: auto;
  }

  .rail-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 0;
  }

  .rail-label {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    color: var(--color-text-secondary, #94a3b8);
    font-family: var(--font-mono, monospace);
  }

  .toggle-switch {
    position: relative;
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background: var(--color-surface-alt, #334155);
    border: 1px solid var(--color-border, #2d3f5e);
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .toggle-switch.active {
    background: rgba(59, 130, 246, 0.3);
    border-color: rgba(59, 130, 246, 0.5);
  }

  .toggle-switch::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--color-text-muted, #7a8ba5);
    transition: transform 0.2s ease, background 0.2s ease;
  }

  .toggle-switch.active::after {
    transform: translateX(16px);
    background: var(--color-accent, #3b82f6);
  }

  .no-payload {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: var(--text-xs, 11px);
    color: var(--color-text-muted, #7a8ba5);
    font-style: italic;
  }
</style>

<div class="payload-card">
  <div class="payload-header">
    <span class="payload-title">Payload</span>
    <div class="connection-dot" id="connectionDot"></div>
  </div>

  <div id="payloadContent">
    <div class="no-payload" id="noPayload">No payload connected</div>

    <div class="payload-info hidden" id="payloadInfo">
      <span class="payload-name" id="payloadName">--</span>
      <span class="payload-id" id="payloadId">--</span>
      <span class="payload-power-info" id="payloadPower">-- W</span>
    </div>

    <div class="rail-toggles hidden" id="railToggles">
      <div class="rail-row">
        <span class="rail-label">5V</span>
        <div class="toggle-switch" id="toggle5v" data-rail="5V" role="switch" aria-checked="false" tabindex="0"></div>
      </div>
      <div class="rail-row">
        <span class="rail-label">12V</span>
        <div class="toggle-switch" id="toggle12v" data-rail="12V" role="switch" aria-checked="false" tabindex="0"></div>
      </div>
      <div class="rail-row">
        <span class="rail-label">VBAT</span>
        <div class="toggle-switch" id="toggleVbat" data-rail="VBAT" role="switch" aria-checked="false" tabindex="0"></div>
      </div>
    </div>
  </div>
</div>
`;

export class RobotPayloadPanel extends HTMLElement {
  private connectionDot!: HTMLElement;
  private noPayload!: HTMLElement;
  private payloadInfo!: HTMLElement;
  private railToggles!: HTMLElement;
  private payloadName!: HTMLElement;
  private payloadId!: HTMLElement;
  private payloadPower!: HTMLElement;
  private toggle5v!: HTMLElement;
  private toggle12v!: HTMLElement;
  private toggleVbat!: HTMLElement;
  private unsubscribe: (() => void) | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot!.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    this.connectionDot = this.shadowRoot!.getElementById('connectionDot')!;
    this.noPayload = this.shadowRoot!.getElementById('noPayload')!;
    this.payloadInfo = this.shadowRoot!.getElementById('payloadInfo')!;
    this.railToggles = this.shadowRoot!.getElementById('railToggles')!;
    this.payloadName = this.shadowRoot!.getElementById('payloadName')!;
    this.payloadId = this.shadowRoot!.getElementById('payloadId')!;
    this.payloadPower = this.shadowRoot!.getElementById('payloadPower')!;
    this.toggle5v = this.shadowRoot!.getElementById('toggle5v')!;
    this.toggle12v = this.shadowRoot!.getElementById('toggle12v')!;
    this.toggleVbat = this.shadowRoot!.getElementById('toggleVbat')!;

    this.toggle5v.addEventListener('click', () => this.toggleRail('5V', this.toggle5v));
    this.toggle12v.addEventListener('click', () => this.toggleRail('12V', this.toggle12v));
    this.toggleVbat.addEventListener('click', () => this.toggleRail('VBAT', this.toggleVbat));

    [this.toggle5v, this.toggle12v, this.toggleVbat].forEach(el => {
      el.addEventListener('keydown', (e: KeyboardEvent) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          (e.currentTarget as HTMLElement).click();
        }
      });
    });

    this.unsubscribe = connection.subscribe<PayloadState>(
      '/payload_state',
      'robot_interfaces/PayloadState',
      (msg) => this.onPayloadState(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  private onPayloadState(msg: PayloadState): void {
    if (msg.connected) {
      this.connectionDot.classList.add('connected');
      this.noPayload.classList.add('hidden');
      this.payloadInfo.classList.remove('hidden');
      this.railToggles.classList.remove('hidden');

      this.payloadName.textContent = msg.name || 'Unknown Payload';
      this.payloadId.textContent = msg.payload_id || '';
      this.payloadPower.textContent = `${msg.power_consumption_watts.toFixed(1)} W`;

      this.setToggleState(this.toggle5v, msg.power_5v_active);
      this.setToggleState(this.toggle12v, msg.power_12v_active);
      this.setToggleState(this.toggleVbat, msg.power_vbat_active);
    } else {
      this.connectionDot.classList.remove('connected');
      this.noPayload.classList.remove('hidden');
      this.payloadInfo.classList.add('hidden');
      this.railToggles.classList.add('hidden');
    }
  }

  private setToggleState(el: HTMLElement, active: boolean): void {
    if (active) {
      el.classList.add('active');
      el.setAttribute('aria-checked', 'true');
    } else {
      el.classList.remove('active');
      el.setAttribute('aria-checked', 'false');
    }
  }

  private async toggleRail(
    rail: string,
    toggleEl: HTMLElement
  ): Promise<void> {
    const currentlyActive = toggleEl.classList.contains('active');
    const enable = !currentlyActive;

    // Optimistic update
    this.setToggleState(toggleEl, enable);

    try {
      await connection.callService<PayloadPowerRequest, PayloadPowerResponse>(
        '/payload_power',
        'robot_interfaces/PayloadPower',
        { payload_id: '', rail, enable }
      );
    } catch {
      // Revert on failure
      this.setToggleState(toggleEl, currentlyActive);
    }
  }
}

customElements.define('robot-payload-panel', RobotPayloadPanel);
