# SLAM Alternatives

> See also: [ros2_interface_reference.md](ros2_interface_reference.md) for the navigation topic/service definitions.

## Why slam_toolbox is Optional

The `slam_toolbox` package is licensed under **LGPL-2.1**. While the LGPL is a
well-respected open-source license, it imposes reciprocal obligations that may
conflict with proprietary derivative works:

- If statically linked, the entire binary must be distributed under LGPL-compatible
  terms
- If dynamically linked, you must allow relinking (provide object files or shared
  library interfaces)

For fully open-source deployments, `slam_toolbox` works perfectly. For commercial
deployments where LGPL obligations are undesirable, use one of the alternatives below.

## Using slam_toolbox (if desired)

Install it separately:

```bash
sudo apt install ros-humble-slam-toolbox
```

The launch file's `use_slam` parameter (defaults to `false`) controls whether SLAM
is loaded at runtime. No rebuild is needed.

## Permissively-Licensed Alternatives

| Package | License | Strengths | Limitations |
|---------|---------|-----------|-------------|
| [Cartographer](https://github.com/cartographer-project/cartographer) | Apache 2.0 | Google-backed, excellent for 2D/3D, mature | Maintenance slowing, complex tuning |
| [RTAB-Map](https://github.com/introlab/rtabmap) | BSD-3-Clause | Visual + lidar SLAM, loop closure, 3D | Higher compute requirements |
| [kiss-icp](https://github.com/PRBonn/kiss-icp) | MIT | Lightweight lidar odometry, simple to integrate | Odometry only (no full SLAM loop closure) |

## Migration Guide

### Switching to Cartographer

1. Install: `sudo apt install ros-humble-cartographer ros-humble-cartographer-ros`
2. Create a `cartographer_params.lua` configuration (see
   [Cartographer ROS docs](https://google-cartographer-ros.readthedocs.io/))
3. Update `navigation.launch.py` to launch `cartographer_node` instead of
   `async_slam_toolbox_node`

### Switching to RTAB-Map

1. Install: `sudo apt install ros-humble-rtabmap-ros`
2. Configure RTAB-Map parameters for your sensor setup (lidar, stereo camera, or RGB-D)
3. Update the launch file to use `rtabmap_slam` node

## Recommendation

For this platform's typical use case (2D indoor navigation with lidar):

- **Open-source deployments**: `slam_toolbox` remains the best choice (feature-rich,
  actively maintained, ROS2-native)
- **Commercial deployments**: Cartographer (Apache 2.0) is the closest drop-in
  replacement with no LGPL concerns
