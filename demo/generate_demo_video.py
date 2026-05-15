#!/usr/bin/env python3
"""Generate a professional 2D navigation demo video for 3we.

Produces a 30-second MP4 showing:
- Top-down view of robot navigating office_v2 scene
- Real-time 360° LiDAR rays
- Smooth trajectory trail
- Python code HUD overlay
- Title and summary frames

Requirements:
    pip install matplotlib numpy
    ffmpeg must be installed (brew install ffmpeg)

Usage:
    python demo/generate_demo_video.py
"""

import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, FancyArrowPatch, Wedge, FancyBboxPatch
from matplotlib.animation import FuncAnimation, FFMpegWriter
import numpy as np

# === Configuration ===

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sim_navigation_demo.mp4")
FPS = 30
DPI = 100
FIG_W, FIG_H = 19.2, 10.8  # 1920x1080 at 100 DPI

# Scene (office_v2)
SCENE_W, SCENE_H = 20.0, 15.0
OBSTACLES = [
    (4.0, 5.0, 6.0, 6.0),
    (10.0, 6.0, 12.0, 7.5),
    (3.0, 10.0, 5.0, 11.5),
    (14.0, 2.0, 15.5, 4.5),
    (8.0, 11.0, 10.0, 13.0),
    (16.0, 8.0, 18.0, 9.5),
]
OBSTACLE_LABELS = [
    (5.0, 5.5, "desk"),
    (11.0, 6.75, "cabinet"),
    (4.0, 10.75, "shelf"),
    (14.75, 3.25, "table"),
    (9.0, 12.0, "bookcase"),
    (17.0, 8.75, "printer"),
]

# Dark theme colors
C = {
    "bg": "#0f0f1a",
    "floor": "#1a1a2e",
    "grid": "#252540",
    "wall": "#4a4a6a",
    "obstacle": "#6366f1",
    "obstacle_fill": "#2d2d5e",
    "robot": "#38bdf8",
    "robot_fill": "#0c4a6e",
    "lidar": "#34d399",
    "lidar_hit": "#f43f5e",
    "trajectory": "#f59e0b",
    "trajectory_glow": "#fbbf24",
    "waypoint": "#a78bfa",
    "start": "#10b981",
    "goal": "#ef4444",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "hud_bg": "#0f172a",
    "code": "#38bdf8",
    "code_kw": "#c084fc",
    "code_str": "#34d399",
}

ROBOT_RADIUS = 0.15


