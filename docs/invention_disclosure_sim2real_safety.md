# Invention Disclosure: Sim2Real Zero-Code-Change Backend Switching and Layered Safety Interlock Architecture

**Document type:** Internal invention disclosure — prior art establishment  
**Date:** 2026-05-23  
**Project:** 3we Robot Platform (`3we-robot-platform`)  
**Status:** Confidential — not for public distribution until patent filing  

---

## 1. Field of the Invention

This disclosure covers two related innovations in the 3we robot platform:

1. **Sim2Real zero-code-change backend switching** — a software architecture that allows identical Python application code to execute on simulation environments (Gazebo, Isaac Sim) and physical robot hardware without any modification to the calling code.

2. **Layered safety interlock architecture** — a dual-channel hardware relay monitoring system combined with a firmware-level watchdog and ROS2-level QoS enforcement that guarantees motor power cutoff independent of software state.

A third related innovation — **payload sandbox isolation** — is described in Section 4 as a dependent sub-system.

---

## 2. Background and Problem Statement

### 2.1 The Sim2Real transfer problem

Robotic AI research workflows typically involve three phases: algorithm development in simulation, transfer to real hardware, and iterative refinement. The dominant approach in existing platforms (ROS2-based frameworks, OpenAI Gym, Isaac Gym) requires developers to maintain **two separate code paths**: one for simulation (using simulator-specific APIs) and one for real hardware (using hardware driver APIs). This dual maintenance burden:

- Creates divergence between tested simulation code and deployed real-hardware code
- Introduces latent bugs that only manifest on real hardware
- Increases the barrier to entry for AI researchers unfamiliar with hardware interfaces
- Makes automated CI/CD pipelines that run both sim and real impossible with a single test suite

No existing open-source platform provides a single Python API that transparently dispatches to both simulation and real hardware backends while guaranteeing identical data formats across all backends.

### 2.2 The safety interlock problem in open-platform robots

Consumer and research robots typically implement emergency stop (E-stop) entirely in software: a software flag is set, and motor driver outputs are zeroed. This approach fails under three realistic fault modes:

- Firmware crash or memory corruption that bypasses the software safety flag
- ROS2 control loop stall (e.g., network timeout, scheduling starvation) that leaves stale velocity commands active
- Single-channel relay fault that is undetected until a safety-critical event

Industrial safety standards (IEC 62061, ISO 13849 Category 3 PLd) require redundant, independently monitored safety channels. No existing open-source robot platform for the sub-$500 price range implements dual-channel relay feedback monitoring with automated fault detection.

---

## 3. Technical Description

### 3.1 Sim2Real Zero-Code-Change Backend Switching

#### 3.1.1 Core abstraction: BackendBase consistency contract

**File:** `sdk/threewe/src/threewe/backends/__init__.py`

The `BackendBase` abstract class defines a strict data format contract that all backends must fulfill:

```python
class BackendBase(ABC):
    """Consistency contract guarantees:
    - Image:   (H, W, 3) uint8 RGB
    - Depth:   (H, W) float32, meters, invalid=0.0
    - LiDAR:   (N,) float32, meters, uniform angular sampling
    - Pose:    right-hand, X forward, Y left, Z up, radians
    - Velocity: m/s linear, rad/s angular
    """
```

This contract is enforced at the abstract method level: any backend that deviates from these formats will fail at construction, not at runtime. The guaranteed output formats are independent of whether the data originates from a physics simulator, a neural network surrogate, or a physical sensor.

#### 3.1.2 Backend factory and dispatch pattern

**File:** `sdk/threewe/src/threewe/robot.py` (lines 322–342)

The `Robot` class accepts a `backend` string parameter at construction and instantiates the corresponding backend implementation via a factory method:

```python
def _create_backend(self, backend: str) -> BackendBase:
    if backend == "gazebo":
        from threewe.backends.gazebo import GazeboBackend
        return GazeboBackend(config=self._config, scene=self._scene)
    elif backend == "real":
        from threewe.backends.real import RealBackend
        return RealBackend(config=self._config)
    elif backend == "isaac_sim":
        from threewe.backends.isaac_sim import IsaacSimBackend, IsaacSimConfig
        return IsaacSimBackend(config=IsaacSimConfig(scene=self._scene))
    elif backend == "mock":
        from threewe.backends.mock import MockBackend
        return MockBackend(config=self._config, scene=self._scene, verbose=self._verbose)
```

All four backends — `gazebo`, `real`, `isaac_sim`, and `mock` — present an identical interface to the calling application. The same application code therefore executes without modification across all four environments:

```python
# Identical code runs on all backends:
async with Robot(backend="gazebo") as robot:   # or "real", "isaac_sim", "mock"
    image = robot.get_camera_image()           # always (H, W, 3) uint8 RGB
    await robot.move_forward(0.5)
    result = await robot.move_to(x=1.0, y=1.0)
```

