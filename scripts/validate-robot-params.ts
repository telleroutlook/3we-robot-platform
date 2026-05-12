// SPDX-License-Identifier: Apache-2.0
import { readFileSync, existsSync } from "node:fs";
import { resolve, join } from "node:path";

const ROOT = resolve(import.meta.dirname!, "..");
const SDKCONFIG_DIR = join(ROOT, "firmware/esp32");
const ROBOT_PARAMS_H = join(ROOT, "firmware/config/robot_params.h");
const LAUNCH_FILE = join(ROOT, "ros2_ws/robot_bringup/launch/robot.launch.py");

interface SkuParams {
  wheel_radius_m: number;
  track_width_m: number;
  wheelbase_m: number;
}

const SKUS = ["basic", "standard", "industrial"] as const;

function parseSdkconfigDefaults(sku: string): Map<string, number> {
  const file = join(SDKCONFIG_DIR, `sdkconfig.defaults.${sku}`);
  const values = new Map<string, number>();
  if (!existsSync(file)) return values;
  for (const line of readFileSync(file, "utf-8").split("\n")) {
    const m = line.match(/^(CONFIG_\w+)=(\d+)$/);
    if (m) values.set(m[1], parseInt(m[2]));
  }
  return values;
}

function parseRobotParamsDefaults(): SkuParams {
  const content = readFileSync(ROBOT_PARAMS_H, "utf-8");
  const radius = content.match(/#define\s+WHEEL_RADIUS_MM\s+([\d.]+)f/);
  const track = content.match(/#define\s+WHEEL_SEPARATION_MM\s+([\d.]+)f/);
  const wheelbase = content.match(/#define\s+WHEELBASE_MM\s+([\d.]+)f/);
  return {
    wheel_radius_m: radius ? parseFloat(radius[1]) / 1000 : NaN,
    track_width_m: track ? parseFloat(track[1]) / 1000 : NaN,
    wheelbase_m: wheelbase ? parseFloat(wheelbase[1]) / 1000 : NaN,
  };
}

function getFirmwareParams(sku: string): SkuParams | null {
  const cfg = parseSdkconfigDefaults(sku);
  const hasGeometry = cfg.has("CONFIG_CHASSIS_WHEEL_RADIUS_MM_X10");

  if (!hasGeometry) {
    if (sku === "basic") return parseRobotParamsDefaults();
    return null;
  }

  return {
    wheel_radius_m: cfg.get("CONFIG_CHASSIS_WHEEL_RADIUS_MM_X10")! / 10 / 1000,
    track_width_m: cfg.get("CONFIG_CHASSIS_TRACK_WIDTH_MM")! / 1000,
    wheelbase_m: cfg.get("CONFIG_CHASSIS_WHEELBASE_MM")! / 1000,
  };
}

function parseLaunchFileParams(): Map<string, SkuParams> {
  const content = readFileSync(LAUNCH_FILE, "utf-8");
  const results = new Map<string, SkuParams>();

  const blockRegex =
    /^(INDUSTRIAL|STANDARD|BASIC)_XACRO_ARGS\s*=\s*\(([\s\S]*?)\)/gm;
  let match: RegExpExecArray | null;

  while ((match = blockRegex.exec(content)) !== null) {
    const sku = match[1].toLowerCase();
    const block = match[2];

    const radius = block.match(/wheel_radius:=([\d.]+)/);
    const wheelbase = block.match(/wheelbase:=([\d.]+)/);
    const track = block.match(/track_width:=([\d.]+)/);

    if (radius && wheelbase && track) {
      results.set(sku, {
        wheel_radius_m: parseFloat(radius[1]),
        track_width_m: parseFloat(track[1]),
        wheelbase_m: parseFloat(wheelbase[1]),
      });
    }
  }

  return results;
}

function approxEqual(a: number, b: number, tolerance = 0.0005): boolean {
  return Math.abs(a - b) < tolerance;
}

let errors = 0;
let passed = 0;

console.log("=== Robot Parameters: Firmware ↔ ROS2 Launch File ===\n");

if (!existsSync(LAUNCH_FILE)) {
  console.log("[SKIP] Launch file not found");
  process.exit(0);
}

const launchParams = parseLaunchFileParams();

for (const sku of SKUS) {
  const fwParams = getFirmwareParams(sku);
  const rosParams = launchParams.get(sku);

  if (!fwParams) {
    console.log(`  [SKIP] ${sku}: No firmware geometry config found`);
    continue;
  }
  if (!rosParams) {
    console.log(`  [WARN] ${sku}: No launch file params found`);
    continue;
  }

  let skuOk = true;

  const checks: [string, number, number][] = [
    ["wheel_radius", fwParams.wheel_radius_m, rosParams.wheel_radius_m],
    ["track_width", fwParams.track_width_m, rosParams.track_width_m],
    ["wheelbase", fwParams.wheelbase_m, rosParams.wheelbase_m],
  ];

  for (const [name, fwVal, rosVal] of checks) {
    if (!approxEqual(fwVal, rosVal)) {
      console.log(
        `  [ERROR] ${sku}.${name}: firmware=${fwVal.toFixed(4)}m, launch=${rosVal.toFixed(4)}m`,
      );
      errors++;
      skuOk = false;
    }
  }

  if (skuOk) {
    console.log(
      `✓ ${sku}: wheel_radius=${fwParams.wheel_radius_m}m, track=${fwParams.track_width_m}m, wheelbase=${fwParams.wheelbase_m}m`,
    );
    passed++;
  }
}

console.log(`\n${"─".repeat(50)}`);
console.log(`Result: ${passed} passed, ${errors} errors`);
process.exit(errors > 0 ? 1 : 0);
