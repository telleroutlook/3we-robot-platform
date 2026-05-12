// SPDX-License-Identifier: Apache-2.0
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { resolve, basename, join } from "node:path";

const ROOT = resolve(import.meta.dirname!, "..");
const MSG_DIR = join(ROOT, "ros2_ws/robot_interfaces/msg");
const SRV_DIR = join(ROOT, "ros2_ws/robot_interfaces/srv");
const ACTION_DIR = join(ROOT, "ros2_ws/robot_interfaces/action");
const TYPES_FILE = join(ROOT, "sdk/web_control/src/types.ts");
const COMPONENTS_DIR = join(ROOT, "sdk/web_control/src/components");
const SAFETY_H = join(ROOT, "firmware/esp32/main/safety.h");
const PAYLOAD_HOTPLUG_C = join(ROOT, "firmware/esp32/main/payload_hotplug.c");
const CAPABILITY_FLAGS_PY = join(
  ROOT,
  "sdk/payload_interface/capability_flags.py",
);
const CUSTOM_MARKER = "// --- Custom robot platform types ---";

interface Field {
  name: string;
  rosType: string;
  tsType: string;
}

interface RosConstant {
  name: string;
  value: number;
  source: string;
}

function rosTypeToTs(rosType: string): string {
  if (rosType === "bool") return "boolean";
  if (rosType === "string") return "string";
  if (/^(float|double|u?int|byte)/.test(rosType)) return "number";
  return rosType;
}

function parseMsgFields(content: string): Field[] {
  const fields: Field[] = [];
  for (const raw of content.split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    if (/^\w+\s+[A-Z_]+=/.test(line)) continue;
    if (/^std_msgs\/Header\s/.test(line)) continue;
    const m = line.match(/^(\S+)\s+(\w+)/);
    if (m)
      fields.push({ name: m[2], rosType: m[1], tsType: rosTypeToTs(m[1]) });
  }
  return fields;
}

function parseMsgConstants(content: string): RosConstant[] {
  const constants: RosConstant[] = [];
  for (const line of content.split("\n")) {
    const m = line.trim().match(/^\w+\s+([A-Z_]+)=(\d+)/);
    if (m) constants.push({ name: m[1], value: parseInt(m[2]), source: "" });
  }
  return constants;
}

function parseSrv(content: string): { request: Field[]; response: Field[] } {
  const [req, res] = content.split("---");
  return { request: parseMsgFields(req), response: parseMsgFields(res ?? "") };
}

function parseAction(content: string): {
  goal: Field[];
  result: Field[];
  feedback: Field[];
} {
  const parts = content.split("---");
  return {
    goal: parseMsgFields(parts[0] ?? ""),
    result: parseMsgFields(parts[1] ?? ""),
    feedback: parseMsgFields(parts[2] ?? ""),
  };
}

function parseTsInterfaces(content: string): Map<string, Field[]> {
  const markerIdx = content.indexOf(CUSTOM_MARKER);
  if (markerIdx === -1) return new Map();
  const section = content.slice(markerIdx);
  const endIdx = section.indexOf("\n// ---", CUSTOM_MARKER.length);
  const block = endIdx === -1 ? section : section.slice(0, endIdx);

  const interfaces = new Map<string, Field[]>();
  let current: string | null = null;

  for (const line of block.split("\n")) {
    const ifaceMatch = line.match(/^export interface (\w+)\s*\{/);
    if (ifaceMatch) {
      current = ifaceMatch[1];
      interfaces.set(current, []);
      continue;
    }
    if (current && /^\}/.test(line)) {
      current = null;
      continue;
    }
    if (current) {
      const fieldMatch = line.match(/^\s+(\w+)\??:\s*(.+);/);
      if (fieldMatch) {
        const tsType = fieldMatch[2].trim();
        const normalized =
          tsType === "boolean"
            ? "boolean"
            : tsType === "string"
              ? "string"
              : tsType === "number"
                ? "number"
                : tsType.startsWith("'")
                  ? "string"
                  : tsType;
        interfaces
          .get(current)!
          .push({ name: fieldMatch[1], rosType: "", tsType: normalized });
      }
    }
  }
  return interfaces;
}

function parseSafetyEnum(content: string): Map<string, number> {
  const enums = new Map<string, number>();
  const enumBlock = content.match(/typedef enum \{([^}]+)\}/s);
  if (!enumBlock) return enums;
  let value = 0;
  for (const line of enumBlock[1].split("\n")) {
    const m = line.trim().match(/^(\w+)\s*(?:=\s*(\d+))?\s*,?/);
    if (m) {
      if (m[2] !== undefined) value = parseInt(m[2]);
      enums.set(m[1], value);
      value++;
    }
  }
  return enums;
}

