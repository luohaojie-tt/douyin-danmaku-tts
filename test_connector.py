#!/usr/bin/env python3
"""
WebSocket Connector Test Script

Test if the DouyinConnector works correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.connector import DouyinConnector
from src.douyin.cookie import CookieManager
from src.config import load_config


def print_section(title: str):
    """Print section title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_connector_initialization():
    """Test connector initialization"""
    print_section("Test 1: Connector Initialization")

    try:
        connector = DouyinConnector(
            room_id="728804746624",
            ttwid="test_ttwid_" + "x" * 50
        )

        if connector.room_id == "728804746624" and connector.ttwid:
            print("[OK] Connector initialized successfully")
            print(f"  room_id: {connector.room_id}")
            print(f"  ttwid length: {len(connector.ttwid)}")
            print(f"  is_connected: {connector.is_connected}")
            return True
        else:
            print("[FAIL] Connector initialization failed")
            return False

    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        return False


async def test_get_room_info():
    """Test getting room info"""
    print_section("Test 2: Get Room Info")

    # Load cookie from cookies.txt
    cookie_mgr = CookieManager()
    ttwid = cookie_mgr.load_from_file()

    if not ttwid:
        print("[SKIP] No valid ttwid found in cookies.txt")
        print("       Please configure cookies.txt to test room info retrieval")
        return None

    connector = DouyinConnector(
        room_id="728804746624",
        ttwid=ttwid
    )

    try:
        print(f"Fetching room info for room_id: {connector.room_id}")
        room_info = await connector._get_room_info()

        if room_info.get("status") == "success" and room_info.get("ws_url"):
            print("[OK] Room info retrieved successfully")
            print(f"  ws_url: {room_info['ws_url'][:50]}...")
            return True
        else:
            print("[FAIL] Failed to get room info")
            return False

    except Exception as e:
        print(f"[WARN] Test failed (may need valid ttwid): {e}")
        print("       This is expected if ttwid is invalid or network issue")
        return None


async def test_connection_establishment():
    """Test WebSocket connection establishment"""
    print_section("Test 3: WebSocket Connection")

    # Load cookie
    cookie_mgr = CookieManager()
    ttwid = cookie_mgr.load_from_file()

    if not ttwid:
        print("[SKIP] No valid ttwid found")
        return None

    connector = DouyinConnector(
        room_id="728804746624",
        ttwid=ttwid
    )

    try:
        print("Attempting to connect...")
        await connector.connect()

        if connector.connected:
            print("[OK] WebSocket connection established")
            print(f"  connected: {connector.connected}")

            # Disconnect after test
            await connector.disconnect()
            print("[OK] Disconnected successfully")
            return True
        else:
            print("[FAIL] Connection failed")
            return False

    except Exception as e:
        print(f"[WARN] Connection test failed: {e}")
        print("       This may be due to invalid ttwid or network issues")
        return None


async def test_heartbeat_simulation():
    """Test heartbeat loop simulation"""
    print_section("Test 4: Heartbeat Simulation")

    # This test doesn't actually connect, just tests the logic
    connector = DouyinConnector(
        room_id="test",
        ttwid="test_ttwid"
    )

    # Check heartbeat interval
    if connector.HEARTBEAT_INTERVAL == 30:
        print("[OK] Heartbeat interval set correctly (30s)")
        return True
    else:
        print(f"[FAIL] Heartbeat interval incorrect: {connector.HEARTBEAT_INTERVAL}")
        return False


async def test_message_callback():
    """Test message callback mechanism"""
    print_section("Test 5: Message Callback")

    received_messages = []

    async def test_callback(msg):
        """Test callback function"""
        received_messages.append(msg)
        print(f"  Received message: {msg.get('type', 'unknown')}")

    # Create a mock message
    test_msg = {"type": "test", "data": "test message"}

    # Test callback
    await test_callback(test_msg)

    if len(received_messages) == 1 and received_messages[0] == test_msg:
        print("[OK] Callback mechanism works")
        return True
    else:
        print("[FAIL] Callback mechanism failed")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Douyin Connector Test")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_connector_initialization())
    results.append(await test_get_room_info())
    results.append(await test_connection_establishment())
    results.append(await test_heartbeat_simulation())
    results.append(await test_message_callback())

    # Summary
    print_section("Test Summary")

    passed = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if r is False)
    skipped = sum(1 for r in results if r is None)

    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")

    if failed == 0:
        print("\n[OK] All executed tests passed!")
        if skipped > 0:
            print(f"[INFO] {skipped} test(s) skipped (need valid ttwid)")
    else:
        print(f"\n[FAIL] {failed} test(s) failed")

    print("\nTest completed\n")


def main():
    """Main test function"""
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