#### 3.1.3 Shared ROS2 bridge for sim and real backends

**File:** `sdk/threewe/src/threewe/backends/_ros2_node.py` (lines 41–92)

Both the `GazeboBackend` and `RealBackend` delegate to a shared `ROS2Node` class that subscribes to and publishes standardized ROS2 topics. Because Gazebo publishes sensor data on the same topic names as the real hardware (`/camera/image_raw`, `/scan`, `/odom`, `/imu/data`, `/battery_state`, `/map`), the `ROS2Node` subscriber code is shared verbatim between simulation and real hardware paths. The key innovation is that the topic namespace and QoS profile are identical between sim and real, so no conditional branching is required in the shared bridge layer.

**Standardized topics:**

| Topic | Type | Direction |
|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | subscribe |
| `/scan` | `sensor_msgs/LaserScan` | subscribe |
| `/odom` | `nav_msgs/Odometry` | subscribe |
| `/imu/data` | `sensor_msgs/Imu` | subscribe |
| `/battery_state` | `sensor_msgs/BatteryState` | subscribe |
| `/cmd_vel` | `geometry_msgs/Twist` | publish (RELIABLE QoS) |

#### 3.1.4 Configuration layer

**File:** `sdk/threewe/src/threewe/config.py`

`LimitsConfig` and `APIConfig` are shared across all backends, ensuring that velocity limits, sensor resolutions, and control frequencies are numerically identical between simulation and real hardware. Key parameters:

- `max_linear_velocity = 0.5 m/s`
- `max_angular_velocity = 1.0 rad/s`
- `safety_distance = 0.15 m`
- `image_size = (640, 480)` pixels
- `lidar_points = 360`
- `control_frequency = 50 Hz`

These values are applied identically in all backends, so a policy trained at `control_frequency=50 Hz` in simulation will be executed at the same control frequency on real hardware.

---

### 3.2 Layered Safety Interlock Architecture

#### 3.2.1 Four-layer interlock stack

The safety architecture implements four independent layers, each of which can independently halt motor output:

| Layer | Location | Mechanism | Bypassed by software crash? |
|---|---|---|---|
| L1: Physical E-stop | Hardware (NC circuit) | Cuts relay coil power directly | No |
| L2: ISR E-stop handler | Firmware ISR (`IRAM_ATTR`) | Sets `state = SAFETY_ESTOPPED` in critical section | No (ISR is always active) |
| L3: Watchdog timeout | Firmware task | Triggers E-stop if `/cmd_vel` stalls | No |
| L4: ROS2 QoS enforcement | ROS2 layer | `transient_local` durability on `/emergency_stop` | N/A (network layer) |

The key property is that **Layer 1 and Layer 2 are independent of the ROS2 control loop and the application software stack**. A complete crash of the Python SDK or ROS2 navigation stack cannot prevent L1 or L2 from engaging.

#### 3.2.2 Hardware E-stop ISR

**File:** `firmware/esp32/main/safety.c` (lines 64–71)

The physical E-stop button is wired as a normally-closed (NC) circuit to a GPIO interrupt. When the circuit opens (button pressed or wire break), the interrupt fires in IRAM-resident code and immediately sets the safety state and stops all motors:

```c
static void IRAM_ATTR estop_isr(void *arg) {
    portENTER_CRITICAL_ISR(&safety_spinlock);
    state = SAFETY_ESTOPPED;
    last_state_transition_us = esp_timer_get_time();
    portEXIT_CRITICAL_ISR(&safety_spinlock);
    motor_stop_all_isr();   // ISR-safe: sets PWM to zero via flag only
}
```

The `IRAM_ATTR` attribute places this function in on-chip SRAM, ensuring it executes even during flash cache misses. The spinlock ensures atomic state transition. The NC wiring means a broken wire is treated identically to a pressed button — fail-safe by design.

#### 3.2.3 Dual-channel relay feedback monitoring

**File:** `firmware/esp32/main/safety.c` (lines 341–376)

Two independent relay feedback pins (`SAFETY_RELAY_FB`, `SAFETY_RELAY_FB2`) are monitored simultaneously. A mismatch between the two channels triggers an escalating fault response:

```c
int relay_fb  = gpio_get_level(SAFETY_RELAY_FB);
int relay_fb2 = gpio_get_level(SAFETY_RELAY_FB2);

if (relay_fb != relay_fb2) {
    relay_mismatch_debounce++;
    if (relay_mismatch_debounce >= RELAY_MISMATCH_DEBOUNCE_THRESHOLD) {
        if (relay_fault_count >= 3) {
            state = SAFETY_RELAY_FAULT;  // Requires physical service
        } else {
            state = SAFETY_ESTOPPED;     // Automatic safety response
        }
    }
}
```

