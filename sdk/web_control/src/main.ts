// SPDX-License-Identifier: Apache-2.0

import { connection } from './connection';
import { validateEnv } from './env';
import type { ConnectionEvent } from './types';

// Import all Web Components (side-effect: registers custom elements)
import './components/joystick';
import './components/battery-gauge';
import './components/sensor-radar';
import './components/estop-button';
import './components/payload-panel';
import './components/wheel-speeds';
import './components/imu-attitude';
import './components/system-status';
import './components/collection-status';

/**
 * Initialize the control panel application.
 */
function init(): void {
  const env = validateEnv();

  const connectBtn = document.getElementById('connectBtn');
  const wsUrlInput = document.getElementById('wsUrlInput') as HTMLInputElement | null;
  const indicatorDot = document.querySelector('.indicator-dot');
  const indicatorLabel = document.querySelector('.indicator-label');

  if (!connectBtn || !wsUrlInput || !indicatorDot || !indicatorLabel) {
    return;
  }

  if (!wsUrlInput.value) {
    wsUrlInput.value = env.VITE_ROSBRIDGE_URL;
  }

  // Connection state UI updates
  connection.addEventListener('statechange', ((e: CustomEvent<ConnectionEvent>) => {
    const { state } = e.detail;

    indicatorDot.classList.remove('connected');
    connectBtn.classList.remove('active');

    switch (state) {
      case 'connected':
        indicatorDot.classList.add('connected');
        indicatorLabel.textContent = 'Connected';
        connectBtn.textContent = 'Disconnect';
        connectBtn.classList.add('active');
        break;
      case 'connecting':
        indicatorLabel.textContent = 'Connecting...';
        connectBtn.textContent = 'Cancel';
        break;
      case 'disconnected':
        indicatorLabel.textContent = 'Disconnected';
        connectBtn.textContent = 'Connect';
        break;
      case 'error':
        indicatorLabel.textContent = 'Error';
        connectBtn.textContent = 'Retry';
        break;
    }
  }) as EventListener);

  // Connect/disconnect button
  connectBtn.addEventListener('click', () => {
    if (connection.connectionState === 'connected' || connection.connectionState === 'connecting') {
      connection.disconnect();
    } else {
      const url = wsUrlInput.value.trim();
      if (url) {
        connection.connect(url);
      }
    }
  });

  // Allow Enter key to connect
  wsUrlInput.addEventListener('keydown', (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      connectBtn.click();
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
