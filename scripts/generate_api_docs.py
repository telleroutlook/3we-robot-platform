# SPDX-License-Identifier: Apache-2.0
"""Generate markdown API reference from the threewe package via introspection.

Inspects the threewe package and all submodules to produce a structured markdown
document with table of contents, class signatures, method signatures, and docstrings.

Usage:
    python scripts/generate_api_docs.py
    python scripts/generate_api_docs.py --output docs/api_reference.md
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any

# Modules to introspect, in documentation order
MODULES = [
    "threewe",
    "threewe.robot",
    "threewe.types",
    "threewe.backends",
    "threewe.gym",
    "threewe.gym.envs",
    "threewe.ai",
    "threewe.ai.vlm_runner",
    "threewe.ai.vla_runner",
    "threewe.data",
    "threewe.data.recorder",
    "threewe.data.hub",
    "threewe.benchmark",
    "threewe.benchmark.runner",
    "threewe.benchmark.metrics",
    "threewe.benchmark.tasks",
    "threewe.cli",
    "threewe.config",
    "threewe.exceptions",
]


def safe_import(module_name: str) -> Any | None:
    """Import a module, returning None if it fails (missing optional deps)."""
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError) as e:
        print(f"  Warning: Could not import {module_name}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(
            f"  Warning: Unexpected error importing {module_name}: {e}", file=sys.stderr
        )
        return None


def get_signature(obj: Any) -> str:
    """Get the signature string for a callable."""
    try:
        sig = inspect.signature(obj)
        return str(sig)
    except (ValueError, TypeError):
        return "(...)"


def get_docstring(obj: Any) -> str:
    """Get cleaned docstring for an object."""
    doc = inspect.getdoc(obj)
    return doc if doc else ""


def is_public(name: str) -> bool:
    """Check if a name is public (not private/dunder)."""
    return not name.startswith("_")


def get_classes(module: Any) -> list[tuple[str, Any]]:
    """Get all public classes defined in a module."""
    classes = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if is_public(name) and obj.__module__ == module.__name__:
            classes.append((name, obj))
    return sorted(classes, key=lambda x: x[0])


def get_functions(module: Any) -> list[tuple[str, Any]]:
    """Get all public functions defined in a module."""
    functions = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if is_public(name) and obj.__module__ == module.__name__:
            functions.append((name, obj))
    return sorted(functions, key=lambda x: x[0])


def get_methods(cls: Any) -> list[tuple[str, Any]]:
    """Get all public methods of a class."""
    methods = []
    for name, obj in inspect.getmembers(cls, predicate=inspect.isfunction):
        if is_public(name):
            methods.append((name, obj))
    # Also include properties
    for name in dir(cls):
        if is_public(name) and isinstance(getattr(cls, name, None), property):
            methods.append((name, getattr(cls, name)))
    return sorted(set(methods), key=lambda x: x[0])


def format_class_doc(class_name: str, cls: Any, module_name: str) -> str:
    """Format documentation for a single class."""
    lines = []
    lines.append(f"### `{class_name}`")
    lines.append("")

    doc = get_docstring(cls)
    if doc:
        lines.append(doc)
        lines.append("")

    # Constructor signature
    init = getattr(cls, "__init__", None)
    if init and init is not object.__init__:
        sig = get_signature(init)
        lines.append("```python")
        lines.append(f"{class_name}{sig}")
        lines.append("```")
        lines.append("")

        init_doc = get_docstring(init)
        if init_doc:
            lines.append(init_doc)
            lines.append("")

    # Methods
    methods = get_methods(cls)
    public_methods = [
        (name, m)
        for name, m in methods
        if name != "__init__" and not name.startswith("_")
    ]

    if public_methods:
        lines.append("**Methods:**")
        lines.append("")

        for method_name, method in public_methods:
            if isinstance(method, property):
                lines.append(f"- `{method_name}` *(property)*")
                prop_doc = get_docstring(method)
                if prop_doc:
                    first_line = prop_doc.split("\n")[0]
                    lines.append(f"  {first_line}")
            else:
                sig = get_signature(method)
                lines.append(f"- `{method_name}{sig}`")
                method_doc = get_docstring(method)
                if method_doc:
                    first_line = method_doc.split("\n")[0]
                    lines.append(f"  {first_line}")

        lines.append("")

    return "\n".join(lines)


def format_function_doc(func_name: str, func: Any) -> str:
    """Format documentation for a single function."""
    lines = []
    sig = get_signature(func)
    lines.append(f"### `{func_name}{sig}`")
    lines.append("")

    doc = get_docstring(func)
    if doc:
        lines.append(doc)
        lines.append("")

    return "\n".join(lines)


def generate_toc(sections: list[tuple[str, str]]) -> str:
    """Generate a table of contents from section titles."""
    lines = ["## Table of Contents", ""]
    for title, anchor in sections:
        lines.append(f"- [{title}](#{anchor})")
    lines.append("")
    return "\n".join(lines)


def generate_section(
    title: str, anchor: str, module_names: list[str]
) -> tuple[str, bool]:
    """Generate a documentation section for one or more modules.

    Returns:
        Tuple of (markdown content, whether any content was generated).
    """
    lines = []
    lines.append(f"## {title}")
    lines.append("")

    has_content = False

    for module_name in module_names:
        mod = safe_import(module_name)
        if mod is None:
            lines.append(
                f"*Module `{module_name}` could not be loaded (missing optional dependencies).*"
            )
            lines.append("")
            continue

        module_doc = get_docstring(mod)
        if module_doc:
            lines.append(f"> {module_doc.split(chr(10))[0]}")
            lines.append("")

        classes = get_classes(mod)
        functions = get_functions(mod)

        if not classes and not functions:
            continue

        has_content = True

        if len(module_names) > 1:
            lines.append(f"### Module: `{module_name}`")
            lines.append("")

        for class_name, cls in classes:
            lines.append(format_class_doc(class_name, cls, module_name))

        for func_name, func in functions:
            lines.append(format_function_doc(func_name, func))

    return "\n".join(lines), has_content


def generate_api_reference() -> str:
    """Generate the full API reference markdown document."""
    sections_config = [
        ("Robot", "robot", ["threewe.robot"]),
        ("Types", "types", ["threewe.types"]),
        ("Backends", "backends", ["threewe.backends"]),
        ("Gymnasium Environments", "gymnasium-environments", ["threewe.gym.envs"]),
        ("AI Module", "ai-module", ["threewe.ai.vlm_runner", "threewe.ai.vla_runner"]),
        ("Data Module", "data-module", ["threewe.data.recorder", "threewe.data.hub"]),
        (
            "Benchmark",
            "benchmark",
            [
                "threewe.benchmark.runner",
                "threewe.benchmark.metrics",
                "threewe.benchmark.tasks",
            ],
        ),
        ("CLI", "cli", ["threewe.cli"]),
        ("Configuration", "configuration", ["threewe.config"]),
        ("Exceptions", "exceptions", ["threewe.exceptions"]),
    ]

    # Generate all sections first to see which ones have content
    generated_sections: list[tuple[str, str, str]] = []
    for title, anchor, module_names in sections_config:
        content, has_content = generate_section(title, anchor, module_names)
        generated_sections.append((title, anchor, content))

    # Build document
    doc_lines = []
    doc_lines.append("# threewe API Reference")
    doc_lines.append("")
    doc_lines.append(
        "Auto-generated API documentation for the `threewe` Python package."
    )
    doc_lines.append("")

    # Get version
    version_mod = safe_import("threewe")
    if version_mod and hasattr(version_mod, "__version__"):
        doc_lines.append(f"**Version**: {version_mod.__version__}")
        doc_lines.append("")

    # TOC
    toc_entries = [(title, anchor) for title, anchor, _ in generated_sections]
    doc_lines.append(generate_toc(toc_entries))

    # Sections
    for _, _, content in generated_sections:
        doc_lines.append(content)
        doc_lines.append("")

    return "\n".join(doc_lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate markdown API reference for the threewe package"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/api_reference.md",
        help="Output file path (default: docs/api_reference.md)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)

    print("Generating API documentation...")
    print("  Package: threewe")

    # Ensure we can import the package
    root_mod = safe_import("threewe")
    if root_mod is None:
        print("Error: Cannot import threewe. Ensure it is installed.", file=sys.stderr)
        print("  Try: pip install -e sdk/threewe", file=sys.stderr)
        sys.exit(1)

    print(f"  Version: {getattr(root_mod, '__version__', 'unknown')}")

    # Pre-import all modules to surface any issues
    print("  Importing submodules...")
    for module_name in MODULES:
        mod = safe_import(module_name)
        if mod:
            print(f"    {module_name}: OK")
        else:
            print(f"    {module_name}: SKIPPED (optional deps missing)")

    # Generate the document
    content = generate_api_reference()

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"\nAPI reference written to: {output_path}")
    print(f"  Size: {len(content):,} bytes")


if __name__ == "__main__":
    main()
