# Architecture Diagrams

Visual reference for the robot platform system architecture. Diagrams use Mermaid syntax and render natively on GitHub.

## System Layer Diagram

```mermaid
flowchart TD
    subgraph Payload["Payload Layer"]
        P1[User Devices]
        P2[PBC-34 Connector]
    end

    subgraph Application["Application Layer"]
        A1[rosbridge WebSocket :9090]
        A2[Web Control UI]
        A3[DTLS Direct Control :5684]
    end

    subgraph ROS2["ROS2 Layer — Raspberry Pi 5"]
        R1[Nav2 Navigation]
        R2[slam_toolbox SLAM]
        R3[robot_state_publisher]
        R4[micro_ros_agent]
    end

    subgraph Firmware["Firmware Layer — ESP32-S3"]
        F1[Motor Control — DRV8833 PWM]
        F2[Sensor Fusion — IMU + Encoders]
        F3[Safety Module — Watchdog + E-stop]
        F4[Communication — micro-ROS DDS-XRCE]
        F5[Payload Hot-plug Manager]
    end

    subgraph Hardware["Hardware Layer"]
        H1[4x Mecanum Wheels + Encoders]
        H2[DRV8833 H-Bridge x2]
        H3[IMU BNO055]
        H4[4x Ultrasonic Sensors]
        H5[Safety Relay + E-stop Button]
        H6[Battery 2S 18650 — 7.4V]
    end

    P1 --> P2
    P2 --> F5
    A2 --> A1
    A3 --> F4
    A1 --> R4
    R1 --> R4
    R2 --> R4
    R3 --> R4
    R4 --> F4
    F1 --> H2
    H2 --> H1
    F2 --> H3
    F2 --> H4
    F3 --> H5
    F4 --> R4
```

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph Sensors["Sensor Input"]
        ENC[Encoders — PCNT]
        IMU[IMU — I2C 100Hz]
        US[Ultrasonic x4 — RMT 10Hz]
    end

    subgraph Fusion["Sensor Fusion"]
        ODOM[Odometry Calculation]
        TF[TF Transform Tree]
    end

    subgraph Planning["Navigation Planning"]
        SLAM[SLAM — Map Building]
        COST[Costmap — Obstacle Layers]
        PLAN[NavfnPlanner — A* Path]
        DWB[DWB Local Planner]
    end

    subgraph Execution["Motor Execution"]
        IK[Inverse Kinematics — Mecanum]
        PWM[PWM Generation — 4 Channels]
        MOT[DRV8833 Motor Drivers]
    end

    ENC --> ODOM
    IMU --> ODOM
    ODOM --> TF
    TF --> SLAM
    US --> COST
    SLAM --> COST
    COST --> PLAN
    PLAN --> DWB
    DWB -->|/cmd_vel| IK
    IK --> PWM
    PWM --> MOT
```

## Communication Topology

```mermaid
flowchart LR
    subgraph Browser["Browser Client"]
        WEB[Web Control UI]
    end

    subgraph RPi["Raspberry Pi 5"]
        ROS[ROS2 Humble]
        BRIDGE[rosbridge_server]
        AGENT[micro_ros_agent]
    end

    subgraph ESP["ESP32-S3"]
        FW[Firmware]
        UROS[micro-ROS Client]
        DTLS_S[DTLS Server]
    end

    WEB -->|"WebSocket :9090 JSON"| BRIDGE
    WEB -->|"UDP/DTLS :5684 PSK"| DTLS_S
    BRIDGE --> ROS
    ROS --> AGENT
    AGENT -->|"UART 921600 baud DDS-XRCE"| UROS
    UROS --> FW
    DTLS_S --> FW

    style WEB fill:#e3f2fd
    style ROS fill:#e8f5e9
    style FW fill:#fff3e0
