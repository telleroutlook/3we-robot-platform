# Contributing to Robot Platform

感谢你对本项目的兴趣！以下是参与贡献的指南。

Thank you for your interest in this project! Below are guidelines for contributing.

## Getting Started

### Development Environment

- **Firmware**: ESP-IDF v5.x + micro-ROS
- **ROS2**: Humble or Jazzy
- **Python**: 3.10+
- **Hardware Design**: KiCad 8+

### Fork & Clone

```bash
git clone https://github.com/<your-username>/robot-platform.git
cd robot-platform
```

## Branch Strategy

```
main          ← stable, release-ready
  └─ feature/ ← new features
  └─ fix/     ← bug fixes
  └─ docs/    ← documentation only
```

- Branch from `main`
- One feature/fix per branch
- Keep branches short-lived

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]
```

### Types

| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |
| `chore` | Build, CI, tooling |
| `perf` | Performance improvement |
| `hw` | Hardware design change |

### Scopes

| Scope | Area |
|-------|------|
| `firmware` | ESP32 firmware |
| `ros2` | ROS2 packages |
| `hardware` | PCB, structure, BOM |
| `sdk` | Payload SDK |
| `docs` | Documentation |

### Examples

```
feat(firmware): add DTLS 1.3 support for control channel
fix(ros2): correct odometry drift compensation
hw(hardware): update motor driver footprint to DRV8833
docs: add assembly guide for standard kit
```

## Pull Request Process

1. Ensure your code builds without errors
2. Add or update tests for new functionality
3. Update documentation if behavior changes
4. Fill in the PR template completely
5. Request review from at least one maintainer

### PR Title Format

Same as commit message format: `type(scope): description`

### PR Checklist

- [ ] Code compiles without warnings
- [ ] Tests pass locally
- [ ] SPDX license headers added to new files
- [ ] No secrets or credentials committed
- [ ] Documentation updated if needed

## Code Style

### Source File Headers

All source files must include an SPDX header:

```c
// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2024 Robot Platform Contributors
```

### Firmware (C/ESP-IDF)

- Follow ESP-IDF coding style
- Use `snake_case` for functions and variables
- Prefix public API functions with module name: `motor_init()`, `comm_send()`

### ROS2 (Python/C++)

- Follow ROS2 coding guidelines
- Python: PEP 8
- C++: ament style (based on Google C++ Style)

### Hardware (KiCad)

- Use project-specific symbol/footprint libraries
- Include design rationale in schematic text notes
- Version BOM spreadsheets alongside schematic changes

## Issue Guidelines

### Bug Reports

Use the bug report template. Include:
- Hardware revision / firmware version
- Steps to reproduce
- Expected vs actual behavior
- Logs or screenshots

### Feature Requests

Use the feature request template. Include:
- Use case description
- Proposed solution (if any)
- Alternatives considered

## Safety-Critical Contributions

Changes to the following areas require extra scrutiny:

- **Emergency stop circuit** — Must maintain ISO 13850 compliance
- **Motor control** — Must respect safety relay interlock
- **Battery management** — Must preserve protection circuit integrity
- **OTA updates** — Must maintain Ed25519 signature verification

These changes require review from at least two maintainers.

## Licensing

- **Code contributions** are licensed under Apache 2.0 (see `LICENSE`)
- **Hardware contributions** are licensed under CERN-OHL-P v2 (see `LICENSE-HARDWARE`)
- **Documentation contributions** are licensed under CC BY-SA 4.0 (see `LICENSE-DOCS`)

By submitting a pull request, you agree that your contributions will be licensed under the same terms as the respective component.

### Developer Certificate of Origin (DCO)

We use the [DCO](https://developercertificate.org/) to certify that contributors have the right to submit their work. Sign off your commits:

```bash
git commit -s -m "feat(firmware): add battery SOC estimation"
```

This adds a `Signed-off-by` line to your commit message.

## Community

- Be respectful and constructive
- Help newcomers get started
- Focus on the technical merits of contributions
- See our [Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)

## Questions?

Open a Discussion or Issue if you're unsure about anything. We're happy to help!
