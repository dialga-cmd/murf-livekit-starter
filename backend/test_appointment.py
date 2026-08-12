#!/usr/bin/env python3
"""Test the appointment booking functionality."""

import asyncio

from agent import Assistant


class MockCtx:
    pass


async def test_appointment_booking():
    print("Testing appointment booking functionality...")

    a = Assistant()
    ctx = MockCtx()

    # Test 1: Successful appointment booking
    print("\\n1. Testing successful appointment booking:")
    result = await a.book_appointment(
        ctx,
        location="Bangalore",
        specialty="general practice",
        preferred_date="2026-08-15",
        preferred_time="10:30 AM",
        patient_name="John Doe",
        symptoms="Fever and cough",
    )
    print(result)
    assert "Appointment booked successfully!" in result
    assert "John Doe" in result
    assert "Confirmation Number:" in result

    # Test 2: Missing required information
    print("\\n2. Testing missing required information:")
    result = await a.book_appointment(
        ctx,
        location="",  # Missing location
        specialty="general practice",
        preferred_date="2026-08-15",
        preferred_time="10:30 AM",
        patient_name="John Doe",
    )
    print(result)
    assert "Please provide all required information" in result

    # Test 3: No clinics found (small town)
    print("\\n3. Testing no clinics found:")
    result = await a.book_appointment(
        ctx,
        location="SmallVille",
        specialty="general practice",
        preferred_date="2026-08-15",
        preferred_time="10:30 AM",
        patient_name="John Doe",
    )
    print(result)
    assert (
        "couldn't find any" in result.lower() or "could not find any" in result.lower()
    )

    print("\\n��✅ All appointment booking tests passed!")


if __name__ == "__main__":
    asyncio.run(test_appointment_booking())
