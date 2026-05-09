// SPDX-License-Identifier: Apache-2.0

import { connection } from '../connection';

interface DiagnosticStatus {
  name: string;
  level: number;
  message: string;
  values: Record<string, string>;
}

interface DiagnosticArray {
  status: DiagnosticStatus[];
}

const LEVEL_OK = 0;
const LEVEL_WARN = 1;
const LEVEL_ERROR = 2;
const LEVEL_STALE = 3;

export class RobotSystemStatus extends HTMLElement {
  private unsubscribe: (() => void) | null = null;
  private statuses: DiagnosticStatus[] = [];
  private lastUpdate = 0;
  private staleTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback(): void {
    this.render();

    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    if (this.staleTimer !== null) {
      clearInterval(this.staleTimer);
      this.staleTimer = null;
    }

    this.subscribeToDiagnostics();

    this.staleTimer = setInterval(() => {
      if (this.lastUpdate > 0 && Date.now() - this.lastUpdate > 5000) {
        this.setAttribute('data-stale', 'true');
      }
    }, 2000);
  }

  disconnectedCallback(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    if (this.staleTimer) {
      clearInterval(this.staleTimer);
      this.staleTimer = null;
    }
  }

  private subscribeToDiagnostics(): void {
    this.unsubscribe = connection.subscribe<DiagnosticArray>(
      '/diagnostics',
      'diagnostic_msgs/msg/DiagnosticArray',
      (msg) => {
        if (!Array.isArray(msg.status)) return;
        this.statuses = msg.status;
        this.lastUpdate = Date.now();
        this.removeAttribute('data-stale');
        this.updateDisplay();
      }
    );
  }

  private updateDisplay(): void {
    const container = this.shadowRoot?.querySelector('.system-status__grid');
    if (!container) return;

    container.innerHTML = '';

    for (const status of this.statuses) {
      const item = document.createElement('div');
      item.className = 'system-status__item';
      item.setAttribute('data-level', this.levelToString(status.level));

      const name = document.createElement('span');
      name.className = 'system-status__name';
      name.textContent = status.name.split('/').pop() || status.name;

      const message = document.createElement('span');
      message.className = 'system-status__message';
      message.textContent = status.message;

      item.appendChild(name);
      item.appendChild(message);
      container.appendChild(item);
    }
  }

  private levelToString(level: number): string {
    switch (level) {
      case LEVEL_OK:
        return 'ok';
      case LEVEL_WARN:
        return 'warn';
      case LEVEL_ERROR:
        return 'error';
      case LEVEL_STALE:
        return 'stale';
      default:
        return 'unknown';
    }
  }

  private render(): void {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `
      <style>
        .system-status { padding: 0.5rem; }
        .system-status__title {
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.5rem;
          opacity: 0.7;
        }
        .system-status__grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 0.375rem;
        }
        .system-status__item {
          display: flex;
          flex-direction: column;
          padding: 0.375rem 0.5rem;
          border-radius: 4px;
          border-left: 3px solid var(--status-color, #888);
          background: var(--color-surface-raised, #f5f5f5);
          font-size: 0.75rem;
        }
        .system-status__item[data-level="ok"] { --status-color: #22c55e; }
        .system-status__item[data-level="warn"] { --status-color: #f59e0b; }
        .system-status__item[data-level="error"] { --status-color: #ef4444; }
        .system-status__item[data-level="stale"] { --status-color: #94a3b8; }
        .system-status__name {
          font-weight: 600;
          text-transform: capitalize;
        }
        .system-status__message {
          opacity: 0.8;
          font-size: 0.675rem;
        }
        :host([data-stale]) .system-status__grid { opacity: 0.5; }
      </style>
      <div class="system-status">
        <div class="system-status__title">System Health</div>
        <div class="system-status__grid"></div>
      </div>
    `;
  }
}

customElements.define('robot-system-status', RobotSystemStatus);
