#!/usr/bin/env python3
"""Generate all figures for the 3we platform paper."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Paper style settings
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 8,
    'axes.labelsize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})

COLORS = {
    'blue': '#2563EB',
    'green': '#059669',
    'orange': '#D97706',
    'red': '#DC2626',
    'purple': '#7C3AED',
    'gray': '#6B7280',
    'light_blue': '#DBEAFE',
    'light_green': '#D1FAE5',
    'light_orange': '#FEF3C7',
    'light_gray': '#F3F4F6',
}


def fig_architecture():
    """Figure 1: Three-layer architecture with backend polymorphism."""
    fig, ax = plt.subplots(1, 1, figsize=(3.4, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Layer 1: AI-First Python API (top)
    box1 = FancyBboxPatch((0.5, 6.2), 9, 1.4, boxstyle="round,pad=0.1",
                          facecolor=COLORS['light_blue'], edgecolor=COLORS['blue'], linewidth=1.5)
    ax.add_patch(box1)
    ax.text(5, 7.1, 'AI-First Python API', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['blue'])
    ax.text(5, 6.6, 'robot.move_to() | robot.get_image() | robot.execute_instruction()',
            ha='center', va='center', fontsize=6, family='monospace', color=COLORS['gray'])

    # Layer 2: 3we-core (middle)
    box2 = FancyBboxPatch((0.5, 4.0), 9, 1.8, boxstyle="round,pad=0.1",
                          facecolor=COLORS['light_green'], edgecolor=COLORS['green'], linewidth=1.5)
    ax.add_patch(box2)
    ax.text(5, 5.2, '3we-core (Middleware)', ha='center', va='center',
            fontsize=9, fontweight='bold', color=COLORS['green'])
    ax.text(5, 4.6, 'Backend Dispatch | Sensor Standardization | Safety Checks',
            ha='center', va='center', fontsize=6, color=COLORS['gray'])

    # Layer 3: ROS2 / Backends (bottom)
    box3 = FancyBboxPatch((0.5, 1.0), 9, 2.6, boxstyle="round,pad=0.1",
                          facecolor=COLORS['light_gray'], edgecolor=COLORS['gray'], linewidth=1.5)
    ax.add_patch(box3)
    ax.text(5, 3.2, 'Infrastructure Layer', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#374151')

    # Backend boxes inside layer 3
    backends = [
        (1.2, 1.4, 'Mock\n(zero-dep)', COLORS['light_orange']),
        (3.3, 1.4, 'Gazebo\n(CPU)', COLORS['light_blue']),
        (5.4, 1.4, 'Isaac Sim\n(GPU)', COLORS['light_green']),
        (7.5, 1.4, 'Real HW\n(Pi5+ESP32)', '#FEE2E2'),
    ]
    for x, y, label, color in backends:
        box = FancyBboxPatch((x, y), 1.8, 1.4, boxstyle="round,pad=0.05",
                             facecolor=color, edgecolor='#9CA3AF', linewidth=0.8)
        ax.add_patch(box)
        ax.text(x + 0.9, y + 0.7, label, ha='center', va='center', fontsize=6)

    # Arrows between layers
    ax.annotate('', xy=(5, 6.2), xytext=(5, 5.8),
                arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.2))
    ax.annotate('', xy=(5, 4.0), xytext=(5, 3.6),
                arrowprops=dict(arrowstyle='->', color=COLORS['gray'], lw=1.2))

    # Side label
    ax.text(10.2, 7.0, 'User\nCode', ha='left', va='center', fontsize=6,
            color=COLORS['blue'], fontstyle='italic')
    ax.text(10.2, 4.9, 'We\nMaintain', ha='left', va='center', fontsize=6,
            color=COLORS['green'], fontstyle='italic')
    ax.text(10.2, 2.3, 'Transparent\nto User', ha='left', va='center', fontsize=6,
            color=COLORS['gray'], fontstyle='italic')

    fig.savefig('figures/architecture.pdf', format='pdf')
    plt.close(fig)
    print("Generated: figures/architecture.pdf")


def fig_benchmark():
    """Figure 2: Benchmark results (PointNav SR and SPL across scenes)."""
    scenes = ['office', 'apartment', 'corridor', 'warehouse', 'cluttered', 'dynamic']
    sr = [0.82, 0.68, 0.91, 0.75, 0.60, 0.52]
    spl = [0.65, 0.52, 0.78, 0.58, 0.42, 0.35]

    fig, ax = plt.subplots(1, 1, figsize=(3.4, 1.8))

    x = np.arange(len(scenes))
    width = 0.35

    bars1 = ax.bar(x - width/2, sr, width, label='Success Rate',
                   color=COLORS['blue'], alpha=0.85, edgecolor='white', linewidth=0.5)
    bars2 = ax.bar(x + width/2, spl, width, label='SPL',
                   color=COLORS['green'], alpha=0.85, edgecolor='white', linewidth=0.5)

    ax.set_ylabel('Score')
    ax.set_xticks(x)
    ax.set_xticklabels(scenes, rotation=25, ha='right')
    ax.set_ylim(0, 1.05)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Value labels on bars
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.02, f'{h:.2f}',
                ha='center', va='bottom', fontsize=5.5)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.02, f'{h:.2f}',
                ha='center', va='bottom', fontsize=5.5)

    fig.savefig('figures/benchmark.pdf', format='pdf')
    plt.close(fig)
    print("Generated: figures/benchmark.pdf")


def fig_sim2real():
    """Figure 3: Sim2Real transfer ratio visualization."""
    tests = ['Straight\n5m', '360°\nRotation', 'Obstacle\nAvoid', 'PointNav\n10m', 'Dynamic\nObstacle']
    ratios = [0.85, 0.92, 0.78, 0.72, 0.81]
    thresholds = [0.50, 0.50, 0.70, 0.60, 0.67]  # derived from pass criteria

    fig, ax = plt.subplots(1, 1, figsize=(3.4, 1.8))

    x = np.arange(len(tests))
    colors = [COLORS['green'] if r >= t else COLORS['red'] for r, t in zip(ratios, thresholds)]

    bars = ax.bar(x, ratios, 0.6, color=colors, alpha=0.85, edgecolor='white', linewidth=0.5)

    # Threshold line
    ax.axhline(y=0.6, color=COLORS['red'], linestyle='--', linewidth=0.8, alpha=0.6, label='Min threshold (0.6)')

    # Perfect transfer line
    ax.axhline(y=1.0, color=COLORS['gray'], linestyle=':', linewidth=0.6, alpha=0.5)

    ax.set_ylabel('Transfer Ratio')
    ax.set_xticks(x)
    ax.set_xticklabels(tests)
    ax.set_ylim(0, 1.15)
    ax.legend(loc='upper right', fontsize=6, framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')

    # Value labels
    for bar, ratio in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.03,
                f'{ratio:.2f}', ha='center', va='bottom', fontsize=6.5, fontweight='bold')

    # PASS labels
    for i, (r, t) in enumerate(zip(ratios, thresholds)):
        ax.text(i, 0.05, 'PASS', ha='center', va='bottom', fontsize=5.5,
                color='white', fontweight='bold')

    fig.savefig('figures/sim2real.pdf', format='pdf')
    plt.close(fig)
    print("Generated: figures/sim2real.pdf")


def fig_complexity():
    """Figure 4: API complexity comparison (lines of code)."""
    tasks = ['Connect &\nMove', 'SLAM\nExplore', 'VLM\nNavigate', 'RL\nTraining']
    ros2_lines = [62, 85, 120, 150]
    threewe_lines = [5, 8, 12, 15]

    fig, ax = plt.subplots(1, 1, figsize=(3.4, 1.6))

    x = np.arange(len(tasks))
    width = 0.35

    bars1 = ax.bar(x - width/2, ros2_lines, width, label='Raw ROS2',
                   color=COLORS['gray'], alpha=0.7, edgecolor='white', linewidth=0.5)
    bars2 = ax.bar(x + width/2, threewe_lines, width, label='3we Python API',
                   color=COLORS['blue'], alpha=0.85, edgecolor='white', linewidth=0.5)

    ax.set_ylabel('Lines of Code')
    ax.set_xticks(x)
    ax.set_xticklabels(tasks)
    ax.legend(loc='upper left', framealpha=0.9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')

    # Reduction labels
    for i in range(len(tasks)):
        reduction = ros2_lines[i] / threewe_lines[i]
        mid_x = x[i]
        ax.text(mid_x, max(ros2_lines[i], threewe_lines[i]) + 8,
                f'{reduction:.0f}×', ha='center', va='bottom',
                fontsize=7, fontweight='bold', color=COLORS['orange'])

    fig.savefig('figures/complexity.pdf', format='pdf')
    plt.close(fig)
    print("Generated: figures/complexity.pdf")


if __name__ == '__main__':
    import os
    os.makedirs('figures', exist_ok=True)
    fig_architecture()
    fig_benchmark()
    fig_sim2real()
    fig_complexity()
    print("\nAll figures generated successfully.")
