# Performance Benchmarks and Stability Testing

## Control Loop Benchmarks

### Target Specifications

| Metric | Target | Method |
|--------|--------|--------|
| Motor PWM update rate | 50 Hz | LEDC timer measurement |
| Odometry publish rate | 50 Hz | ROS2 topic Hz monitor |
| Ultrasonic scan cycle | 10 Hz (2.5 Hz/sensor) | Timer ISR measurement |
| IMU data rate | 100 Hz | I2C transaction timing |
| cmd_vel → motor latency | < 20 ms | GPIO toggle measurement |
| E-stop response time | < 5 ms | ISR + relay timing |

### Measurement Procedure

#### 1. Control Loop Jitter

```bash
# On companion computer, monitor topic rates
ros2 topic hz /odom --window 100
ros2 topic hz /cmd_vel --window 100

# Expected output:
# /odom: average rate: 50.0 Hz, min: 19.5ms, max: 20.5ms, std dev: 0.3ms
```

#### 2. End-to-End Latency

Hardware setup: Connect GPIO test pin to oscilloscope.

```c
// In firmware, toggle test pin on cmd_vel receive and motor update
gpio_set_level(TEST_PIN, 1);  // On cmd_vel callback
// ... process ...
gpio_set_level(TEST_PIN, 0);  // After motor PWM set
```

Measure pulse width on oscilloscope. Target: < 20ms (1 control cycle).

#### 3. E-Stop Response Time

Test procedure:
1. Robot moving at maximum speed (1.2 m/s)
2. Press E-stop button
3. Measure time from button press to motor current = 0

Equipment: Current probe on motor leads + E-stop GPIO signal.

Expected: < 5ms (single ISR latency + relay activation).

#### 4. Wi-Fi Latency (DTLS)

```bash
# On client machine
python3 -c "
import socket, time, struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
robot_ip = '192.168.1.100'

for i in range(100):
    t0 = time.monotonic_ns()
    sock.sendto(b'PING' + struct.pack('Q', t0), (robot_ip, 8888))
    data, addr = sock.recvfrom(256)
    rtt = (time.monotonic_ns() - t0) / 1e6
    print(f'RTT: {rtt:.2f} ms')
"
```

Target RTT: < 10ms on local network, < 50ms on congested Wi-Fi.

---

## Stability Test Suite

### Test 1: 24-Hour Continuous Operation

**Purpose**: Verify no memory leaks, task starvation, or watchdog resets.

**Procedure**:
1. Power on robot with all systems active
2. Run continuous cmd_vel at 0.5 m/s in square pattern
3. Monitor for 24 hours
4. Log: free heap, task stack watermarks, restart count

**Pass criteria**:
- Zero unplanned restarts
- Free heap drift < 1 KB/hour
- No task stack overflow warnings
- All sensor topics maintain rated Hz ±5%

**Monitoring script**:
```bash
#!/bin/bash
# Run on companion computer
LOG="stability_$(date +%Y%m%d_%H%M%S).csv"
echo "timestamp,heap_free,stack_min,odom_hz,temp_c" > "$LOG"

while true; do
    HEAP=$(ros2 topic echo /diagnostics --once | grep heap_free | awk '{print $2}')
    STACK=$(ros2 topic echo /diagnostics --once | grep stack_min | awk '{print $2}')
    ODOM_HZ=$(ros2 topic hz /odom --window 10 2>&1 | grep average | awk '{print $4}')
    TEMP=$(ros2 topic echo /thermal --once | grep temp | awk '{print $2}')
    echo "$(date +%s),$HEAP,$STACK,$ODOM_HZ,$TEMP" >> "$LOG"
    sleep 60
done
```

### Test 2: Payload Hot-Plug Stress

**Purpose**: Verify reliable hot-plug detection and power sequencing.

**Procedure**:
1. Insert/remove payload module 100 times
2. Vary insertion speed (slow: 2s, fast: 0.1s)
3. Record success/failure for each cycle

**Pass criteria**:
- 100% detection rate for properly-seated insertions
- Zero false positives from partial insertions (debounce working)
- Power sequencing timing within spec (5V before 12V, 10ms ramp)
- No EEPROM read failures on valid modules

### Test 3: Wi-Fi Reconnection

**Purpose**: Verify automatic recovery from Wi-Fi drops.

**Procedure**:
1. Establish DTLS connection
2. Disable AP for 5 seconds
3. Re-enable AP
4. Verify reconnection and command resumption

**Pass criteria**:
- Robot stops within watchdog timeout (500ms) on disconnect
- Reconnection within 10 seconds of AP availability
- No stale commands executed after reconnection
- Session keys renegotiated on reconnect

### Test 4: Thermal Stress

**Purpose**: Verify thermal protection under sustained load.

**Procedure**:
1. Run all 4 motors at 100% duty cycle
2. Monitor INA219 power readings
3. Continue until thermal warning triggers

**Pass criteria**:
- Warning triggers before junction temp estimate > 70°C
- Shutdown triggers before > 85°C
- Motors stop within 1 control cycle of shutdown
- Recovery after cool-down is automatic

### Test 5: Battery Depletion

**Purpose**: Verify graceful shutdown at low battery.

**Procedure**:
1. Run robot until battery reaches 10% SOC
2. Verify low-battery warning published
3. Continue until critical threshold (5%)

**Pass criteria**:
- Low battery warning at 10% SOC
- Motor power reduced at 8% SOC
- Graceful shutdown initiated at 5% SOC
- No data corruption or brown-out resets

### Test 6: Concurrent Payload + Navigation

**Purpose**: Verify payload I2C traffic doesn't interfere with control.

**Procedure**:
1. Active navigation (Nav2) running
2. Payload performing continuous I2C transactions (100 bytes/s)
3. Run for 1 hour

**Pass criteria**:
- Odometry jitter < 2ms (no I2C bus starvation)
- IMU update rate maintained at 100Hz
- Payload transactions complete without CRC errors
- No navigation drift from delayed encoder reads

---

## Benchmark Results Template

```
Robot Platform Performance Report
=================================
Date:       YYYY-MM-DD
FW Version: x.y.z
SKU:        [Basic|Standard|Pro|Industrial]
Tester:     [Name]

Motor PWM Rate:     ___ Hz (target: 50)
Odom Publish Rate:  ___ Hz (target: 50)
cmd_vel Latency:    ___ ms (target: <20)
E-Stop Response:    ___ ms (target: <5)
Wi-Fi RTT:          ___ ms (target: <10)
Free Heap (start):  ___ bytes
Free Heap (24h):    ___ bytes
Heap Drift:         ___ bytes/hr (target: <1024)
24h Restarts:       ___ (target: 0)
Hot-plug Success:   ___/100 (target: 100/100)
Thermal Warning @:  ___°C (target: <70)
Thermal Shutdown @: ___°C (target: <85)

RESULT: [PASS|FAIL]
Notes:
```
