#!/usr/bin/env python3
"""
Test script to verify agent memory tools functionality
"""

import sys
import os
import asyncio
import json

# Add the parent directory to sys.path so we can import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import Assistant
from livekit.agents import function_tool, RunContext

# Mock RunContext for testing
class MockRunContext:
    pass

async def test_agent_memory_tools():
    print("Testing agent memory tools...")

    # Create an instance of the Assistant
    assistant = Assistant()

    # Test 1: look_up_caller for non-existent user
    print("\n1. Testing look_up_caller for non-existent user...")
    ctx = MockRunContext()
    result = await assistant.look_up_caller(ctx, "non_existent_user_123")
    print(f"Result: {result}")
    assert "No prior information found" in result
    print("������✓ Non-existent caller lookup test passed")

    # Test 2: save_caller_info
    print("\n2. Testing save_caller_info...")
    test_facts = json.dumps({
        "age_band": "30-40",
        "ongoing_conditions": ["diabetes"],
        "last_triage_outcome": "advised to check blood sugar regularly"
    })
    result = await assistant.save_caller_info(
        ctx,
        "test_patient_456",
        "Priya Sharma",
        "en",
        test_facts
    )
    print(f"Result: {result}")
    assert "Successfully saved information" in result
    print("������✓ Save caller info test passed")

    # Test 3: look_up_caller for existing user
    print("\n3. Testing look_up_caller for existing user...")
    result = await assistant.look_up_caller(ctx, "test_patient_456")
    print(f"Result: {result}")
    assert "Found caller info" in result
    assert "Priya Sharma" in result
    assert "diabetes" in result
    print("������✓ Existing caller lookup test passed")

    print("\n���������🎉 All agent memory tools tests passed!")
    return True

async def main():
    success = await test_agent_memory_tools()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)