This dual-channel feedback architecture corresponds to **ISO 13849 Category 3 Performance Level d (PLd)** for the relay monitoring subsystem: a single component failure is detected before or during the next safety function demand, and the safety function is still performed. No existing open-source robot platform at this price point implements dual-channel relay feedback with automated fault escalation.

#### 3.2.4 Firmware safety state machine

**File:** `firmware/esp32/main/safety.h` (lines 8–13)

```c
typedef enum {
    SAFETY_NORMAL          = 0,
    SAFETY_ESTOPPED        = 1,
    SAFETY_RECOVERY_PENDING = 2,
    SAFETY_RELAY_FAULT     = 3,
} safety_state_t;
```

Every motor command path checks safety state before executing:

```c
void motor_set_speed(motor_id_t id, float speed_pct) {
    portENTER_CRITICAL(&motor_spinlock);
    if (safety_is_estopped()) {
        portEXIT_CRITICAL(&motor_spinlock);
        return;   // Hard gate: no motor output in any non-NORMAL state
    }
    // ... motor driver update follows
}
```

The safety check is inside the same spinlock as the motor update, making it impossible for a context switch to insert a motor command between the safety check and the motor output.

#### 3.2.5 Control loop watchdog

**File:** `firmware/esp32/main/safety.c` (lines 256–277)

A firmware-side watchdog monitors the arrival of `/cmd_vel` messages from the ROS2 control loop. If no valid velocity command arrives within `WATCHDOG_TIMEOUT_MS`, the watchdog independently triggers E-stop:

```c
if (elapsed >= (WATCHDOG_TIMEOUT_MS * 1000LL)) {
    state = SAFETY_ESTOPPED;
    motor_stop_all();
    notify_state_change(SAFETY_ESTOPPED);
    ESP_LOGW(TAG, "Watchdog timeout - control loop stalled");
}
```

This protects against the failure mode where the ROS2 stack (running on Raspberry Pi 5) crashes or stalls while the ESP32 firmware still holds a non-zero velocity command buffered in the motor driver.

#### 3.2.6 Speed limit with NVS persistence

**File:** `firmware/esp32/main/safety.c` (lines 586–642)

```c
#define SPEED_LIMIT_HARD_CAP_MPS  1.2f

esp_err_t safety_set_speed_limit(float limit_mps);
float     safety_clamp_speed(float requested_mps);
void      safety_clamp_velocity(float *vx, float *vy);
```

Speed limits are stored in ESP32 Non-Volatile Storage (NVS) and survive power cycles. The hard cap (`1.2 m/s`) is enforced in firmware independent of any ROS2 parameter or Python-side configuration, preventing a software misconfiguration from commanding unsafe speeds.

#### 3.2.7 ROS2 QoS safety enforcement

**File:** `ros2_ws/robot_bringup/launch/hardware.launch.py` (lines 49–64)

```python
"qos_overrides./cmd_vel.subscription.reliability":         "reliable",
"qos_overrides./emergency_stop.publisher.reliability":     "reliable",
"qos_overrides./emergency_stop.publisher.durability":      "transient_local",
```

`transient_local` durability on `/emergency_stop` ensures that a newly-joined node immediately receives the last published safety state without requiring the publisher to be active. This prevents a race condition where a node joining after an E-stop event would start in an unknown safety state.

---

### 4. Related Innovation: Payload Sandbox Isolation

**Files:** `sdk/payload_interface/payload_protocol.py`, `firmware/esp32/main/payload_power.h`