function parseSrvConstants(content: string): Map<string, number> {
  const constants = new Map<string, number>();
  for (const line of content.split("\n")) {
    const m = line.trim().match(/^\w+\s+([A-Z_]+)=(\d+)/);
    if (m) constants.set(m[1], parseInt(m[2]));
  }
  return constants;
}

function parseTsNumericRecord(content: string): Map<number, string> {
  const map = new Map<number, string>();
  const regex = /(\d+):\s*['"]([A-Z_]+)['"]/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(content)) !== null) {
    map.set(parseInt(m[1]), m[2]);
  }
  return map;
}

function parseFirmwareCapFlags(content: string): Map<string, number> {
  const flags = new Map<string, number>();
  const regex = /#define\s+(CAP_\w+)\s+\(1\s*<<\s*(\d+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(content)) !== null) {
    flags.set(m[1], 1 << parseInt(m[2]));
  }
  return flags;
}

function parsePythonCapFlags(content: string): Map<string, number> {
  const flags = new Map<string, number>();
  const regex = /^(CAP_\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)/gm;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(content)) !== null) {
    flags.set(m[1], parseInt(m[2]));
  }
  return flags;
}

let errors = 0;
let warnings = 0;
let passed = 0;
let failed = 0;

function compare(
  rosFields: Field[],
  tsFields: Field[],
  rosLabel: string,
  tsLabel: string,
): string[] {
  const tsMap = new Map(
    tsFields.filter((f) => f.name !== "header").map((f) => [f.name, f]),
  );
  const rosMap = new Map(rosFields.map((f) => [f.name, f]));
  const issues: string[] = [];

  for (const rf of rosFields) {
    if (!tsMap.has(rf.name)) {
      issues.push(
        `  [ERROR] ${rosLabel} has '${rf.name}' (${rf.rosType}) — missing in ${tsLabel}`,
      );
      errors++;
    } else {
      const tf = tsMap.get(rf.name)!;
      if (rf.tsType !== "Header" && tf.tsType !== rf.tsType) {
        issues.push(
          `  [WARN]  Type mismatch: '${rf.name}' — .msg=${rf.rosType}→${rf.tsType}, ts=${tf.tsType}`,
        );
        warnings++;
      }
    }
  }
  for (const tf of tsFields) {
    if (tf.name === "header") continue;
    if (!rosMap.has(tf.name)) {
      issues.push(
        `  [ERROR] ${tsLabel} has '${tf.name}' — missing in ${rosLabel}`,
      );
      errors++;
    }
  }
  return issues;
}

// --- Main ---
console.log("=== Phase 1: ROS2 Messages ↔ TypeScript ===\n");

const tsContent = readFileSync(TYPES_FILE, "utf-8");
const tsInterfaces = parseTsInterfaces(tsContent);

// Phase 1a: Messages
for (const file of readdirSync(MSG_DIR).filter((f) => f.endsWith(".msg"))) {
  const name = basename(file, ".msg");
  const content = readFileSync(join(MSG_DIR, file), "utf-8");
  const rosFields = parseMsgFields(content);
  const tsFields = tsInterfaces.get(name);

  if (!tsFields) {
    console.log(`✗ ${file} ↔ ${name}`);
    console.log(`  [ERROR] Interface '${name}' not found in types.ts\n`);
    errors++;
    failed++;
    continue;
  }

  const issues = compare(rosFields, tsFields, `.msg`, "types.ts");
  console.log(`${issues.length === 0 ? "✓" : "✗"} ${file} ↔ ${name}`);
  if (issues.length > 0) {
    issues.forEach((i) => console.log(i));
    console.log("");
  }
  issues.length === 0 ? passed++ : failed++;
}

// Phase 1b: Services
for (const file of readdirSync(SRV_DIR).filter((f) => f.endsWith(".srv"))) {
  const name = basename(file, ".srv");
  const content = readFileSync(join(SRV_DIR, file), "utf-8");
  const { request, response } = parseSrv(content);

  const reqName = `${name}Request`;
  const resName = `${name}Response`;
  const reqFields = tsInterfaces.get(reqName) ?? tsInterfaces.get(name);
  const resFields = tsInterfaces.get(resName);

  const label = `${file} ↔ ${reqName}/${resName}`;
  const allIssues: string[] = [];

  if (!reqFields) {
    allIssues.push(`  [ERROR] Interface '${reqName}' not found in types.ts`);
    errors++;
  } else if (request.length > 0) {
    const usedName = tsInterfaces.has(reqName) ? reqName : name;
    allIssues.push(...compare(request, reqFields, `${file} request`, usedName));
  }

  if (!resFields) {
    allIssues.push(`  [ERROR] Interface '${resName}' not found in types.ts`);
    errors++;
  } else if (response.length > 0) {
    allIssues.push(
      ...compare(response, resFields, `${file} response`, resName),
    );
  }

  console.log(`${allIssues.length === 0 ? "✓" : "✗"} ${label}`);
  if (allIssues.length > 0) {
    allIssues.forEach((i) => console.log(i));
    console.log("");
  }
  allIssues.length === 0 ? passed++ : failed++;
}

