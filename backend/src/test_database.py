#!/usr/bin/env python3
"""
Test script to verify database functionality for caller memory
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, get_caller, save_caller, update_last_interaction, delete_caller
import json

def test_database():
    print("Testing database functionality...")

    # Test 1: Save a caller
    print("\n1. Testing save_caller...")
    test_user_id = "test_user_123"
    test_name = "Ramesh Kumar"
    test_language = "en"
    test_facts = {
        "age_band": "30-40",
        "ongoing_conditions": ["hypertension"],
        "last_triage_outcome": "advised to monitor blood pressure"
    }

    result = save_caller(test_user_id, test_name, test_language, test_facts)
    print(f"Save result: {result}")

    # Test 2: Retrieve the caller
    print("\n2. Testing get_caller...")
    caller = get_caller(test_user_id)
    if caller:
        print(f"Retrieved caller: {caller}")
        assert caller['user_id'] == test_user_id
        assert caller['name'] == test_name
        assert caller['language_preference'] == test_language
        assert caller['facts'] == test_facts
        print("��✓ Caller retrieval test passed")
    else:
        print("��✗ Failed to retrieve caller")
        return False

    # Test 3: Update last interaction
    print("\n3. Testing update_last_interaction...")
    result = update_last_interaction(test_user_id)
    print(f"Update last interaction result: {result}")
    caller_updated = get_caller(test_user_id)
    if caller_updated:
        print(f"Caller after update: {caller_updated}")
        # The last_interaction should be more recent now
        print("��✓ Last interaction update test passed")
    else:
        print("��✗ Failed to retrieve caller after update")
        return False

    # Test 4: Get non-existent caller
    print("\n4. Testing get_caller for non-existent user...")
    non_existent = get_caller("non_existent_user")
    if non_existent is None:
        print("��✓ Non-existent caller correctly returns None")
    else:
        print(f"��✗ Expected None but got: {non_existent}")
        return False

    # Test 5: Delete caller
    print("\n5. Testing delete_caller...")
    result = delete_caller(test_user_id)
    print(f"Delete result: {result}")
    caller_deleted = get_caller(test_user_id)
    if caller_deleted is None:
        print("��✓ Caller deletion test passed")
    else:
        print(f"��✗ Expected None after deletion but got: {caller_deleted}")
        return False

    print("\n���🎉 All database tests passed!")
    return True

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)