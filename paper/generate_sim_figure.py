#!/usr/bin/env python3
"""Generate a mock simulation visualization for the paper.

Produces a publication-quality top-down view of the robot navigating
in the office_v2 scene, showing:
- Room boundary and obstacles
- Robot position with heading indicator
- LiDAR scan rays
- Navigation trajectory (multi-waypoint path)
"""

import math
import sys
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Wedge
import numpy as np

# Paper style
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 8,
    'axes.labelsize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

COLORS = {
    'wall': '#374151',
    'obstacle': '#9CA3AF',
    'obstacle_fill': '#E5E7EB',
    'robot': '#2563EB',
    'robot_fill': '#DBEAFE',
    'lidar': '#059669',
    'lidar_hit': '#DC2626',
    'trajectory': '#D97706',
    'waypoint': '#7C3AED',
    'start': '#059669',
    'goal': '#DC2626',
    'grid': '#F3F4F6',
    'floor': '#FAFAFA',
}

# Scene definition (office_v2)
SCENE_W, SCENE_H = 20.0, 15.0
OBSTACLES = [
    (4.0, 5.0, 6.0, 6.0),
    (10.0, 6.0, 12.0, 7.5),
    (3.0, 10.0, 5.0, 11.5),
    (14.0, 2.0, 15.5, 4.5),
    (8.0, 11.0, 10.0, 13.0),
    (16.0, 8.0, 18.0, 9.5),
]

ROBOT_RADIUS = 0.15