def raycast(x, y, angle, obstacles, scene_w, scene_h):
    """2D raycast against walls and AABB obstacles."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    min_dist = scene_w + scene_h

    if cos_a > 1e-6:
        min_dist = min(min_dist, (scene_w - x) / cos_a)
    elif cos_a < -1e-6:
        min_dist = min(min_dist, -x / cos_a)
    if sin_a > 1e-6:
        min_dist = min(min_dist, (scene_h - y) / sin_a)
    elif sin_a < -1e-6:
        min_dist = min(min_dist, -y / sin_a)

    for obs in obstacles:
        x_min, y_min, x_max, y_max = obs
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


def generate_smooth_path(waypoints, points_per_segment=30):
    """Generate a smooth path through waypoints using cubic interpolation."""
    from scipy.interpolate import CubicSpline

    wp = np.array(waypoints)
    t = np.zeros(len(wp))
    for i in range(1, len(wp)):
        t[i] = t[i-1] + np.linalg.norm(wp[i] - wp[i-1])

    t_fine = np.linspace(t[0], t[-1], len(wp) * points_per_segment)
    cs_x = CubicSpline(t, wp[:, 0])
    cs_y = CubicSpline(t, wp[:, 1])

    path_x = cs_x(t_fine)
    path_y = cs_y(t_fine)
    return list(zip(path_x, path_y))


def generate_linear_path(waypoints, step=0.08):
    """Fallback: linear interpolation between waypoints."""
    trajectory = [waypoints[0]]
    for i in range(1, len(waypoints)):
        sx, sy = trajectory[-1]
        gx, gy = waypoints[i]
        dist = math.sqrt((gx - sx)**2 + (gy - sy)**2)
        n_steps = max(1, int(dist / step))
        for j in range(1, n_steps + 1):
            t = j / n_steps
            trajectory.append((sx + (gx - sx) * t, sy + (gy - sy) * t))
    return trajectory


def build_trajectory():
    """Build the navigation trajectory."""
    waypoints = [
        (1.5, 1.5),
        (2.5, 3.5),
        (7.0, 4.0),
        (9.5, 5.0),
        (13.5, 5.5),
        (15.5, 6.5),
        (14.0, 9.0),
        (12.0, 10.5),
        (11.0, 12.0),
    ]

    try:
        path = generate_smooth_path(waypoints, points_per_segment=25)
    except ImportError:
        path = generate_linear_path(waypoints)

    return path, waypoints


# === Animation State ===

TITLE_FRAMES = 60       # 2s
ARRIVE_FRAMES = 60      # 2s
SUMMARY_FRAMES = 90     # 3s

trajectory, waypoints = build_trajectory()

# Navigation frames match trajectory length exactly (no dead time)
NAV_FRAMES = len(trajectory)
TOTAL_FRAMES = TITLE_FRAMES + NAV_FRAMES + ARRIVE_FRAMES + SUMMARY_FRAMES


def get_robot_state(nav_frame):
    """Get robot position and heading for a navigation frame."""
    idx = min(nav_frame, len(trajectory) - 1)
    x, y = trajectory[idx]

    if idx < len(trajectory) - 1:
        nx, ny = trajectory[idx + 1]
        theta = math.atan2(ny - y, nx - x)
    else:
        if idx > 0:
            px, py = trajectory[idx - 1]
            theta = math.atan2(y - py, x - px)
        else:
            theta = 0.0

    return x, y, theta, idx


def render_frame(frame_num, fig, ax_main, ax_hud):
    """Render a single frame."""
    ax_main.clear()
    ax_hud.clear()

    if frame_num < TITLE_FRAMES:
        render_title(frame_num, fig, ax_main, ax_hud)
    elif frame_num < TITLE_FRAMES + NAV_FRAMES:
        nav_frame = frame_num - TITLE_FRAMES
        render_navigation(nav_frame, fig, ax_main, ax_hud)
    elif frame_num < TITLE_FRAMES + NAV_FRAMES + ARRIVE_FRAMES:
        arrive_frame = frame_num - TITLE_FRAMES - NAV_FRAMES
        render_arrival(arrive_frame, fig, ax_main, ax_hud)
    else:
        summary_frame = frame_num - TITLE_FRAMES - NAV_FRAMES - ARRIVE_FRAMES
        render_summary(summary_frame, fig, ax_main, ax_hud)


def setup_scene(ax):
    """Draw the static scene elements."""
    ax.set_facecolor(C["floor"])
    ax.set_xlim(-1, SCENE_W + 1)
    ax.set_ylim(-1, SCENE_H + 1)
    ax.set_aspect("equal")
    ax.axis("off")

    # Grid
    for x in range(0, int(SCENE_W) + 1, 2):
        ax.axvline(x, color=C["grid"], linewidth=0.3, zorder=0)
    for y in range(0, int(SCENE_H) + 1, 2):
        ax.axhline(y, color=C["grid"], linewidth=0.3, zorder=0)

    # Boundary
    boundary = plt.Rectangle((0, 0), SCENE_W, SCENE_H,
                              fill=False, edgecolor=C["wall"],
                              linewidth=2.0, zorder=2)
    ax.add_patch(boundary)

    # Obstacles
    for obs in OBSTACLES:
        x_min, y_min, x_max, y_max = obs
        rect = plt.Rectangle((x_min, y_min), x_max - x_min, y_max - y_min,
                              facecolor=C["obstacle_fill"],
                              edgecolor=C["obstacle"],
                              linewidth=1.0, zorder=3, alpha=0.8)
        ax.add_patch(rect)

    # Labels
    for lx, ly, label in OBSTACLE_LABELS:
        ax.text(lx, ly, label, ha="center", va="center",
                fontsize=7, color=C["text_dim"], fontstyle="italic", zorder=4)

    # Start & Goal markers
    ax.plot(*waypoints[0], "s", color=C["start"], markersize=10, zorder=6)
    ax.plot(*waypoints[-1], "*", color=C["goal"], markersize=14, zorder=6)
    ax.text(waypoints[0][0], waypoints[0][1] - 0.8, "Start",
            ha="center", fontsize=8, color=C["start"], fontweight="bold")
    ax.text(waypoints[-1][0], waypoints[-1][1] + 0.8, "Goal",
            ha="center", fontsize=8, color=C["goal"], fontweight="bold")

    # Scene label
    ax.text(SCENE_W / 2, SCENE_H + 0.5, "office_v2  (20m × 15m)",
            ha="center", fontsize=9, color=C["text_dim"])


def draw_robot(ax, x, y, theta, lidar=True):
    """Draw robot with optional LiDAR visualization."""
    # LiDAR rays
    if lidar:
        n_rays = 72
        angles = np.linspace(0, 2 * math.pi, n_rays, endpoint=False)
        for angle in angles:
            ray_angle = theta + angle
            dist = raycast(x, y, ray_angle, OBSTACLES, SCENE_W, SCENE_H)
            hit_x = x + dist * math.cos(ray_angle)
            hit_y = y + dist * math.sin(ray_angle)
            ax.plot([x, hit_x], [y, hit_y], color=C["lidar"],
                    linewidth=0.3, alpha=0.35, zorder=4)
            ax.plot(hit_x, hit_y, ".", color=C["lidar_hit"],
                    markersize=1.5, alpha=0.7, zorder=5)

    # FOV wedge
    fov_deg = 120
    fov_radius = 2.0
    wedge = Wedge((x, y), fov_radius,
                  math.degrees(theta) - fov_deg / 2,
                  math.degrees(theta) + fov_deg / 2,
                  facecolor=C["robot_fill"], edgecolor="none",
                  alpha=0.25, zorder=3)
    ax.add_patch(wedge)

    # Robot body
    robot_circle = Circle((x, y), ROBOT_RADIUS * 3,
                          facecolor=C["robot_fill"],
                          edgecolor=C["robot"],
                          linewidth=1.5, zorder=7)
    ax.add_patch(robot_circle)

    # Heading arrow
    arrow_len = ROBOT_RADIUS * 5
    ax.annotate("", xy=(x + arrow_len * math.cos(theta),
                        y + arrow_len * math.sin(theta)),
                xytext=(x, y),
                arrowprops=dict(arrowstyle="->", color=C["robot"], lw=2.0),
                zorder=8)


def render_title(frame, fig, ax_main, ax_hud):
    """Render title card."""
    ax_main.set_facecolor(C["bg"])
    ax_main.set_xlim(0, 10)
    ax_main.set_ylim(0, 10)
    ax_main.axis("off")

    alpha = min(1.0, frame / 30.0)

    ax_main.text(5, 6.5, "3we", ha="center", va="center",
                 fontsize=72, fontweight="bold", color=C["robot"], alpha=alpha,
                 fontfamily="monospace")
    ax_main.text(5, 4.8, "Open Infrastructure for Embodied AI",
                 ha="center", va="center", fontsize=20, color=C["text"], alpha=alpha)
    ax_main.text(5, 3.5, "Autonomous Navigation Demo  ·  office_v2 scene",
                 ha="center", va="center", fontsize=13, color=C["text_dim"], alpha=alpha)
    ax_main.text(5, 2.2, "github.com/telleroutlook/3we-robot-platform",
                 ha="center", va="center", fontsize=10, color=C["text_dim"],
                 alpha=alpha * 0.7, fontfamily="monospace")

    ax_hud.set_facecolor(C["bg"])
    ax_hud.axis("off")


def render_navigation(nav_frame, fig, ax_main, ax_hud):
    """Render navigation frame."""
    setup_scene(ax_main)

    x, y, theta, idx = get_robot_state(nav_frame)

    # Trajectory trail (already visited)
    trail = trajectory[:idx+1]
    if len(trail) > 1:
        tx = [p[0] for p in trail]
        ty = [p[1] for p in trail]
        ax_main.plot(tx, ty, color=C["trajectory"], linewidth=2.0,
                     alpha=0.85, zorder=5, solid_capstyle="round")
        # Glow effect
        ax_main.plot(tx, ty, color=C["trajectory_glow"], linewidth=4.0,
                     alpha=0.15, zorder=4, solid_capstyle="round")

    # Planned path (faded)
    future = trajectory[idx:]
    if len(future) > 1:
        fx = [p[0] for p in future]
        fy = [p[1] for p in future]
        ax_main.plot(fx, fy, color=C["waypoint"], linewidth=1.0,
                     alpha=0.3, linestyle="--", zorder=4)

    draw_robot(ax_main, x, y, theta)

    # HUD
    ax_hud.set_facecolor(C["hud_bg"])
    ax_hud.set_xlim(0, 10)
    ax_hud.set_ylim(0, 1)
    ax_hud.axis("off")

    progress = idx / max(1, len(trajectory) - 1)
    dist_traveled = sum(
        math.sqrt((trajectory[i+1][0]-trajectory[i][0])**2 +
                  (trajectory[i+1][1]-trajectory[i][1])**2)
        for i in range(min(idx, len(trajectory)-1))
    )

    # Code display
    code_lines = [
        'from threewe import Robot',
        '',
        'async with Robot(backend="mock") as robot:',
        '    await robot.navigate_to(11.0, 12.0)',
    ]
    code_y = 0.85
    for i, line in enumerate(code_lines):
        color = C["code"]
        if "from" in line or "import" in line or "async" in line or "with" in line or "await" in line:
            color = C["code_kw"]
        elif '"' in line:
            color = C["code_str"]
        ax_hud.text(0.3, code_y - i * 0.22, line, fontsize=9,
                    color=color, fontfamily="monospace", va="top")

    # Stats on right
    ax_hud.text(7.5, 0.75, f"Position: ({x:.1f}, {y:.1f})", fontsize=9,
                color=C["text_dim"], fontfamily="monospace")
    ax_hud.text(7.5, 0.50, f"Distance: {dist_traveled:.1f}m", fontsize=9,
                color=C["text_dim"], fontfamily="monospace")
    ax_hud.text(7.5, 0.25, f"Progress: {progress*100:.0f}%", fontsize=9,
                color=C["trajectory"], fontfamily="monospace")

    # Progress bar
    bar_x, bar_y, bar_w, bar_h = 7.4, 0.05, 2.3, 0.08
    ax_hud.add_patch(plt.Rectangle((bar_x, bar_y), bar_w, bar_h,
                                    facecolor=C["grid"], edgecolor="none", zorder=2))
    ax_hud.add_patch(plt.Rectangle((bar_x, bar_y), bar_w * progress, bar_h,
                                    facecolor=C["trajectory"], edgecolor="none", zorder=3))


def render_arrival(frame, fig, ax_main, ax_hud):
    """Render goal arrival celebration."""
    setup_scene(ax_main)

    # Full trajectory
    tx = [p[0] for p in trajectory]
    ty = [p[1] for p in trajectory]
    ax_main.plot(tx, ty, color=C["trajectory"], linewidth=2.0,
                 alpha=0.85, zorder=5, solid_capstyle="round")
    ax_main.plot(tx, ty, color=C["trajectory_glow"], linewidth=4.0,
                 alpha=0.15, zorder=4, solid_capstyle="round")

    # Robot at final position
    x, y = trajectory[-1]
    if len(trajectory) > 1:
        px, py = trajectory[-2]
        theta = math.atan2(y - py, x - px)
    else:
        theta = 0.0

    draw_robot(ax_main, x, y, theta)

    # Pulsing "Goal Reached" text
    pulse = 0.7 + 0.3 * math.sin(frame * 0.2)
    ax_main.text(SCENE_W / 2, SCENE_H / 2, "✓ Goal Reached",
                 ha="center", va="center", fontsize=28, fontweight="bold",
                 color=C["start"], alpha=pulse,
                 bbox=dict(boxstyle="round,pad=0.5", facecolor=C["bg"],
                           edgecolor=C["start"], alpha=0.8),
                 zorder=10)

    # HUD
    ax_hud.set_facecolor(C["hud_bg"])
    ax_hud.set_xlim(0, 10)
    ax_hud.set_ylim(0, 1)
    ax_hud.axis("off")

    total_dist = sum(
        math.sqrt((trajectory[i+1][0]-trajectory[i][0])**2 +
                  (trajectory[i+1][1]-trajectory[i][1])**2)
        for i in range(len(trajectory)-1)
    )
    ax_hud.text(5, 0.5, f"Navigation complete  ·  {total_dist:.1f}m traveled  ·  {len(waypoints)} waypoints",
                ha="center", va="center", fontsize=12, color=C["start"], fontfamily="monospace")


def render_summary(frame, fig, ax_main, ax_hud):
    """Render summary card."""
    ax_main.set_facecolor(C["bg"])
    ax_main.set_xlim(0, 10)
    ax_main.set_ylim(0, 10)
    ax_main.axis("off")

    alpha = min(1.0, frame / 20.0)

    total_dist = sum(
        math.sqrt((trajectory[i+1][0]-trajectory[i][0])**2 +
                  (trajectory[i+1][1]-trajectory[i][1])**2)
        for i in range(len(trajectory)-1)
    )

    ax_main.text(5, 8.5, "3we Navigation Demo — Summary",
                 ha="center", fontsize=22, fontweight="bold",
                 color=C["text"], alpha=alpha)

    metrics = [
        ("Scene", "office_v2 (20m × 15m)"),
        ("Backend", "Mock (zero-dependency, no GPU/ROS2 needed)"),
        ("Waypoints", f"{len(waypoints)}"),
        ("Total distance", f"{total_dist:.1f} m"),
        ("Obstacles avoided", f"{len(OBSTACLES)}"),
        ("LiDAR rays", "72 × 360°"),
        ("API code", "4 lines of Python"),
        ("Sim2Real", "Same code → Robot(backend=\"real\")"),
    ]

    y = 7.2
    for label, value in metrics:
        ax_main.text(3.0, y, label + ":", ha="right", fontsize=11,
                     color=C["text_dim"], alpha=alpha)
        ax_main.text(3.3, y, value, ha="left", fontsize=11,
                     color=C["text"], alpha=alpha, fontfamily="monospace")
        y -= 0.65

    ax_main.text(5, 1.5, "pip install threewe", ha="center", fontsize=14,
                 color=C["code"], alpha=alpha, fontfamily="monospace",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor=C["hud_bg"],
                           edgecolor=C["code"], alpha=0.5 * alpha))

    ax_main.text(5, 0.6, "3we.org  ·  github.com/telleroutlook/3we-robot-platform",
                 ha="center", fontsize=9, color=C["text_dim"], alpha=alpha * 0.7,
                 fontfamily="monospace")

    ax_hud.set_facecolor(C["bg"])
    ax_hud.axis("off")


def main():
    print(f"Generating demo video: {OUTPUT_PATH}")
    print(f"  Resolution: 1920×1080 @ {FPS}fps")
    print(f"  Duration: {TOTAL_FRAMES/FPS:.1f}s ({TOTAL_FRAMES} frames)")
    print(f"  Trajectory: {len(trajectory)} points, {len(waypoints)} waypoints")
    print()

    fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=C["bg"])

    # Main scene area (top 82%)
    ax_main = fig.add_axes([0.02, 0.18, 0.96, 0.80])
    # HUD strip (bottom 16%)
    ax_hud = fig.add_axes([0.02, 0.01, 0.96, 0.16])

    def animate(frame):
        if frame % 30 == 0:
            pct = frame / TOTAL_FRAMES * 100
            print(f"  Rendering: {pct:.0f}% (frame {frame}/{TOTAL_FRAMES})", end="\r")
        render_frame(frame, fig, ax_main, ax_hud)

    writer = FFMpegWriter(fps=FPS, bitrate=4000,
                          extra_args=["-pix_fmt", "yuv420p"])

    anim = FuncAnimation(fig, animate, frames=TOTAL_FRAMES, repeat=False)
    anim.save(OUTPUT_PATH, writer=writer, dpi=DPI)
    plt.close(fig)

    print(f"\n\n  Done! Video saved to: {OUTPUT_PATH}")

    # Print file size
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"  File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
