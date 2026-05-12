// SPDX-License-Identifier: Apache-2.0

import type { CollectionState } from '../types';
import { connection } from '../connection';
import { collectionStateSchema } from '../schemas';

const STAGE_LABELS: Record<number, string> = {
  0: 'IDLE',
  1: 'SEARCHING',
  2: 'APPROACHING',
  3: 'PICKING',
  4: 'RETURNING',
  5: 'DUMPING',
};

const STAGE_COLORS: Record<number, string> = {
  0: 'var(--color-text-muted, #7a8ba5)',
  1: 'var(--color-accent, #3b82f6)',
  2: 'var(--color-warning, #f59e0b)',
  3: 'var(--color-success, #22c55e)',
  4: 'var(--color-warning, #f59e0b)',
  5: 'var(--color-danger, #ef4444)',
};

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
  }

  .collection-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm, 8px);
    padding: var(--space-sm, 8px);
    height: 100%;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-title {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .state-badge {
    font-size: var(--text-2xs, 10px);
    font-weight: 700;
    padding: 2px 6px;
    border-radius: var(--radius-sm, 4px);
    color: #fff;
    background: var(--color-text-muted, #7a8ba5);
    transition: background 0.3s ease;
  }

  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-xs, 4px);
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .stat-label {
    font-size: var(--text-2xs, 10px);
    color: var(--color-text-muted, #7a8ba5);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .stat-value {
    font-size: var(--text-md, 16px);
    font-weight: 700;
    font-family: var(--font-mono, 'SF Mono', monospace);
    color: var(--color-text-primary, #e2e8f0);
  }

  .stage-flow {
    display: flex;
    gap: 2px;
    align-items: center;
  }

  .stage-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-surface-alt, #2a3441);
    transition: background 0.3s ease, transform 0.2s ease;
  }

  .stage-dot.active {
    transform: scale(1.3);
  }

  .stage-connector {
    flex: 1;
    height: 2px;
    background: var(--color-surface-alt, #2a3441);
  }

  .controls {
    display: flex;
    gap: var(--space-xs, 4px);
    margin-top: auto;
  }

  .btn {
    flex: 1;
    padding: 6px 12px;
    border: none;
    border-radius: var(--radius-sm, 4px);
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s ease;
  }

  .btn:hover {
    opacity: 0.85;
  }

  .btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .btn--start {
    background: var(--color-success, #22c55e);
    color: #fff;
  }

  .btn--stop {
    background: var(--color-danger, #ef4444);
    color: #fff;
  }
</style>

<div class="collection-card">
  <div class="card-header">
    <span class="card-title">Collection</span>
    <span class="state-badge" id="stateBadge">IDLE</span>
  </div>

  <div class="stats">
    <div class="stat-item">
      <span class="stat-label">In basket</span>
      <span class="stat-value" id="basketCount">0</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">Total</span>
      <span class="stat-value" id="totalCount">0</span>
    </div>
  </div>

  <div class="stage-flow" id="stageFlow">
    <span class="stage-dot" data-stage="1"></span>
    <span class="stage-connector"></span>
    <span class="stage-dot" data-stage="2"></span>
    <span class="stage-connector"></span>
    <span class="stage-dot" data-stage="3"></span>
    <span class="stage-connector"></span>
    <span class="stage-dot" data-stage="4"></span>
    <span class="stage-connector"></span>
    <span class="stage-dot" data-stage="5"></span>
  </div>

  <div class="controls">
    <button class="btn btn--start" id="startBtn">Start</button>
    <button class="btn btn--stop" id="stopBtn" disabled>Stop</button>
  </div>
</div>
`;

export class RobotCollectionStatus extends HTMLElement {
  private stateBadge!: HTMLElement;
  private basketCount!: HTMLElement;
  private totalCount!: HTMLElement;
  private stageFlow!: HTMLElement;
  private startBtn!: HTMLButtonElement;
  private stopBtn!: HTMLButtonElement;
  private unsubscribe: (() => void) | null = null;

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: 'open' });
    shadow.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    const shadow = this.shadowRoot;
    if (!shadow) return;

    this.stateBadge = shadow.getElementById('stateBadge') as HTMLElement;
    this.basketCount = shadow.getElementById('basketCount') as HTMLElement;
    this.totalCount = shadow.getElementById('totalCount') as HTMLElement;
    this.stageFlow = shadow.getElementById('stageFlow') as HTMLElement;
    this.startBtn = shadow.getElementById('startBtn') as HTMLButtonElement;
    this.stopBtn = shadow.getElementById('stopBtn') as HTMLButtonElement;

    this.startBtn.addEventListener('click', this.onStart);
    this.stopBtn.addEventListener('click', this.onStop);

    this.unsubscribe = connection.safeSubscribe(
      '/collection/state',
      'robot_interfaces/msg/CollectionState',
      collectionStateSchema,
      (msg: CollectionState) => this.onStateUpdate(msg)
    );
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    this.startBtn?.removeEventListener('click', this.onStart);
    this.stopBtn?.removeEventListener('click', this.onStop);
  }

  private onStateUpdate(msg: CollectionState): void {
    this.stateBadge.textContent = STAGE_LABELS[msg.state] ?? 'UNKNOWN';
    this.stateBadge.style.background = STAGE_COLORS[msg.state] ?? STAGE_COLORS[0];

    this.basketCount.textContent = String(msg.balls_in_basket);
    this.totalCount.textContent = String(msg.total_collected);

    const dots = this.stageFlow.querySelectorAll('.stage-dot');
    dots.forEach((dot) => {
      const stage = Number((dot as HTMLElement).dataset.stage);
      dot.classList.toggle('active', stage === msg.state);
      (dot as HTMLElement).style.background =
        stage <= msg.state
          ? (STAGE_COLORS[stage] ?? STAGE_COLORS[0])
          : 'var(--color-surface-alt, #2a3441)';
    });

    this.startBtn.disabled = msg.state !== 0;
    this.stopBtn.disabled = msg.state === 0;
  }

  private onStart = (): void => {
    connection.publish('/collection/command', 'std_msgs/String', {
      data: 'start',
    });
  };

  private onStop = (): void => {
    connection.publish('/collection/command', 'std_msgs/String', {
      data: 'stop',
    });
  };
}

customElements.define('robot-collection-status', RobotCollectionStatus);
