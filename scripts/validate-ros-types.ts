// SPDX-License-Identifier: Apache-2.0
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, basename, join } from 'node:path';

const ROOT = resolve(import.meta.dirname!, '..');
const MSG_DIR = join(ROOT, 'ros2_ws/robot_interfaces/msg');
const SRV_DIR = join(ROOT, 'ros2_ws/robot_interfaces/srv');
const TYPES_FILE = join(ROOT, 'sdk/web_control/src/types.ts');
const SAFETY_H = join(ROOT, 'firmware/esp32/main/safety.h');
const CUSTOM_MARKER = '// --- Custom robot platform types ---';

interface Field {
  name: string;
  rosType: string;
  tsType: string;
}

function rosTypeToTs(rosType: string): string {
  if (rosType === 'bool') return 'boolean';
  if (rosType === 'string') return 'string';
  if (/^(float|double|u?int|byte)/.test(rosType)) return 'number';
  return rosType;
}

function parseMsgFields(content: string): Field[] {
  const fields: Field[] = [];
  for (const raw of content.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    if (/^\w+\s+[A-Z_]+=/.test(line)) continue;
    if (/^std_msgs\/Header\s/.test(line)) continue;
    const m = line.match(/^(\S+)\s+(\w+)/);
    if (m) fields.push({ name: m[2], rosType: m[1], tsType: rosTypeToTs(m[1]) });
  }
  return fields;
}

function parseSrv(content: string): { request: Field[]; response: Field[] } {
  const [req, res] = content.split('---');
  return { request: parseMsgFields(req), response: parseMsgFields(res ?? '') };
}

function parseTsInterfaces(content: string): Map<string, Field[]> {
  const markerIdx = content.indexOf(CUSTOM_MARKER);
  if (markerIdx === -1) return new Map();
  const section = content.slice(markerIdx);
  const endIdx = section.indexOf('\n// ---', CUSTOM_MARKER.length);
  const block = endIdx === -1 ? section : section.slice(0, endIdx);

  const interfaces = new Map<string, Field[]>();
  let current: string | null = null;

  for (const line of block.split('\n')) {
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
        const normalized = tsType === 'boolean' ? 'boolean'
          : tsType === 'string' ? 'string'
          : tsType === 'number' ? 'number'
          : tsType.startsWith("'") ? 'string'
          : tsType;
        interfaces.get(current)!.push({ name: fieldMatch[1], rosType: '', tsType: normalized });
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
  for (const line of enumBlock[1].split('\n')) {
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
  for (const line of content.split('\n')) {
    const m = line.trim().match(/^\w+\s+([A-Z_]+)=(\d+)/);
    if (m) constants.set(m[1], parseInt(m[2]));
  }
  return constants;
}

let errors = 0;
let warnings = 0;
let passed = 0;
let failed = 0;

function compare(rosFields: Field[], tsFields: Field[], rosLabel: string, tsLabel: string): string[] {
  const tsMap = new Map(tsFields.filter(f => f.name !== 'header').map(f => [f.name, f]));
  const rosMap = new Map(rosFields.map(f => [f.name, f]));
  const issues: string[] = [];

  for (const rf of rosFields) {
    if (!tsMap.has(rf.name)) {
      issues.push(`  [ERROR] ${rosLabel} has '${rf.name}' (${rf.rosType}) — missing in ${tsLabel}`);
      errors++;
    } else {
      const tf = tsMap.get(rf.name)!;
      if (rf.tsType !== 'Header' && tf.tsType !== rf.tsType) {
        issues.push(`  [WARN]  Type mismatch: '${rf.name}' — .msg=${rf.rosType}→${rf.tsType}, ts=${tf.tsType}`);
        warnings++;
      }
    }
  }
  for (const tf of tsFields) {
    if (tf.name === 'header') continue;
    if (!rosMap.has(tf.name)) {
      issues.push(`  [ERROR] ${tsLabel} has '${tf.name}' — missing in ${rosLabel}`);
      errors++;
    }
  }
  return issues;
}

// --- Main ---
console.log('=== ROS2 ↔ TypeScript Type Validation ===\n');

const tsContent = readFileSync(TYPES_FILE, 'utf-8');
const tsInterfaces = parseTsInterfaces(tsContent);

// Phase 1a: Messages
for (const file of readdirSync(MSG_DIR).filter(f => f.endsWith('.msg'))) {
  const name = basename(file, '.msg');
  const content = readFileSync(join(MSG_DIR, file), 'utf-8');
  const rosFields = parseMsgFields(content);
  const tsFields = tsInterfaces.get(name);

  if (!tsFields) {
    console.log(`✗ ${file} ↔ ${name}`);
    console.log(`  [ERROR] Interface '${name}' not found in types.ts\n`);
    errors++;
    failed++;
    continue;
  }

  const issues = compare(rosFields, tsFields, `.msg`, 'types.ts');
  console.log(`${issues.length === 0 ? '✓' : '✗'} ${file} ↔ ${name}`);
  if (issues.length > 0) { issues.forEach(i => console.log(i)); console.log(''); }
  issues.length === 0 ? passed++ : failed++;
}

// Phase 1b: Services
for (const file of readdirSync(SRV_DIR).filter(f => f.endsWith('.srv'))) {
  const name = basename(file, '.srv');
  const content = readFileSync(join(SRV_DIR, file), 'utf-8');
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
    allIssues.push(...compare(response, resFields, `${file} response`, resName));
  }

  console.log(`${allIssues.length === 0 ? '✓' : '✗'} ${label}`);
  if (allIssues.length > 0) { allIssues.forEach(i => console.log(i)); console.log(''); }
  allIssues.length === 0 ? passed++ : failed++;
}

// Phase 2: Firmware enum vs ROS constants
console.log('\n=== Firmware ↔ ROS2 Constant Validation ===\n');

if (existsSync(SAFETY_H)) {
  const safetyContent = readFileSync(SAFETY_H, 'utf-8');
  const fwEnums = parseSafetyEnum(safetyContent);
  const srvContent = readFileSync(join(SRV_DIR, 'EmergencyStop.srv'), 'utf-8');
  const rosConsts = parseSrvConstants(srvContent);

  const mapping: [string, string][] = [
    ['SAFETY_NORMAL', 'STATE_NORMAL'],
    ['SAFETY_ESTOPPED', 'STATE_ESTOPPED'],
    ['SAFETY_RECOVERY_PENDING', 'STATE_RECOVERY'],
    ['SAFETY_RELAY_FAULT', 'STATE_RELAY_FAULT'],
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
      console.log(`  [ERROR] Value mismatch: ${fw}=${fwVal} vs ${ros}=${rosVal}`);
      errors++;
      enumOk = false;
    }
  }
  console.log(`${enumOk ? '✓' : '✗'} safety_state_t ↔ EmergencyStop.srv constants`);
  enumOk ? passed++ : failed++;
}

// Summary
console.log(`\n${'─'.repeat(40)}`);
console.log(`Result: ${passed} passed, ${failed} failed (${errors} errors, ${warnings} warnings)`);
process.exit(errors > 0 ? 1 : 0);