```

## Safety Chain Diagram

```mermaid
flowchart TD
    BTN[Physical E-stop Button]
    GPIO[GPIO ISR — 50ms Debounce]
    STATE[safety_set_state — ESTOPPED]
    RELAY[Safety Relay — OPEN]
    MOTOR_OFF[Motor Driver Power CUT]
    WDG[Software Watchdog — 500ms Timeout]
    CMD_TO[cmd_vel Timeout — 500ms]

    BTN -->|"Hardware interrupt"| GPIO
    GPIO --> STATE
    STATE --> RELAY
    RELAY --> MOTOR_OFF
    WDG -->|"No heartbeat"| STATE
    CMD_TO -->|"No velocity cmd"| STATE

    subgraph Recovery["Recovery Sequence"]
        R1[Physical button released]
        R2[safety_reset called]
        R3[safety_confirm_reset called]
        R4[Relay self-test passes]
        R5[SAFETY_NORMAL restored]
    end

    MOTOR_OFF -.->|"Manual intervention"| R1
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> R5

    style BTN fill:#ffcdd2
    style MOTOR_OFF fill:#ffcdd2
    style R5 fill:#c8e6c9
```

## E-stop State Machine

```mermaid
stateDiagram-v2
    [*] --> SAFETY_NORMAL

    SAFETY_NORMAL --> SAFETY_ESTOPPED : Button press / Watchdog timeout / Software trigger
    SAFETY_ESTOPPED --> SAFETY_RECOVERY_PENDING : safety_reset() called
    SAFETY_RECOVERY_PENDING --> SAFETY_NORMAL : safety_confirm_reset() + relay self-test OK
    SAFETY_RECOVERY_PENDING --> SAFETY_RELAY_FAULT : Relay self-test FAILS

    SAFETY_NORMAL --> SAFETY_RELAY_FAULT : Relay self-test fails at startup
    SAFETY_RELAY_FAULT --> [*] : Requires physical service

    state SAFETY_NORMAL {
        [*] --> Operational
        Operational : Motors enabled
        Operational : Watchdog fed every 500ms
        Operational : Speed limit enforced
    }

    state SAFETY_ESTOPPED {
        [*] --> Stopped
        Stopped : All motors disabled
        Stopped : Relay open (power cut)
        Stopped : Awaiting manual reset
    }

    state SAFETY_RELAY_FAULT {
        [*] --> Faulted
        Faulted : Hardware failure detected
        Faulted : Cannot resume operation
        Faulted : Flag persisted in NVS
    }
```

## Payload Hot-plug State Machine

```mermaid
stateDiagram-v2
    [*] --> PAYLOAD_STATE_ABSENT

    PAYLOAD_STATE_ABSENT --> PAYLOAD_STATE_DETECTED : I2C address responds at 0x50
    PAYLOAD_STATE_DETECTED --> PAYLOAD_STATE_IDENTIFYING : Read EEPROM descriptor (64 bytes)
    PAYLOAD_STATE_IDENTIFYING --> PAYLOAD_STATE_POWERING : Descriptor valid (magic "PBC4")
    PAYLOAD_STATE_IDENTIFYING --> PAYLOAD_STATE_FAULT : Invalid descriptor / CRC fail
    PAYLOAD_STATE_POWERING --> PAYLOAD_STATE_READY : Power budget check passes, rails enabled
    PAYLOAD_STATE_POWERING --> PAYLOAD_STATE_FAULT : Overcurrent / budget exceeded
    PAYLOAD_STATE_READY --> PAYLOAD_STATE_REMOVING : I2C address stops responding
    PAYLOAD_STATE_FAULT --> PAYLOAD_STATE_REMOVING : Operator clears fault
    PAYLOAD_STATE_REMOVING --> PAYLOAD_STATE_ABSENT : Power rails disabled, cleanup done

    state PAYLOAD_STATE_READY {
        [*] --> Active
        Active : Payload communication active
        Active : Power rails monitored
        Active : Heartbeat via PING cmd
    }

    state PAYLOAD_STATE_FAULT {
        [*] --> Error
        Error : Power rails disabled
        Error : Event callback fired
        Error : Awaiting removal or clear
    }
```
