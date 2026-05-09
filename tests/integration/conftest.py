# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for robot platform integration tests.

Provides ROS2 lifecycle management, topic collection, and service calling
utilities. All fixtures gracefully skip when rclpy is unavailable.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Type

import pytest

rclpy = pytest.importorskip(
    "rclpy", reason="rclpy not available — skipping integration tests"
)

from rclpy.node import Node  # noqa: E402


# ---------------------------------------------------------------------------
# Session-scoped: rclpy context
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ros2_context() -> None:
    """Initialize and shutdown rclpy for the entire test session."""
    rclpy.init()
    yield
    rclpy.shutdown()


# ---------------------------------------------------------------------------
# Function-scoped: disposable ROS2 node
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_node(ros2_context: None) -> Node:
    """Create a fresh rclpy Node per test, destroyed after use."""
    node = rclpy.create_node("integration_test_node")
    yield node
    node.destroy_node()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CollectedMessages:
    """Immutable container for messages collected from a topic."""

    messages: List[Any] = field(default_factory=list)


def topic_collector(
    node: Node,
    topic: str,
    msg_type: Type[Any],
    timeout: float = 10.0,
    count: int = 1,
) -> List[Any]:
    """Subscribe to *topic* and collect up to *count* messages within *timeout*.

    Returns the list of collected messages. May return fewer than *count* if
    the timeout expires first.
    """
    collected: List[Any] = []
    event = threading.Event()

    def _callback(msg: Any) -> None:
        collected.append(msg)
        if len(collected) >= count:
            event.set()

    subscription = node.create_subscription(msg_type, topic, _callback, 10)

    deadline = time.monotonic() + timeout
    while not event.is_set() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_subscription(subscription)
    return collected


def service_caller(
    node: Node,
    service: str,
    srv_type: Type[Any],
    request: Any,
    timeout: float = 10.0,
) -> Any:
    """Call a ROS2 service and return its response.

    Raises TimeoutError if the service does not respond within *timeout*.
    Raises RuntimeError if the service is not available.
    """
    client = node.create_client(srv_type, service)

    if not client.wait_for_service(timeout_sec=timeout):
        node.destroy_client(client)
        raise RuntimeError(f"Service '{service}' not available within {timeout}s")

    future = client.call_async(request)

    deadline = time.monotonic() + timeout
    while not future.done() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_client(client)

    if not future.done():
        raise TimeoutError(f"Service '{service}' did not respond within {timeout}s")

    return future.result()


def wait_for_topic(
    node: Node,
    topic: str,
    msg_type: Type[Any],
    timeout: float = 10.0,
) -> Any:
    """Wait for the first message on *topic* and return it.

    Raises TimeoutError if no message arrives within *timeout*.
    """
    messages = topic_collector(node, topic, msg_type, timeout=timeout, count=1)
    if not messages:
        raise TimeoutError(f"No message received on '{topic}' within {timeout}s")
    return messages[0]


# ---------------------------------------------------------------------------
# Pytest fixtures wrapping helpers for convenience
# ---------------------------------------------------------------------------


@pytest.fixture()
def collect_topics(test_node: Node) -> Callable[..., List[Any]]:
    """Return a callable bound to the current test node for topic collection."""

    def _collect(
        topic: str,
        msg_type: Type[Any],
        timeout: float = 10.0,
        count: int = 1,
    ) -> List[Any]:
        return topic_collector(test_node, topic, msg_type, timeout=timeout, count=count)

    return _collect


@pytest.fixture()
def call_service(test_node: Node) -> Callable[..., Any]:
    """Return a callable bound to the current test node for service calls."""

    def _call(
        service: str,
        srv_type: Type[Any],
        request: Any,
        timeout: float = 10.0,
    ) -> Any:
        return service_caller(test_node, service, srv_type, request, timeout=timeout)

    return _call