def raycast(x, y, angle, obstacles, scene_w, scene_h):
    """Simple 2D raycast against walls and AABB obstacles."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    min_dist = scene_w + scene_h

    # Walls
    if cos_a > 1e-6:
        min_dist = min(min_dist, (scene_w - x) / cos_a)
    elif cos_a < -1e-6:
        min_dist = min(min_dist, -x / cos_a)
    if sin_a > 1e-6:
        min_dist = min(min_dist, (scene_h - y) / sin_a)
    elif sin_a < -1e-6:
        min_dist = min(min_dist, -y / sin_a)

    # Obstacles
    for obs in obstacles:
        x_min, y_min, x_max, y_max = obs
        # Slab method
        if abs(cos_a) < 1e-9:
            if x < x_min or x > x_max:
                continue
            t_min_x, t_max_x = -1e30, 1e30
        else:
            inv_dx = 1.0 / cos_a
            t1 = (x_min - x) * inv_dx
            t2 = (x_max - x) * inv_dx
            t_min_x, t_max_x = min(t1, t2), max(t1, t2)

        if abs(sin_a) < 1e-9:
            if y < y_min or y > y_max:
                continue
            t_min_y, t_max_y = -1e30, 1e30
        else:
            inv_dy = 1.0 / sin_a
            t1 = (y_min - y) * inv_dy
            t2 = (y_max - y) * inv_dy
            t_min_y, t_max_y = min(t1, t2), max(t1, t2)

        t_enter = max(t_min_x, t_min_y)
        t_exit = min(t_max_x, t_max_y)

        if t_enter > t_exit or t_exit < 0:
            continue
        t = t_enter if t_enter > 0 else t_exit
        if t > 0 and t < min_dist:
            min_dist = t

    return max(0.12, min(min_dist, 12.0))


def simulate_navigation():
    """Simulate a multi-waypoint navigation and return trajectory."""
    waypoints = [
        (1.5, 1.5),
        (3.0, 3.5),
        (7.0, 3.0),
        (9.0, 5.0),
        (13.0, 5.5),
        (15.0, 7.0),
        (13.0, 10.0),
        (11.0, 12.0),
    ]

    trajectory = [(1.5, 1.5)]
    step = 0.15

    for i in range(1, len(waypoints)):
        sx, sy = trajectory[-1]
        gx, gy = waypoints[i]
        dist = math.sqrt((gx - sx)**2 + (gy - sy)**2)
        n_steps = max(1, int(dist / step))
        for j in range(1, n_steps + 1):
            t = j / n_steps
            px = sx + (gx - sx) * t
            py = sy + (gy - sy) * t
            trajectory.append((px, py))

    return trajectory, waypoints


def generate_sim_figure():
    """Generate the simulation visualization figure."""
    fig, ax = plt.subplots(1, 1, figsize=(3.4, 2.6))

    # Floor
    ax.set_facecolor(COLORS['floor'])

    # Grid
    for x in range(0, int(SCENE_W) + 1, 2):
        ax.axvline(x, color=COLORS['grid'], linewidth=0.3, zorder=0)
    for y in range(0, int(SCENE_H) + 1, 2):
        ax.axhline(y, color=COLORS['grid'], linewidth=0.3, zorder=0)

    # Room boundary
    boundary = plt.Rectangle((0, 0), SCENE_W, SCENE_H,
                              fill=False, edgecolor=COLORS['wall'],
                              linewidth=1.5, zorder=2)
    ax.add_patch(boundary)

    # Obstacles
    for obs in OBSTACLES:
        x_min, y_min, x_max, y_max = obs
        rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                              facecolor=COLORS['obstacle_fill'],
                              edgecolor=COLORS['obstacle'],
                              linewidth=0.8, zorder=3)
        ax.add_patch(rect)
        # Hatching for better visibility in B&W print
        rect_h = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                                facecolor='none', edgecolor=COLORS['obstacle'],
                                linewidth=0.3, hatch='///', zorder=3)
        ax.add_patch(rect_h)

    # Simulate trajectory
    trajectory, waypoints = simulate_navigation()
    traj_x = [p[0] for p in trajectory]
    traj_y = [p[1] for p in trajectory]

    # Draw trajectory
    ax.plot(traj_x, traj_y, color=COLORS['trajectory'], linewidth=1.2,
            linestyle='-', alpha=0.8, zorder=4, label='Planned path')

    # Waypoints
    for i, (wx, wy) in enumerate(waypoints):
        if i == 0:
            ax.plot(wx, wy, 's', color=COLORS['start'], markersize=5, zorder=6)
        elif i == len(waypoints) - 1:
            ax.plot(wx, wy, '*', color=COLORS['goal'], markersize=8, zorder=6)
        else:
            ax.plot(wx, wy, 'o', color=COLORS['waypoint'], markersize=3,
                    alpha=0.7, zorder=5)

    # Robot position (at waypoint 5 - mid-navigation)
    robot_idx = len(trajectory) * 5 // 8
    rx, ry = trajectory[robot_idx]
    # Compute heading toward next point
    if robot_idx < len(trajectory) - 1:
        nx, ny = trajectory[robot_idx + 1]
        theta = math.atan2(ny - ry, nx - rx)
    else:
        theta = 0.0

    # LiDAR scan visualization
    n_rays = 72
    angles = np.linspace(0, 2 * math.pi, n_rays, endpoint=False)
    for angle in angles:
        ray_angle = theta + angle
        dist = raycast(rx, ry, ray_angle, OBSTACLES, SCENE_W, SCENE_H)
        hit_x = rx + dist * math.cos(ray_angle)
        hit_y = ry + dist * math.sin(ray_angle)
        ax.plot([rx, hit_x], [ry, hit_y], color=COLORS['lidar'],
                linewidth=0.2, alpha=0.4, zorder=4)
        # Hit point
        ax.plot(hit_x, hit_y, '.', color=COLORS['lidar_hit'],
                markersize=1.0, alpha=0.6, zorder=5)

    # Robot body
    robot_circle = Circle((rx, ry), ROBOT_RADIUS * 3, facecolor=COLORS['robot_fill'],
                          edgecolor=COLORS['robot'], linewidth=1.2, zorder=7)
    ax.add_patch(robot_circle)

    # Heading arrow
    arrow_len = ROBOT_RADIUS * 5
    ax.annotate('', xy=(rx + arrow_len * math.cos(theta),
                        ry + arrow_len * math.sin(theta)),
                xytext=(rx, ry),
                arrowprops=dict(arrowstyle='->', color=COLORS['robot'],
                                lw=1.5), zorder=8)

    # FOV wedge (camera field of view)
    fov_deg = 120
    fov_radius = 2.5
    wedge = Wedge((rx, ry), fov_radius,
                  math.degrees(theta) - fov_deg / 2,
                  math.degrees(theta) + fov_deg / 2,
                  facecolor=COLORS['robot_fill'], edgecolor='none',
                  alpha=0.2, zorder=3)
    ax.add_patch(wedge)

    # Labels
    ax.text(waypoints[0][0], waypoints[0][1] - 0.8, 'Start',
            ha='center', va='top', fontsize=6, color=COLORS['start'], fontweight='bold')
    ax.text(waypoints[-1][0], waypoints[-1][1] + 0.8, 'Goal',
            ha='center', va='bottom', fontsize=6, color=COLORS['goal'], fontweight='bold')

    # Obstacle labels
    ax.text(5.0, 5.5, 'desk', ha='center', va='center', fontsize=5,
            color=COLORS['obstacle'], fontstyle='italic')
    ax.text(11.0, 6.75, 'cabinet', ha='center', va='center', fontsize=5,
            color=COLORS['obstacle'], fontstyle='italic')
    ax.text(4.0, 10.75, 'shelf', ha='center', va='center', fontsize=5,
            color=COLORS['obstacle'], fontstyle='italic')
    ax.text(14.75, 3.25, 'table', ha='center', va='center', fontsize=5,
            color=COLORS['obstacle'], fontstyle='italic')

    # Scene title
    ax.text(SCENE_W / 2, SCENE_H + 0.4, 'office\_v2 (20m $\\times$ 15m)',
            ha='center', va='bottom', fontsize=7, color=COLORS['wall'])

    # Legend
    legend_elements = [
        plt.Line2D([0], [0], color=COLORS['trajectory'], linewidth=1.2, label='Navigation path'),
        plt.Line2D([0], [0], color=COLORS['lidar'], linewidth=0.6, alpha=0.6, label='LiDAR rays'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=COLORS['lidar_hit'],
                   markersize=3, label='LiDAR hits'),
        mpatches.Patch(facecolor=COLORS['obstacle_fill'], edgecolor=COLORS['obstacle'],
                       linewidth=0.5, label='Obstacles'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', framealpha=0.9,
              borderpad=0.4, handlelength=1.5)

    # Axes
    ax.set_xlim(-0.5, SCENE_W + 0.5)
    ax.set_ylim(-0.5, SCENE_H + 1.0)
    ax.set_aspect('equal')
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.savefig('figures/simulation.pdf', format='pdf')
    plt.close(fig)
    print("Generated: figures/simulation.pdf")


if __name__ == '__main__':
    os.makedirs('figures', exist_ok=True)
    generate_sim_figure()
