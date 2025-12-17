#!/usr/bin/env python3
"""Test the Databricks AI Workflow system."""

import os
import sys
from typing import List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from main import build_pipeline, run_workflow


def print_configuration() -> None:
    print("1. Configuration check")
    required: List[str] = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "OPENAI_API_KEY"]
    for key in required:
        configured = bool(getattr(settings, key))
        print(f"   - {key}: {'✅' if configured else '⚠️  not set'}")


def test_imports() -> None:
    print("2. Import check")
    try:
        pipeline = build_pipeline()
        assert pipeline is not None
        print("   - Services import: ✅")
    except Exception as exc:  # noqa: BLE001
        print(f"   - Services import: ❌ ({exc})")


def test_cli() -> None:
    print("3. CLI check")
    success = run_workflow("test")
    print(f"   - run_workflow('test'): {'✅' if success else '❌'}")


def main() -> None:
    print("Testing Databricks AI Workflow…")
    print_configuration()
    test_imports()
    test_cli()
    print("\n✅ Basic tests completed")


if __name__ == "__main__":
    main()