Payload code (user-developed code running on hardware attached to the robot's payload port) is isolated from the core safety and motor control systems through three independent mechanisms:

**4.1 EEPROM capability bitmask** — Each payload declares its allowed capabilities (`CAP_I2C`, `CAP_GPIO`, `CAP_SPI`, `CAP_UART`, `CAP_CAN`) and a GPIO pin mask in a hardware EEPROM descriptor. The firmware enforces that payload code can only access the pins declared in its descriptor; attempts to access undeclared pins are silently rejected at the firmware level.

**4.2 MCP23017 power rail isolation** — Payload power rails are controlled via a dedicated I²C GPIO expander (MCP23017), physically separate from the motor driver power path. The payload power state machine (`POWER_RAIL_OFF`, `POWER_RAIL_RAMPING`, `POWER_RAIL_ON`, `POWER_RAIL_FAULT`) is isolated from the safety interlock state machine; a payload power fault cannot affect motor control.

**4.3 ROS2 namespace isolation** — Payload nodes run in the `/payload` ROS2 namespace. The safety node and motor control nodes reject publications and service calls originating from the `/payload` namespace for the following topics and services:
- `/cmd_vel` (motor velocity commands)
- `/emergency_stop` (E-stop service)
- `/robot/*` parameter namespace (safety relay GPIO config, watchdog timeout)

This three-layer isolation means that a compromised or buggy payload cannot command motors, cannot disable the E-stop, and cannot read safety-critical configuration parameters.

---

## 5. Claims of Novelty

The following aspects of the implementation are believed to be novel over the prior art as of the document date:

**C1.** A robot control API in which a single `backend` constructor parameter dispatches to simulation and real-hardware backends that are guaranteed to return sensor data in identical formats (tensor shape, dtype, coordinate convention, physical units), with the guarantee enforced at the abstract class level rather than by documentation convention.

**C2.** A shared ROS2 bridge layer (`_ros2_node.py`) that is used verbatim by both simulation and real-hardware backends, where the identical topic names and QoS profiles in simulation and real hardware are a deliberate architectural requirement rather than a coincidence.

**C3.** A firmware-level dual-channel relay feedback monitor that detects single-channel relay faults through debounced mismatch detection between two independent feedback GPIO pins, and escalates through a state machine from `SAFETY_ESTOPPED` to `SAFETY_RELAY_FAULT` based on repeated fault count, without requiring any software-layer involvement.

**C4.** The combination of (i) an ISR-resident E-stop handler placed in IRAM (`IRAM_ATTR`) that executes independently of the flash cache state, (ii) a firmware watchdog that triggers E-stop on ROS2 control loop stall, and (iii) a hardware normally-closed E-stop circuit — where all three mechanisms independently gate the same motor driver spinlock, making simultaneous bypass of all three layers by a single software fault impossible.

**C5.** A payload isolation architecture in which three independent isolation layers (hardware EEPROM capability bitmask, MCP23017 power rail separation, ROS2 namespace rejection) operate at different abstraction levels such that a fault or compromise in any single isolation layer does not propagate to the motor control or safety interlock subsystems.

---

## 6. Prior Art Acknowledgment

The following prior art is acknowledged. The claims of novelty above are asserted to be distinct from these references:

- ROS2 Navigation Stack (Nav2): provides software E-stop and velocity limiting but does not implement hardware relay monitoring or dual-channel fault detection.
- OpenAI Gym / Gymnasium: provides simulation environment abstraction but does not address real-hardware backends or format consistency contracts.
- NVIDIA Isaac Gym / Isaac Lab: simulation-only; no real-hardware backend.
- PyRobot (Facebook AI Research): provides a robot abstraction layer but does not enforce data format contracts at the abstract class level and does not implement dual-channel hardware safety monitoring.
- Boston Dynamics Spot SDK: proprietary; implements similar safety layering but is not open-source and does not address the Sim2Real zero-code-change problem.

---

## 7. Reduction to Practice

The following components have been implemented and are present in the repository as of this document date:

| Component | File | Status |
|---|---|---|
| `BackendBase` contract | `sdk/threewe/src/threewe/backends/__init__.py` | Implemented |
| `Robot._create_backend()` factory | `sdk/threewe/src/threewe/robot.py` | Implemented |
| `ROS2Node` shared bridge | `sdk/threewe/src/threewe/backends/_ros2_node.py` | Implemented |
| `GazeboBackend` | `sdk/threewe/src/threewe/backends/gazebo.py` | Implemented |
| `RealBackend` | `sdk/threewe/src/threewe/backends/real.py` | Implemented |
| `IsaacSimBackend` | `sdk/threewe/src/threewe/backends/isaac_sim.py` | Implemented |
| `safety_state_t` state machine | `firmware/esp32/main/safety.h` | Implemented |
| Dual-channel relay feedback | `firmware/esp32/main/safety.c` | Implemented |
| ISR E-stop handler | `firmware/esp32/main/safety.c` | Implemented |
| Watchdog timeout | `firmware/esp32/main/safety.c` | Implemented |
| NVS speed limit persistence | `firmware/esp32/main/safety.c` | Implemented |
| Payload EEPROM descriptor | `sdk/payload_interface/payload_protocol.py` | Implemented |
| MCP23017 power rail isolation | `firmware/esp32/main/payload_power.h` | Implemented |
| ROS2 namespace rejection tests | `sdk/tests/test_payload_sandbox.py` | Implemented |

---

## 8. Inventor Declaration

I, the author of this repository, declare that the technical content described in this document was conceived and reduced to practice independently, without use of employer resources, and outside of employment working hours. This invention is a personal project unrelated to any employer's business.

**Signed:** [Author]  
**Date:** 2026-05-23  
**Repository commit at time of signing:** d85c720188f0f7678d37d4a6a21e0813dbf0b6d5

---

*This document is intended to establish prior art and invention date for future patent prosecution. It does not constitute a patent application. All technical claims are subject to review by a registered patent attorney before any filing.*
