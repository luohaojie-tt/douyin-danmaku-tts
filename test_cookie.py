#!/usr/bin/env python3
"""
Cookie Manager Test Script

Test if the Cookie management functionality works correctly.
"""

import sys
import tempfile
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager


def print_section(title: str):
    """Print section title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_load_valid_cookie():
    """Test loading valid cookie from file"""
    print_section("Test 1: Load Valid Cookie")

    # Create a temporary cookie file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("ttwid=valid_ttwid_1234567890abcdefghijklmnopqrstyz" + "x" * 50)
        temp_file = f.name

    try:
        cookie_mgr = CookieManager(temp_file)
        ttwid = cookie_mgr.load_from_file()

        if ttwid and len(ttwid) > 50:
            print(f"[OK] Cookie loaded successfully")
            print(f"  ttwid length: {len(ttwid)}")
            print(f"  ttwid prefix: {ttwid[:20]}...")
        else:
            print(f"[FAIL] Cookie loading failed")
    finally:
        Path(temp_file).unlink()


def test_load_empty_file():
    """Test loading from empty file"""
    print_section("Test 2: Load Empty File")

    # Create an empty file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_file = f.name

    try:
        cookie_mgr = CookieManager(temp_file)
        ttwid = cookie_mgr.load_from_file()

        if ttwid is None:
            print("[OK] Correctly returned None for empty file")
        else:
            print(f"[FAIL] Should return None, got: {ttwid}")
    finally:
        Path(temp_file).unlink()


def test_load_nonexistent_file():
    """Test loading from nonexistent file"""
    print_section("Test 3: Load Nonexistent File")

    cookie_mgr = CookieManager("nonexistent_cookies.txt")
    ttwid = cookie_mgr.load_from_file()

    if ttwid is None:
        print("[OK] Correctly returned None for nonexistent file")
    else:
        print(f"[FAIL] Should return None, got: {ttwid}")


def test_validate_ttwid():
    """Test ttwid validation"""
    print_section("Test 4: Validate ttwid")

    cookie_mgr = CookieManager()

    test_cases = [
        ("valid_ttwid_with_enough_characters_" + "x" * 50, True, "Valid ttwid"),
        ("", False, "Empty ttwid"),
        ("short", False, "Too short ttwid"),
        ("ttwid_with_invalid_chars@#$", False, "Invalid characters"),
    ]

    all_passed = True
    for ttwid, expected, description in test_cases:
        result = cookie_mgr.validate_ttwid(ttwid)
        if result == expected:
            print(f"[OK] {description}: {result}")
        else:
            print(f"[FAIL] {description}: expected {expected}, got {result}")
            all_passed = False

    return all_passed


def test_parse_ttwid():
    """Test parsing ttwid from content"""
    print_section("Test 5: Parse ttwid from Content")

    cookie_mgr = CookieManager()

    test_cases = [
        ("ttwid=test_value\n", "test_value", "Simple format"),
        ("ttwid = test_value_with_spaces\n", "test_value_with_spaces", "Format with spaces"),
        ("# This is a comment\nttwid=value_after_comment\n", "value_after_comment", "After comment"),
        ("ttwid=value1\n\nttwid=value2\n", "value1", "First value"),
        ("ttwid=value_with_%_symbol\n", "value_with_%_symbol", "With % symbol"),
    ]

    all_passed = True
    for content, expected, description in test_cases:
        result = cookie_mgr._parse_ttwid(content)
        if result == expected:
            print(f"[OK] {description}: {result}")
        else:
            print(f"[FAIL] {description}: expected '{expected}', got '{result}'")
            all_passed = False

    return all_passed


def test_load_from_actual_cookies():
    """Test loading from actual cookies.txt if exists"""
    print_section("Test 6: Load from Actual cookies.txt")

    cookie_mgr = CookieManager("cookies.txt")
    ttwid = cookie_mgr.load_from_file()

    if ttwid:
        print(f"[OK] Loaded from cookies.txt")
        print(f"  ttwid length: {len(ttwid)}")
        print(f"  ttwid prefix: {ttwid[:20]}...")
    else:
        print("[WARN] cookies.txt not found or empty (this is expected if not configured)")


def test_save_to_file():
    """Test saving ttwid to file"""
    print_section("Test 7: Save ttwid to File")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_file = f.name

    try:
        cookie_mgr = CookieManager(temp_file)
        test_ttwid = "test_ttwid_" + "x" * 50

        success = cookie_mgr.save_to_file(test_ttwid)

        if success:
            # Verify the file was written
            content = Path(temp_file).read_text()
            if test_ttwid in content:
                print("[OK] ttwid saved and verified")
            else:
                print("[FAIL] File saved but content incorrect")
        else:
            print("[FAIL] Failed to save ttwid")

        # Clean up
        Path(temp_file).unlink()

    except Exception as e:
        print(f"[FAIL] Exception: {e}")


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("  Cookie Manager Test")
    print("=" * 60)

    # Run tests
    test_load_valid_cookie()
    test_load_empty_file()
    test_load_nonexistent_file()
    result1 = test_validate_ttwid()
    result2 = test_parse_ttwid()
    test_load_from_actual_cookies()
    test_save_to_file()

    # Summary
    print_section("Test Summary")
    if result1 and result2:
        print("[OK] All core tests passed! Cookie module works correctly")
    else:
        print("[FAIL] Some tests failed, please check implementation")

    print("\nTest completed\n")


if __name__ == "__main__":
    main()