// Phase 2: Firmware enum vs ROS constants
console.log("\n=== Phase 2: Firmware Enums ↔ ROS2 Constants ===\n");

if (existsSync(SAFETY_H)) {
  const safetyContent = readFileSync(SAFETY_H, "utf-8");
  const fwEnums = parseSafetyEnum(safetyContent);
  const srvContent = readFileSync(join(SRV_DIR, "EmergencyStop.srv"), "utf-8");
  const rosConsts = parseSrvConstants(srvContent);

  const mapping: [string, string][] = [
    ["SAFETY_NORMAL", "STATE_NORMAL"],
    ["SAFETY_ESTOPPED", "STATE_ESTOPPED"],
    ["SAFETY_RECOVERY_PENDING", "STATE_RECOVERY"],
    ["SAFETY_RELAY_FAULT", "STATE_RELAY_FAULT"],
  ];

  let enumOk = true;
  for (const [fw, ros] of mapping) {
    const fwVal = fwEnums.get(fw);
    const rosVal = rosConsts.get(ros);
    if (fwVal === undefined) {
      console.log(`  [ERROR] Firmware missing enum '${fw}'`);
      errors++;
      enumOk = false;
    } else if (rosVal === undefined) {
      console.log(`  [ERROR] ROS srv missing constant '${ros}'`);
      errors++;
      enumOk = false;
    } else if (fwVal !== rosVal) {
      console.log(
        `  [ERROR] Value mismatch: ${fw}=${fwVal} vs ${ros}=${rosVal}`,
      );
      errors++;
      enumOk = false;
    }
  }
  console.log(
    `${enumOk ? "✓" : "✗"} safety_state_t ↔ EmergencyStop.srv constants`,
  );
  enumOk ? passed++ : failed++;
}

// Phase 3: Action files ↔ TypeScript
console.log("\n=== Phase 3: ROS2 Actions ↔ TypeScript ===\n");

if (existsSync(ACTION_DIR)) {
  for (const file of readdirSync(ACTION_DIR).filter((f) =>
    f.endsWith(".action"),
  )) {
    const name = basename(file, ".action");
    const content = readFileSync(join(ACTION_DIR, file), "utf-8");
    const { goal, result, feedback } = parseAction(content);

    const sections: [string, Field[], string][] = [
      ["Goal", goal, `${name}Goal`],
      ["Result", result, `${name}Result`],
      ["Feedback", feedback, `${name}Feedback`],
    ];

    let actionHasTs = false;
    for (const [, , tsName] of sections) {
      if (tsInterfaces.has(tsName)) {
        actionHasTs = true;
        break;
      }
    }

    if (!actionHasTs) {
      console.log(`  ${file} — no TypeScript interfaces (skipped)`);
      continue;
    }

    for (const [sectionName, rosFields, tsName] of sections) {
      const tsFields = tsInterfaces.get(tsName);
      if (!tsFields) {
        console.log(`✗ ${file} ${sectionName}`);
        console.log(`  [ERROR] Interface '${tsName}' not found in types.ts\n`);
        errors++;
        failed++;
        continue;
      }
      const issues = compare(
        rosFields,
        tsFields,
        `${file} ${sectionName}`,
        tsName,
      );
      console.log(
        `${issues.length === 0 ? "✓" : "✗"} ${file} ${sectionName} ↔ ${tsName}`,
      );
      if (issues.length > 0) {
        issues.forEach((i) => console.log(i));
        console.log("");
      }
      issues.length === 0 ? passed++ : failed++;
    }
  }
}

// Phase 4: ROS2 msg constants ↔ TypeScript component literals
console.log("\n=== Phase 4: ROS2 Constants ↔ TypeScript Literals ===\n");

