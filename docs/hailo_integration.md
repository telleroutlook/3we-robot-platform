# SPDX-License-Identifier: Apache-2.0

# Hailo AI Accelerator Integration

## Overview

The Hailo-8 and Hailo-8L are dedicated AI inference accelerators designed for edge
deployment. They provide high-throughput neural network inference at low power
consumption, making them ideal for real-time perception on mobile robot platforms.

By offloading inference from the main CPU/GPU, the Hailo accelerator frees compute
resources for navigation, planning, and other workloads.

## Supported Hardware

| Accelerator | Performance | Power    | Form Factor       |
|-------------|-------------|----------|-------------------|
| Hailo-8     | 26 TOPS     | ~2.5 W  | M.2 Key B+M, mPCIe |
| Hailo-8L    | 13 TOPS     | ~1.5 W  | M.2 Key B+M, mPCIe |

Both modules connect over PCIe and are compatible with standard carrier boards
including Raspberry Pi 5 (via M.2 HAT) and NVIDIA Jetson carriers.

## Prerequisites

- Ubuntu 22.04 or later (aarch64 or x86_64)
- HailoRT >= 4.17
- Python >= 3.10
- `hailo_platform` Python package
- PCIe slot with the Hailo module physically installed

## Installation (Ubuntu)

```bash
# 1. Add Hailo APT repository
wget -qO - https://hailo.ai/keys/hailo-archive-keyring.gpg | sudo tee /usr/share/keyrings/hailo-archive-keyring.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] https://apt.hailo.ai/ jammy main" | sudo tee /etc/apt/sources.list.d/hailo.list

# 2. Install HailoRT and development libraries
sudo apt update
sudo apt install -y hailort hailort-dev

# 3. Install Python bindings
pip install hailo_platform hailort

# 4. Verify installation
hailortcli fw-control identify
```

## Model Compilation (ONNX to HEF)

Hailo models run in the proprietary HEF (Hailo Executable Format). Use the Dataflow
Compiler (DFC) to convert standard models:

```bash
# Install the Dataflow Compiler (requires Hailo Developer Zone access)
pip install hailo_dataflow_compiler

# Parse ONNX model
hailo parser onnx yolov8n.onnx

# Optimize and compile to HEF
hailo optimize yolov8n.har
hailo compiler yolov8n.har --hw-arch hailo8
# Output: yolov8n.hef
```

The resulting `.hef` file is what you pass to the ROS2 node via the `model_path` parameter.

## ROS2 Node Usage

### Launch

```bash
ros2 launch robot_perception perception.launch.py \
  model_path:=/opt/models/yolov8n.hef \
  confidence_threshold:=0.6 \
  device_id:=0
```

### Parameters

| Parameter              | Type   | Default               | Description                          |
|------------------------|--------|-----------------------|--------------------------------------|
| `model_path`           | string | `""`                  | Path to compiled HEF model           |
| `confidence_threshold` | float  | `0.5`                 | Minimum detection confidence         |
| `device_id`            | int    | `0`                   | Hailo device index                   |
| `input_topic`          | string | `/camera/image_raw`   | Camera image subscription topic      |
| `output_topic`         | string | `/perception/detections` | Detection results publish topic   |

### Topics

| Topic                       | Type                           | Direction |
|-----------------------------|--------------------------------|-----------|
| `/camera/image_raw`         | `sensor_msgs/msg/Image`        | Subscribe |
| `/perception/detections`    | `vision_msgs/msg/Detection2DArray` | Publish |

## Example: YOLOv8n Object Detection Pipeline

1. Compile `yolov8n.onnx` to `yolov8n.hef` using the DFC workflow above
2. Place the HEF at `/opt/models/yolov8n.hef`
3. Launch camera and perception nodes:

```bash
ros2 launch robot_perception perception.launch.py model_path:=/opt/models/yolov8n.hef
```

4. Visualize detections in RViz2 or consume from downstream planning nodes

## Performance Expectations

| Model     | Accelerator | Latency (ms) | FPS   | Power  |
|-----------|-------------|--------------|-------|--------|
| YOLOv8n   | Hailo-8     | ~8           | ~120  | ~2.5 W |
| YOLOv8n   | Hailo-8L    | ~15          | ~65   | ~1.5 W |
| YOLOv8s   | Hailo-8     | ~14          | ~70   | ~2.8 W |

Actual performance depends on input resolution, batch size, and system thermal conditions.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `hailortcli` reports "No devices found" | Check PCIe connection; run `lspci \| grep Hailo`; reload driver with `sudo modprobe hailo_pci` |
| Import error for `hailo_platform` | Ensure `pip install hailo_platform` matches your HailoRT version |
| Model fails to load | Verify HEF was compiled for the correct hardware arch (`hailo8` vs `hailo8l`) |
| Low FPS despite accelerator present | Check thermal throttling; ensure PCIe link is Gen3 x1 or better |
| Node runs in passthrough mode | `hailo_platform` is not installed or the module is not detected |
| Permission denied on device | Add user to `hailo` group: `sudo usermod -aG hailo $USER` and re-login |
