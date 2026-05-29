#!/usr/bin/env python3
"""Aerodynamic shape optimization example using DiffCFD's differentiable solver.

Demonstrates how to optimize a 2D cross-section shape for minimal drag using
DiffCFD's differentiable Navier-Stokes solver. The shape is parameterized with
B-spline control points from DiffCFD's BSplineAirfoil class, enabling gradient-
based optimization through the entire CFD pipeline.

Application to 3we-robot chassis design:
    Mobile robots operating at moderate speeds (5-15 m/s) experience non-trivial
    aerodynamic drag. For a 3we-robot platform with a rectangular chassis, the
    drag coefficient Cd may be 0.8-1.2. By optimizing the leading-edge and
    trailing-edge cross-section shapes, Cd can often be reduced to 0.3-0.5,
    extending battery life by 10-20% at cruising speed.

    This example optimizes the 2D mid-plane cross-section, which corresponds to
    the dominant flow direction seen by the robot chassis during forward motion.
    In practice, a full 3D optimization would follow the same pattern but with
    a 3D mesh.

Workflow:
    1. Define a channel flow simulation domain
    2. Parameterize the body shape with B-spline control points
    3. Run the differentiable SIMPLE solver to obtain (ux, uy, p)
    4. Compute drag force via pressure integration
    5. Backpropagate through the solver to update control points

Requirements:
    pip install diffcfd torch numpy matplotlib

Usage:
    python aero_shape_opt.py
"""

from __future__ import annotations

import numpy as np
import torch

# ---------------------------------------------------------------------------
# NOTE: This example uses DiffCFD's API. If DiffCFD is not installed, the
# example will print installation instructions and exit gracefully.
# ---------------------------------------------------------------------------
try:
    from diffcfd.geometry.airfoil import BSplineAirfoil, compute_forces
    from diffcfd.geometry.mesh import CartesianMesh
    from diffcfd.solvers.navier_stokes_2d import NavierStokes2D
except ImportError:
    print("DiffCFD is required for this example.")
    print("Install with:  pip install diffcfd")
    print("Or clone from:  https://github.com/your-org/DiffCFD")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Simulation domain — represents a 2D wind-tunnel slice through the robot
LX = 4.0       # channel length (m)
LY = 1.0       # channel height (m)
NX = 64        # grid cells in x (coarse for speed; production would use 128+)
NY = 32        # grid cells in y

# Robot chassis cross-section parameters
CHORD = 0.8    # body length along flow direction (m)
LE_X = 1.2     # leading-edge x-position (centered in domain)
CY = 0.5       # centerline y-position

# Flow conditions — representative of 3we-robot at 10 m/s
# Re = U * L / nu.  For a 0.8m chord at 10 m/s in air (nu ~ 1.5e-5):
#   Re = 10 * 0.8 / 1.5e-5 ~ 530,000
# We use a much lower Re (100) for demonstration with a coarse grid.
REYNOLDS = 100
INLET_VELOCITY = 1.0

# Optimization parameters
N_CONTROL_POINTS = 6   # B-spline control points per surface
N_OPTIM_STEPS = 30
LEARNING_RATE = 0.005

# Allow only y-displacement of control points to maintain chord
# x-positions are fixed; only y-offsets are optimized
MAX_Y_OFFSET = 0.08  # maximum displacement from initial shape (m)


