## Description

<!-- Describe your changes concisely. What problem does this solve? -->

## Type of Change

- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `refactor` — Code change that neither fixes a bug nor adds a feature
- [ ] `docs` — Documentation only
- [ ] `test` — Adding or updating tests
- [ ] `chore` — Build process, CI, or tooling changes
- [ ] `hw` — Hardware design changes

## Component

- [ ] Firmware (`firmware/`)
- [ ] ROS2 (`ros2_ws/`)
- [ ] SDK (`sdk/`)
- [ ] Hardware (`hardware/`)
- [ ] Documentation (`docs/`)

## Checklist

### Required

- [ ] Code compiles without warnings
- [ ] Tests pass locally (`make test` / `colcon test` / `npx playwright test`)
- [ ] SPDX license headers added to new files
- [ ] No secrets or credentials in the code
- [ ] Commits are signed off (`git commit -s`) for DCO compliance

### CLA

- [ ] I have signed the [Individual CLA](CLA-INDIVIDUAL.md) (first-time contributors)
- [ ] _OR_ my organization has signed the [Corporate CLA](CLA-CORPORATE.md)

### If Safety-Critical

Changes to E-stop, motor control, battery management, OTA, or safety relay logic
require review from **two maintainers**.

- [ ] This PR touches safety-critical code
- [ ] Two maintainer approvals obtained (if applicable)

### Documentation

- [ ] Documentation updated (if user-facing behavior changed)
- [ ] API changes reflected in relevant docs

## Testing

<!-- Describe how you tested these changes -->

## Related Issues

<!-- Link related issues: Closes #123, Fixes #456 -->
