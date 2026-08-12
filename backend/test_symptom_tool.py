#!/usr/bin/env python3
"""
Test script for the assess_symptoms_urgency tool
"""

import asyncio
import os
import sys

# Add the src directory to the path so we can import the agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


from agent import Assistant


class MockContext:
    """Mock RunContext for testing"""

    def __init__(self):
        pass


async def test_symptom_assessment():
    """Test the symptom assessment tool with various inputs"""

    # Create an assistant instance
    assistant = Assistant()

    # Create mock context
    ctx = MockContext()

    print("Testing symptom assessment tool...")
    print("=" * 50)

    # Test emergency symptoms
    emergency_tests = [
        "I have chest pain and shortness of breath",
        "I think I'm having a heart attack",
        "I can't breathe and my face is drooping",
        "I have severe bleeding that won't stop",
        "I have a sudden weakness on one side of my body",
        "I have the worst headache of my life",
        "I feel suicidal and want to hurt myself",
    ]

    print("\nTesting EMERGENCY symptoms:")
    for symptom in emergency_tests:
        print(f"\nSymptoms: {symptom}")
        result = await assistant.assess_symptoms_urgency(ctx, symptom)
        # Check if result contains emergency indicators
        if "MEDICAL EMERGENCY" in result and "108" in result:
            print("��✓ Correctly identified as EMERGENCY")
        else:
            print("��✗ Failed to identify as emergency")
            print(f"Result: {result[:100]}...")

    # Test urgent symptoms
    urgent_tests = [
        "I have a high fever over 102 degrees",
        "I've been vomiting blood",
        "I have blood in my stool",
        "I have severe diarrhea and dehydration",
        "I have excruciating abdominal pain",
        "I'm having an allergic reaction with face swelling",
        "I have a high fever with stiff neck",
    ]

    print("\n\nTesting URGENT symptoms:")
    for symptom in urgent_tests:
        print(f"\nSymptoms: {symptom}")
        result = await assistant.assess_symptoms_urgency(ctx, symptom)
        # Check if result contains urgent indicators
        if "URGENT medical attention" in result and "24 hours" in result:
            print("��✓ Correctly identified as URGENT")
        else:
            print("��✗ Failed to identify as urgent")
            print(f"Result: {result[:100]}...")

    # Test routine symptoms
    routine_tests = [
        "I have a mild headache",
        "I have a slight cough",
        "I feel a little tired today",
        "I have a minor sore throat",
        "I have a small cut on my finger",
        "I have seasonal allergies",
        "I have mild indigestion",
    ]

    print("\n\nTesting ROUTINE symptoms:")
    for symptom in routine_tests:
        print(f"\nSymptoms: {symptom}")
        result = await assistant.assess_symptoms_urgency(ctx, symptom)
        # Check if result contains routine indicators
        if "ROUTINE medical evaluation" in result:
            print("��✓ Correctly identified as ROUTINE")
        else:
            print("��✗ Failed to identify as routine")
            print(f"Result: {result[:100]}...")

    # Test error handling (pass None or empty string)
    print("\n\nTesting edge cases:")
    print("\nSymptoms: (empty string)")
    result = await assistant.assess_symptoms_urgency(ctx, "")
    if "unable to assess" in result or "ROUTINE medical evaluation" in result:
        print("��✓ Handled empty string gracefully")
    else:
        print("��✗ Did not handle empty string properly")

    print("\nSymptoms: None (will be converted to string)")
    result = await assistant.assess_symptoms_urgency(ctx, None)
    if "unable to assess" in result or "ROUTINE medical evaluation" in result:
        print("��✓ Handled None gracefully")
    else:
        print("��✗ Did not handle None properly")

    print("\n" + "=" * 50)
    print("Symptom assessment tool testing completed!")


if __name__ == "__main__":
    asyncio.run(test_symptom_assessment())