if (existsSync(COMPONENTS_DIR)) {
  const componentFiles = readdirSync(COMPONENTS_DIR).filter(
    (f) => f.endsWith(".ts") && !f.endsWith(".test.ts"),
  );

  for (const file of readdirSync(MSG_DIR).filter((f) => f.endsWith(".msg"))) {
    const msgName = basename(file, ".msg");
    const content = readFileSync(join(MSG_DIR, file), "utf-8");
    const rosConstants = parseMsgConstants(content);
    if (rosConstants.length === 0) continue;

    const componentFile = componentFiles.find((f) => {
      const src = readFileSync(join(COMPONENTS_DIR, f), "utf-8");
      return src.includes(`/${msgName}`) || src.includes(`msg/${msgName}`);
    });
    if (!componentFile) continue;

    const componentContent = readFileSync(
      join(COMPONENTS_DIR, componentFile),
      "utf-8",
    );
    const tsRecord = parseTsNumericRecord(componentContent);
    if (tsRecord.size === 0) continue;

    let constOk = true;
    for (const rc of rosConstants) {
      const tsLabel = tsRecord.get(rc.value);
      if (!tsLabel) {
        console.log(
          `  [WARN]  ${msgName}: ROS constant ${rc.name}=${rc.value} has no TS mapping in ${componentFile}`,
        );
        warnings++;
        constOk = false;
      } else if (tsLabel !== rc.name) {
        const rosShort = rc.name.replace(/^(STATE_|STAGE_)/, "");
        if (tsLabel !== rosShort) {
          console.log(
            `  [WARN]  ${msgName}: ROS ${rc.name}=${rc.value} ↔ TS ${rc.value}:'${tsLabel}' (name mismatch)`,
          );
          warnings++;
          constOk = false;
        }
      }
    }
    console.log(`${constOk ? "✓" : "⚠"} ${file} constants ↔ ${componentFile}`);
    constOk ? passed++ : failed++;
  }
}

// Phase 5: Capability flags — firmware ↔ Python SDK
console.log("\n=== Phase 5: Capability Flags — Firmware ↔ Python SDK ===\n");

if (existsSync(PAYLOAD_HOTPLUG_C) && existsSync(CAPABILITY_FLAGS_PY)) {
  const fwContent = readFileSync(PAYLOAD_HOTPLUG_C, "utf-8");
  const pyContent = readFileSync(CAPABILITY_FLAGS_PY, "utf-8");
  const fwFlags = parseFirmwareCapFlags(fwContent);
  const pyFlags = parsePythonCapFlags(pyContent);

  let capOk = true;

  for (const [name, fwVal] of fwFlags) {
    const pyVal = pyFlags.get(name);
    if (pyVal === undefined) {
      console.log(
        `  [ERROR] Firmware defines '${name}' (0x${fwVal.toString(16)}) — missing in Python SDK`,
      );
      errors++;
      capOk = false;
    } else if (pyVal !== fwVal) {
      console.log(
        `  [ERROR] Value mismatch: '${name}' — firmware=0x${fwVal.toString(16)}, python=0x${pyVal.toString(16)}`,
      );
      errors++;
      capOk = false;
    }
  }

  for (const [name] of pyFlags) {
    if (!fwFlags.has(name)) {
      console.log(
        `  [ERROR] Python SDK defines '${name}' — missing in firmware`,
      );
      errors++;
      capOk = false;
    }
  }

  console.log(
    `${capOk ? "✓" : "✗"} payload_hotplug.c ↔ capability_flags.py (${fwFlags.size} flags)`,
  );
  capOk ? passed++ : failed++;
}

// Phase 6: Cross-file ROS2 constant consistency
console.log("\n=== Phase 6: Cross-File ROS2 Constant Consistency ===\n");

const allRosConstants = new Map<string, RosConstant[]>();

function collectConstants(dir: string, ext: string): void {
  if (!existsSync(dir)) return;
  for (const file of readdirSync(dir).filter((f) => f.endsWith(ext))) {
    const content = readFileSync(join(dir, file), "utf-8");
    for (const line of content.split("\n")) {
      const m = line.trim().match(/^\w+\s+([A-Z_]+)=(\d+)/);
      if (m) {
        const name = m[1];
        const value = parseInt(m[2]);
        if (!allRosConstants.has(name)) allRosConstants.set(name, []);
        allRosConstants.get(name)!.push({ name, value, source: file });
      }
    }
  }
}

collectConstants(MSG_DIR, ".msg");
collectConstants(SRV_DIR, ".srv");

let crossOk = true;
for (const [name, entries] of allRosConstants) {
  if (entries.length < 2) continue;
  const first = entries[0];
  for (let i = 1; i < entries.length; i++) {
    if (entries[i].value !== first.value) {
      console.log(
        `  [ERROR] '${name}' value conflict: ${first.source} defines ${first.value}, ${entries[i].source} defines ${entries[i].value}`,
      );
      errors++;
      crossOk = false;
    }
  }
}

if (crossOk) {
  const dupes = [...allRosConstants.entries()].filter(([, v]) => v.length > 1);
  console.log(
    `✓ All shared constants consistent (${dupes.length} constants appear in multiple files)`,
  );
  passed++;
} else {
  failed++;
}

// Summary
console.log(`\n${"─".repeat(50)}`);
console.log(
  `Result: ${passed} passed, ${failed} failed (${errors} errors, ${warnings} warnings)`,
);
process.exit(errors > 0 ? 1 : 0);
