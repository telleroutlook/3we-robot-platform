// SPDX-License-Identifier: Apache-2.0

import type { Range } from '../types';
import { connection } from '../connection';

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 200px;
  }

  .radar-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-xs, 4px);
    height: 100%;
    padding: var(--space-sm, 8px);
  }

  .radar-label {
    font-size: var(--text-xs, 11px);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted, #7a8ba5);
  }

  .radar-svg {
    flex: 1;
    width: 100%;
    max-width: 240px;
    max-height: 240px;
  }
</style>

<div class="radar-container">
  <span class="radar-label">Ultrasonic</span>
  <svg class="radar-svg" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <!-- Range rings -->
    <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(100,140,200,0.06)" stroke-width="1"/>
    <circle cx="100" cy="100" r="55" fill="none" stroke="rgba(100,140,200,0.06)" stroke-width="1"/>
    <circle cx="100" cy="100" r="30" fill="none" stroke="rgba(100,140,200,0.06)" stroke-width="1"/>

    <!-- Robot body (top-down view) -->
    <rect x="85" y="85" width="30" height="30" rx="4" fill="rgba(100,140,200,0.15)" stroke="rgba(100,140,200,0.3)" stroke-width="1.5"/>
    <!-- Direction arrow -->
    <polygon points="100,80 96,87 104,87" fill="rgba(59,130,246,0.6)"/>

    <!-- Sensor cones -->
    <path id="coneFront" d="" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.5)" stroke-width="1"/>
    <path id="coneBack" d="" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.5)" stroke-width="1"/>
    <path id="coneLeft" d="" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.5)" stroke-width="1"/>
    <path id="coneRight" d="" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.5)" stroke-width="1"/>

    <!-- Distance labels -->
    <text id="labelFront" x="100" y="28" text-anchor="middle" fill="rgba(148,163,184,0.8)" font-size="9" font-family="var(--font-mono, monospace)">--</text>
    <text id="labelBack" x="100" y="178" text-anchor="middle" fill="rgba(148,163,184,0.8)" font-size="9" font-family="var(--font-mono, monospace)">--</text>
    <text id="labelLeft" x="18" y="104" text-anchor="middle" fill="rgba(148,163,184,0.8)" font-size="9" font-family="var(--font-mono, monospace)">--</text>
    <text id="labelRight" x="182" y="104" text-anchor="middle" fill="rgba(148,163,184,0.8)" font-size="9" font-family="var(--font-mono, monospace)">--</text>
  </svg>
</div>
`;

interface SensorData {
  range: number;
  maxRange: number;
}

export class RobotSensorRadar extends HTMLElement {
  private sensors: Record<string, SensorData> = {
    front: { range: 4.0, maxRange: 4.0 },
    back: { range: 4.0, maxRange: 4.0 },
    left: { range: 4.0, maxRange: 4.0 },
    right: { range: 4.0, maxRange: 4.0 },
  };

  private pendingRender = false;
  private unsubscribers: Array<() => void> = [];

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot!.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback(): void {
    const topics: Array<[string, string]> = [
      ['/ultrasonic/front', 'front'],
      ['/ultrasonic/back', 'back'],
      ['/ultrasonic/left', 'left'],
      ['/ultrasonic/right', 'right'],
    ];

    for (const [topic, direction] of topics) {
      const unsub = connection.subscribe<Range>(
        topic,
        'sensor_msgs/Range',
        (msg) => this.onRange(direction, msg)
      );
      this.unsubscribers.push(unsub);
    }

    this.render();
  }

  disconnectedCallback(): void {
    for (const unsub of this.unsubscribers) {
      unsub();
    }
    this.unsubscribers = [];
  }

  private onRange(direction: string, msg: Range): void {
    const range = (Number.isFinite(msg.range) && msg.range >= 0) ? msg.range : Infinity;
    const maxRange = (Number.isFinite(msg.max_range) && msg.max_range > 0) ? msg.max_range : 4.0;
    this.sensors[direction] = { range, maxRange };
    if (!this.pendingRender) {
      this.pendingRender = true;
      requestAnimationFrame(() => {
        this.pendingRender = false;
        this.render();
      });
    }
  }

  private render(): void {
    this.drawCone('Front', 'front', 0, -1);
    this.drawCone('Back', 'back', 0, 1);
    this.drawCone('Left', 'left', -1, 0);
    this.drawCone('Right', 'right', 1, 0);
  }

  private drawCone(id: string, direction: string, dirX: number, dirY: number): void {
    const cone = this.shadowRoot!.getElementById(`cone${id}`);
    const label = this.shadowRoot!.getElementById(`label${id}`);
    if (!cone || !label) return;

    const data = this.sensors[direction];
    const normalized = Math.min(data.range / data.maxRange, 1.0);
    const length = normalized * 55; // max visual range in SVG units

    const cx = 100;
    const cy = 100;
    const startOffset = 18; // start outside robot body

    // Cone spread angle (30 degrees each side)
    const spreadAngle = Math.PI / 6;
    const baseAngle = Math.atan2(dirY, dirX);

    const startX = cx + dirX * startOffset;
    const startY = cy + dirY * startOffset;

    const endX1 = startX + Math.cos(baseAngle - spreadAngle) * length;
    const endY1 = startY + Math.sin(baseAngle - spreadAngle) * length;
    const endX2 = startX + Math.cos(baseAngle + spreadAngle) * length;
    const endY2 = startY + Math.sin(baseAngle + spreadAngle) * length;

    cone.setAttribute('d', `M${startX},${startY} L${endX1},${endY1} L${endX2},${endY2} Z`);

    // Color by distance
    const color = this.getDistanceColor(data.range);
    cone.setAttribute('fill', color.fill);
    cone.setAttribute('stroke', color.stroke);

    // Update label
    label.textContent = data.range < data.maxRange ? data.range.toFixed(2) : '--';
  }

  private getDistanceColor(range: number): { fill: string; stroke: string } {
    if (!Number.isFinite(range)) {
      return { fill: 'rgba(34,197,94,0.15)', stroke: 'rgba(34,197,94,0.4)' };
    }
    if (range < 0.15) {
      return { fill: 'rgba(239,68,68,0.3)', stroke: 'rgba(239,68,68,0.7)' };
    }
    if (range < 0.4) {
      return { fill: 'rgba(245,158,11,0.25)', stroke: 'rgba(245,158,11,0.6)' };
    }
    return { fill: 'rgba(34,197,94,0.15)', stroke: 'rgba(34,197,94,0.4)' };
  }
}

customElements.define('robot-sensor-radar', RobotSensorRadar);
