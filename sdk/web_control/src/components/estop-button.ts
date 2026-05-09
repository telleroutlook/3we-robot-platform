// SPDX-License-Identifier: Apache-2.0

import type { EmergencyStopState } from '../types';
import { connection } from '../connection';

type EstopVisualState = 'normal' | 'estopped' | 'recovery_pending';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .estop-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: var(--space-xs, 4px);
  }

  .estop-btn {
    position: relative;
    width: 100%;
    max-width: 320px;
    height: 56px;
    border: none;
    border-radius: var(--radius-md, 8px);
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    cursor: pointer;
    transition: transform 80ms ease, box-shadow 120ms ease;
    outline: none;
    font-family: inherit;
  }

  .estop-btn:focus-visible {
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
  }

  .estop-btn:active {
    transform: scale(0.97);
  }

  /* Normal state — green outline, ready to stop */
  .estop-btn.normal {
    background: rgba(34, 197, 94, 0.08);
    color: var(--color-success, #22c55e);
    border: 2px solid var(--color-success, #22c55e);
    box-shadow: 0 0 12px rgba(34, 197, 94, 0.15);
  }

  .estop-btn.normal:hover {
    background: rgba(34, 197, 94, 0.14);
    box-shadow: 0 0 20px rgba(34, 197, 94, 0.25);
  }

  /* ESTOPPED — pulsing red */
  .estop-btn.estopped {
    background: var(--color-danger, #ef4444);
    color: #fff;
    border: 2px solid var(--color-danger, #ef4444);
    box-shadow: 0 0 24px rgba(239, 68, 68, 0.4);
    animation: pulse-estop 1s ease-in-out infinite;
  }

  /* Recovery pending — amber */
  .estop-btn.recovery_pending {
    background: rgba(245, 158, 11, 0.15);
    color: var(--color-warning, #f59e0b);
    border: 2px solid var(--color-warning, #f59e0b);
    box-shadow: 0 0 16px rgba(245, 158, 11, 0.2);
    animation: pulse-recovery 1.5s ease-in-out infinite;
  }

  @keyframes pulse-estop {
    0%, 100% { box-shadow: 0 0 24px rgba(239, 68, 68, 0.4); }
    50% { box-shadow: 0 0 40px rgba(239, 68, 68, 0.7); }
  }

  @keyframes pulse-recovery {
    0%, 100% { box-shadow: 0 0 16px rgba(245, 158, 11, 0.2); }
    50% { box-shadow: 0 0 28px rgba(245, 158, 11, 0.4); }
  }

  .confirm-overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 15, 30, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    backdrop-filter: blur(4px);
  }

  .confirm-dialog {
    background: var(--color-surface-elevated, #1e293b);
    border: 1px solid var(--color-border, #2d3f5e);
    border-radius: var(--radius-lg, 12px);
    padding: var(--space-lg, 24px);
    max-width: 360px;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: var(--space-md, 16px);
  }

  .confirm-title {
    font-size: var(--text-md, 15px);
    font-weight: 700;
    color: var(--color-text-primary, #e2e8f0);
  }

  .confirm-message {
    font-size: var(--text-sm, 13px);
    color: var(--color-text-secondary, #94a3b8);
    line-height: 1.5;
  }

  .confirm-actions {
    display: flex;
    gap: var(--space-sm, 8px);
    justify-content: center;
  }

  .confirm-actions button {
    padding: 8px 20px;
    border-radius: var(--radius-sm, 6px);
    font-size: var(--text-sm, 13px);
    font-weight: 600;
    cursor: pointer;
    border: none;
    font-family: inherit;
  }

  .btn-cancel {
    background: var(--color-surface-alt, #334155);
    color: var(--color-text-secondary, #94a3b8);
  }

  .btn-confirm {
    background: var(--color-success, #22c55e);
    color: #fff;
  }

  .hidden {
    display: none;
  }
</style>

<div class="estop-wrapper">
  <button class="estop-btn normal" id="estopBtn" aria-label="Emergency Stop">
    EMERGENCY STOP
  </button>
</div>

<div class="confirm-overlay hidden" id="confirmOverlay">
  <div class="confirm-dialog">
    <div class="confirm-title">Reset Emergency Stop?</div>
    <div class="confirm-message">
      Confirm that it is safe to resume robot operation. Ensure the area is clear before resetting.
    </div>
    <div class="confirm-actions">
      <button class="btn-cancel" id="cancelReset">Cancel</button>
      <button class="btn-confirm" id="confirmReset">Reset &amp; Resume</button>
    </div>
  </div>
</div>
`;

export class RobotEstopButton extends HTMLElement {
  private btn!: HTMLButtonElement;
  private overlay!: HTMLElement;
  private _visualState: EstopVisualState = 'normal';
  private estopped = false;
  private unsubscribe: (() => void) | null = null;

  get visualState(): EstopVisualState {
    return this._visualState;
  }

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    shadow.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    const shadow = this.shadowRoot;
    if (!shadow) return;
    this.btn = shadow.getElementById('estopBtn') as HTMLButtonElement;
    this.overlay = shadow.getElementById('confirmOverlay') as HTMLElement;
    const cancelBtn = shadow.getElementById('cancelReset') as HTMLElement;
    const confirmBtn = shadow.getElementById('confirmReset') as HTMLElement;

    this.btn.addEventListener('click', () => this.onButtonClick());
    cancelBtn.addEventListener('click', () => this.hideConfirm());
    confirmBtn.addEventListener('click', () => this.doReset());

    this.unsubscribe = connection.subscribe<EmergencyStopState>(
      '/emergency_stop_state',
      'robot_interfaces/EmergencyStopState',
      (msg) => this.onEstopState(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
  }

  private onButtonClick(): void {
    if (!this.estopped) {
      this.triggerEstop();
    } else {
      this.showConfirm();
    }
  }

  private async triggerEstop(): Promise<void> {
    this.estopped = true;
    this.setVisualState('estopped');

    // Notify all listeners (joystick, etc.) to halt immediately
    document.dispatchEvent(new CustomEvent('robot-estop', { detail: { estopped: true } }));

    try {
      await connection.callService('/emergency_stop', 'std_srvs/SetBool', { data: true });
    } catch {
      // Even if service call fails, keep local E-stop state
    }
  }

  private showConfirm(): void {
    this.overlay.classList.remove('hidden');
  }

  private hideConfirm(): void {
    this.overlay.classList.add('hidden');
  }

  private async doReset(): Promise<void> {
    this.hideConfirm();
    this.setVisualState('recovery_pending');

    try {
      await connection.callService('/emergency_stop', 'std_srvs/SetBool', { data: false });
      // State will be cleared by onEstopState when topic confirms
    } catch {
      // Remain in estopped state on failure
      this.setVisualState('estopped');
    }
  }

  private onEstopState(msg: EmergencyStopState): void {
    this.estopped = msg.stopped;
    if (msg.stopped) {
      this.setVisualState('estopped');
    } else {
      this.setVisualState('normal');
    }
  }

  private setVisualState(state: EstopVisualState): void {
    this._visualState = state;
    this.btn.classList.remove('normal', 'estopped', 'recovery_pending');
    this.btn.classList.add(state);

    switch (state) {
      case 'normal':
        this.btn.textContent = 'EMERGENCY STOP';
        break;
      case 'estopped':
        this.btn.textContent = 'ESTOPPED — TAP TO RESET';
        break;
      case 'recovery_pending':
        this.btn.textContent = 'RESETTING...';
        break;
    }
  }
}

customElements.define('robot-estop-button', RobotEstopButton);
