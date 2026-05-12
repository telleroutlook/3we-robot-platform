# SPDX-License-Identifier: Apache-2.0
# Root Makefile — orchestrates all subsystem builds, tests, and checks.

.PHONY: all build test lint validate clean help
.PHONY: firmware-build firmware-test
.PHONY: ros2-build ros2-test
.PHONY: web-build web-test web-lint web-format
.PHONY: python-lint python-test
.PHONY: docker-build docker-up docker-down
.PHONY: validate-types validate-params validate-pins validate-bom validate-kconfig coverage

# Default target
all: lint test build

# ─── Help ─────────────────────────────────────────────────────────────────────

help:
	@echo "Robot Platform — Build & Test Orchestration"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  all              Lint, test, and build everything (default)"
	@echo "  build            Build all subsystems"
	@echo "  test             Run all tests"
	@echo "  lint             Run all linters"
	@echo "  validate         Cross-layer validation (all checks)"
	@echo "  validate-types   ROS2 ↔ TypeScript ↔ firmware type alignment"
	@echo "  validate-params  Firmware params ↔ ROS2 launch file"
	@echo "  validate-pins    GPIO pin conflict detection"
	@echo "  validate-bom     BOM ↔ firmware component alignment"
	@echo "  validate-kconfig Kconfig constraint validation"
	@echo "  coverage         Generate test coverage reports"
	@echo "  clean            Remove build artifacts"
	@echo ""
	@echo "  firmware-build   Build ESP32 firmware (requires ESP-IDF)"
	@echo "  firmware-test    Run firmware host-side unit tests"
	@echo "  ros2-build       Build ROS2 workspace (requires colcon)"
	@echo "  ros2-test        Run ROS2 tests"
	@echo "  web-build        Build web_control frontend"
	@echo "  web-test         Run Playwright E2E tests"
	@echo "  web-lint         Lint and type-check web_control"
	@echo "  python-lint      Lint Python SDK with ruff"
	@echo "  python-test      Run Python SDK tests"
	@echo ""
	@echo "  docker-build     Build production Docker image"
	@echo "  docker-up        Start docker-compose stack"
	@echo "  docker-down      Stop docker-compose stack"
	@echo ""

# ─── Firmware ─────────────────────────────────────────────────────────────────

firmware-build:
	cd firmware/esp32 && idf.py build

firmware-test:
	cd firmware/tests && make clean && make && ./test_runner

# ─── ROS2 ────────────────────────────────────────────────────────────────────

ros2-build:
	cd ros2_ws && colcon build --symlink-install

ros2-test:
	cd ros2_ws && colcon test && colcon test-result --verbose

# ─── Web Control ──────────────────────────────────────────────────────────────

web-build:
	cd sdk/web_control && npm run build

web-test:
	cd sdk/web_control && npm run test:unit
	cd sdk/web_control && npx playwright test

web-lint:
	cd sdk/web_control && npm run typecheck
	cd sdk/web_control && npm run lint
	cd sdk/web_control && npm run format:check

web-format:
	cd sdk/web_control && npm run format
	cd sdk/web_control && npm run lint:fix

# ─── Python SDK ───────────────────────────────────────────────────────────────

python-lint:
	ruff format --check sdk/
	ruff check sdk/

python-test:
	cd sdk && python -m pytest tests/ -v --tb=short

# ─── Cross-Layer Validation ───────────────────────────────────────────────────

validate-types:
	npx tsx scripts/validate-ros-types.ts

validate-params:
	npx tsx scripts/validate-robot-params.ts

validate-pins:
	python3 scripts/validate-pin-conflicts.py

validate-bom:
	python3 scripts/validate-bom-firmware.py

validate-kconfig:
	python3 scripts/validate-kconfig-constraints.py

validate: validate-types validate-params validate-pins validate-bom validate-kconfig web-lint python-lint

# ─── Coverage ─────────────────────────────────────────────────────────────────

coverage:
	cd sdk/web_control && npm run test:coverage
	cd sdk && python -m pytest tests/ --cov=payload_interface --cov-report=term --cov-report=xml:coverage.xml

# ─── Aggregate Targets ────────────────────────────────────────────────────────

build: web-build

test: firmware-test web-test python-test

lint: web-lint python-lint

# ─── Docker ───────────────────────────────────────────────────────────────────

docker-build:
	docker build -t robot-platform:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# ─── Clean ────────────────────────────────────────────────────────────────────

clean:
	rm -rf sdk/web_control/dist
	rm -rf sdk/web_control/node_modules/.vite
	rm -rf ros2_ws/build ros2_ws/install ros2_ws/log
	cd firmware/tests && make clean 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