def run_optimization() -> None:
    """Run the drag minimization loop and print results."""

    device = "cpu"
    print("=" * 65)
    print("  3we-Robot Aerodynamic Shape Optimization via DiffCFD")
    print("=" * 65)
    print()
    print(f"Domain: {LX}m x {LY}m, grid {NX}x{NY}")
    print(f"Body chord: {CHORD}m, Re={REYNOLDS}, U_inlet={INLET_VELOCITY} m/s")
    print(f"Control points: {N_CONTROL_POINTS} per surface")
    print(f"Optimization: {N_OPTIM_STEPS} steps, lr={LEARNING_RATE}")
    print()

    # ---- 1. Set up mesh, solver, and shape parameterization ----
    mesh = CartesianMesh(NX, NY, lx=LX, ly=LY, device=device)
    solver = NavierStokes2D(
        reynolds_number=REYNOLDS,
        grid=(NX, NY),
        device=device,
        backward="implicit_diff",
        lx=LX,
        ly=LY,
        max_iter=500,
        tol=1e-4,
    )
    airfoil = BSplineAirfoil(
        n_control_points=N_CONTROL_POINTS,
        chord=CHORD,
        leading_edge_x=LE_X,
        center_y=CY,
    )

    # Initial control points — NACA 0012-like symmetric shape
    cp_initial = airfoil.initial_control_points().clone()
    print(f"Initial control points shape: {cp_initial.shape}")
    print(f"  (2 * {N_CONTROL_POINTS} points = upper + lower surface)")
    print()

    # ---- 2. Define optimizable parameters ----
    # Only y-offsets are trainable; x-coordinates are frozen to maintain
    # the chord length and leading/trailing-edge positions.
    y_offsets = torch.zeros(cp_initial.shape[0], device=device, requires_grad=True)

    optimizer = torch.optim.Adam([y_offsets], lr=LEARNING_RATE)

    # ---- 3. Optimization loop ----
    print(f"{'Step':>5}  {'Drag (N/m)':>12}  {'Status':>20}")
    print("-" * 45)

    drag_history = []

    for step in range(N_OPTIM_STEPS):
        optimizer.zero_grad()

        # Build current control points = initial + clamped offsets
        cp_current = cp_initial.clone()
        cp_current[:, 1] = cp_current[:, 1] + torch.clamp(
            y_offsets, -MAX_Y_OFFSET, MAX_Y_OFFSET
        )

        # Compute SDF from B-spline control points
        sdf = airfoil.sdf(mesh, cp_current)

        # Run differentiable SIMPLE solver
        ux, uy, p = solver.solve_steady(
            sdf=sdf,
            inlet_velocity=INLET_VELOCITY,
            case="channel",
        )

        # Compute drag force (per unit span width, N/m)
        # This is differentiable w.r.t. the control points through the solver
        drag, lift = compute_forces(
            p=p, ux=ux, uy=uy, mesh=mesh, sdf=sdf,
            mu=1.0 / REYNOLDS,
        )

        # Backpropagate and update
        drag.backward()
        optimizer.step()

        drag_val = drag.item()
        lift_val = lift.item()
        drag_history.append(drag_val)

        status = ""
        if step > 0 and drag_val < min(drag_history[:-1]):
            status = "new best"
        elif step == 0:
            status = "initial"

        print(f"{step:5d}  {drag_val:12.6f}  {status:>20}")

    # ---- 4. Report results ----
    print()
    print("=" * 65)
    print("  Optimization Summary")
    print("=" * 65)
    print(f"  Initial drag:  {drag_history[0]:.6f} N/m")
    print(f"  Final drag:    {drag_history[-1]:.6f} N/m")
    reduction = (1.0 - drag_history[-1] / drag_history[0]) * 100
    print(f"  Reduction:     {reduction:.1f}%")
    print()

    # ---- 5. Robot chassis design implications ----
    print("  Application to 3we-robot chassis design:")
    print(f"    - Original Cd estimate (bluff body): ~0.9")
    if reduction > 0:
        print(f"    - Optimized Cd estimate:            ~{0.9 * (1 - reduction/100):.2f}")
    print(f"    - For a 3we-robot at 10 m/s:")
    print(f"      Power saved ~ {reduction:.0f}% of aerodynamic power loss")
    print(f"      At 10 m/s with 0.5 m^2 frontal area:")
    rho_air = 1.225  # kg/m^3
    area = 0.5  # m^2
    v = 10.0  # m/s
    power_before = 0.5 * rho_air * v**3 * area * 0.9
    power_after = power_before * (1 - reduction / 100)
    print(f"        Power(aero) before: {power_before:.1f} W")
    print(f"        Power(aero) after:  {power_after:.1f} W")
    print(f"        Battery life gain:  ~{reduction * 0.6:.0f}% at cruise")
    print()

    # ---- 6. Print final control point positions ----
    with torch.no_grad():
        cp_final = cp_initial.clone()
        cp_final[:, 1] = cp_final[:, 1] + torch.clamp(
            y_offsets, -MAX_Y_OFFSET, MAX_Y_OFFSET
        )
    print("  Final B-spline control point offsets (y, meters):")
    for i in range(cp_final.shape[0]):
        dy = cp_final[i, 1].item() - cp_initial[i, 1].item()
        label = "upper" if i < N_CONTROL_POINTS else "lower"
        print(f"    CP[{i:2d}] ({label}): dy = {dy:+.4f}")

    print()
    print("Done. In production, increase grid resolution (128x64+),")
    print("Reynolds number, and optimization steps for convergent results.")


if __name__ == "__main__":
    run_optimization()
