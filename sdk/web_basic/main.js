// SPDX-License-Identifier: Apache-2.0
// Robot Platform Web Teleop - rosbridge WebSocket client

class RobotConnection {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.subscribers = {};
        this.publishInterval = null;
        this.cmdVel = { linear: { x: 0, y: 0, z: 0 }, angular: { x: 0, y: 0, z: 0 } };
    }

    connect(url) {
        if (this.ws) this.disconnect();

        this.ws = new WebSocket(url);
        this.ws.onopen = () => {
            this.connected = true;
            document.getElementById('statusDot').classList.add('connected');
            this.subscribe('/battery_state', 'sensor_msgs/BatteryState', this.onBattery);
            this.subscribe('/ultrasonic/front', 'sensor_msgs/Range', (msg) => this.onRange('Front', msg));
            this.subscribe('/ultrasonic/back', 'sensor_msgs/Range', (msg) => this.onRange('Back', msg));
            this.subscribe('/ultrasonic/left', 'sensor_msgs/Range', (msg) => this.onRange('Left', msg));
            this.subscribe('/ultrasonic/right', 'sensor_msgs/Range', (msg) => this.onRange('Right', msg));
            this.startPublishing();
        };

        this.ws.onclose = () => {
            this.connected = false;
            document.getElementById('statusDot').classList.remove('connected');
            this.stopPublishing();
            setTimeout(() => this.connect(url), 3000);
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.op === 'publish' && this.subscribers[msg.topic]) {
                this.subscribers[msg.topic](msg.msg);
            }
        };

        this.ws.onerror = () => {};
    }

    disconnect() {
        this.stopPublishing();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
    }

    subscribe(topic, type, callback) {
        this.subscribers[topic] = callback;
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                op: 'subscribe', topic: topic, type: type
            }));
        }
    }

    publish(topic, type, msg) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                op: 'publish', topic: topic, type: type, msg: msg
            }));
        }
    }

    startPublishing() {
        this.publishInterval = setInterval(() => {
            this.publish('/cmd_vel', 'geometry_msgs/Twist', this.cmdVel);
        }, 50); // 20 Hz
    }

    stopPublishing() {
        if (this.publishInterval) {
            clearInterval(this.publishInterval);
            this.publishInterval = null;
        }
    }

    setCmdVel(vx, vy, omega) {
        const scale = parseInt(document.getElementById('speedSlider').value) / 100.0;
        const maxV = 0.35;
        const maxW = 2.5;
        this.cmdVel.linear.x = vx * scale * maxV;
        this.cmdVel.linear.y = vy * scale * maxV;
        this.cmdVel.angular.z = omega * scale * maxW;
    }

    stop() {
        this.cmdVel.linear.x = 0;
        this.cmdVel.linear.y = 0;
        this.cmdVel.angular.z = 0;
    }

    onBattery(msg) {
        const voltage = msg.voltage ? msg.voltage.toFixed(1) + 'V' : '--';
        const pct = msg.percentage ? Math.round(msg.percentage * 100) + '%' : '--%';
        document.getElementById('battVoltage').textContent = voltage;
        document.getElementById('battLevel').textContent = pct;
    }

    onRange(direction, msg) {
        const dist = msg.range ? msg.range.toFixed(2) : '--';
        document.getElementById('dist' + direction).textContent = dist;

        const bar = document.getElementById('dist' + direction + 'Bar');
        const pct = Math.min(100, (msg.range / 4.0) * 100);
        bar.style.width = pct + '%';
        bar.className = 'distance-fill';
        if (msg.range < 0.1) bar.classList.add('danger');
        else if (msg.range < 0.3) bar.classList.add('warn');
    }
}

// Joystick controller
class Joystick {
    constructor(areaEl, baseEl, knobEl, onMove) {
        this.area = areaEl;
        this.base = baseEl;
        this.knob = knobEl;
        this.onMove = onMove;
        this.active = false;
        this.baseRect = null;

        this.area.addEventListener('pointerdown', (e) => this.start(e));
        this.area.addEventListener('pointermove', (e) => this.move(e));
        this.area.addEventListener('pointerup', () => this.end());
        this.area.addEventListener('pointercancel', () => this.end());
    }

    start(e) {
        this.active = true;
        this.baseRect = this.base.getBoundingClientRect();
        this.area.setPointerCapture(e.pointerId);
        this.move(e);
    }

    move(e) {
        if (!this.active || !this.baseRect) return;

        const centerX = this.baseRect.left + this.baseRect.width / 2;
        const centerY = this.baseRect.top + this.baseRect.height / 2;
        const radius = this.baseRect.width / 2 - 30;

        let dx = e.clientX - centerX;
        let dy = e.clientY - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist > radius) {
            dx = (dx / dist) * radius;
            dy = (dy / dist) * radius;
        }

        this.knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;

        // Normalize to [-1, 1]: x = forward (up), y = left (left)
        const normX = -dy / radius;  // Forward is up (negative Y)
        const normY = -dx / radius;  // Left is negative X

        this.onMove(normX, normY);
    }

    end() {
        this.active = false;
        this.knob.style.transform = 'translate(-50%, -50%)';
        this.onMove(0, 0);
    }
}

// Global state
const robot = new RobotConnection();
let estopped = false;

const joystick = new Joystick(
    document.getElementById('joystickArea'),
    document.getElementById('joystickBase'),
    document.getElementById('joystickKnob'),
    (vx, vy) => {
        if (!estopped) {
            robot.setCmdVel(vx, vy, 0);
        }
    }
);

// Speed slider
document.getElementById('speedSlider').addEventListener('input', (e) => {
    document.getElementById('speedValue').textContent = e.target.value + '%';
});

// E-stop
function toggleEstop() {
    estopped = !estopped;
    const btn = document.getElementById('estopBtn');
    if (estopped) {
        robot.stop();
        btn.textContent = 'RESET (Click to Resume)';
        btn.classList.add('active');
    } else {
        btn.textContent = 'EMERGENCY STOP';
        btn.classList.remove('active');
    }
}

// Connection
function toggleConnection() {
    if (robot.connected) {
        robot.disconnect();
    } else {
        const url = document.getElementById('wsUrl').value;
        robot.connect(url);
    }
}

// Keyboard controls (WASD + QE for rotation)
document.addEventListener('keydown', (e) => {
    if (estopped) return;
    switch (e.key.toLowerCase()) {
        case 'w': robot.setCmdVel(1, 0, 0); break;
        case 's': robot.setCmdVel(-1, 0, 0); break;
        case 'a': robot.setCmdVel(0, 1, 0); break;
        case 'd': robot.setCmdVel(0, -1, 0); break;
        case 'q': robot.setCmdVel(0, 0, 1); break;
        case 'e': robot.setCmdVel(0, 0, -1); break;
        case ' ': toggleEstop(); break;
    }
});

document.addEventListener('keyup', (e) => {
    if ('wasdeq'.includes(e.key.toLowerCase())) {
        robot.stop();
    }
});
