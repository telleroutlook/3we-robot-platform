# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

Only the latest release receives security patches.

## Reporting a Vulnerability

**Do NOT file a public GitHub issue for security vulnerabilities.**

Instead, report vulnerabilities via one of:

1. **GitHub Security Advisories** (preferred): Go to the
   [Security Advisories](../../security/advisories/new) page and create a
   new draft advisory.
2. **Email**: Send details to the maintainer email listed in the repository's
   `package.json` or `pyproject.toml`.

### What to Include

- Description of the vulnerability and its impact
- Steps to reproduce or proof-of-concept
- Affected components (firmware, ROS2, SDK, web_control, hardware)
- Suggested fix if you have one

### Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgement | 48 hours |
| Triage and severity assessment | 7 days |
| Fix development | 30 days (critical: 7 days) |
| Public disclosure | After fix is released |

## Severity Classification

| Level | Description | Example |
|-------|-------------|---------|
| Critical | Remote code execution, safety system bypass | Unsigned OTA accepted, E-stop bypass |
| High | Authentication bypass, data exfiltration | DTLS key leak, payload sandbox escape |
| Medium | Denial of service, information disclosure | WebSocket crash, sensor data leak |
| Low | Minor issues with limited impact | Verbose error messages |

## Safe Harbor

We consider security research conducted in good faith to be authorized. We
will not pursue legal action against researchers who:

- Make a good faith effort to avoid privacy violations, data destruction, and
  service disruption
- Only interact with accounts they own or have explicit permission to test
- Do not exploit vulnerabilities beyond what is necessary to confirm their
  existence
- Report findings promptly and do not disclose publicly before a fix is
  available

## Scope

The following are in scope:

- Firmware (ESP32-S3): DTLS implementation, OTA signing, safety FSM
- ROS2 stack: Authentication, message validation, service authorization
- SDK: Payload protocol, web_control interface
- Hardware: Safety relay interlock logic

Out of scope:

- Denial-of-service attacks against production infrastructure
- Social engineering of project maintainers
- Third-party dependencies (report upstream; notify us if it affects this project)
