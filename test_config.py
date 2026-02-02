#!/usr/bin/env python3
"""
Configuration Module Test Script

Test if the configuration loading functionality works correctly.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import load_config, DEFAULT_CONFIG


def print_section(title: str):
    """Print section title"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_config(config):
    """Print configuration content"""
    print_section("Room Config (room)")
    print(f"  room_id: {config.room.room_id}")
    print(f"  cookie_file: {config.room.cookie_file}")
    print(f"  auto_reconnect: {config.room.auto_reconnect}")
    print(f"  heartbeat_interval: {config.room.heartbeat_interval}")

    print_section("TTS Config (tts)")
    print(f"  engine: {config.tts.engine}")
    print(f"  voice: {config.tts.voice}")
    print(f"  rate: {config.tts.rate}")
    print(f"  volume: {config.tts.volume}")
    print(f"  cache_enabled: {config.tts.cache_enabled}")
    print(f"  cache_days: {config.tts.cache_days}")

    print_section("Filter Config (filter)")
    print(f"  min_length: {config.filter.min_length}")
    print(f"  max_length: {config.filter.max_length}")
    print(f"  enable_filter: {config.filter.enable_filter}")
    print(f"  users.blocked: {config.filter.users.blocked}")
    print(f"  users.only_vip: {config.filter.users.only_vip}")
    print(f"  keywords.blocked: {config.filter.keywords.blocked}")
    print(f"  keywords.only: {config.filter.keywords.only}")

    print_section("Playback Config (playback)")
    print(f"  max_queue_size: {config.playback.max_queue_size}")
    print(f"  play_interval: {config.playback.play_interval}")
    print(f"  volume: {config.playback.volume}")

    print_section("Log Config (log)")
    print(f"  level: {config.log.level}")
    print(f"  enable_console: {config.log.enable_console}")
    print(f"  enable_file: {config.log.enable_file}")
    print(f"  file_path: {config.log.file_path}")


def test_default_config():
    """Test default configuration"""
    print_section("Test 1: Default Config")
    print("Testing if DEFAULT_CONFIG loads correctly...")

    if DEFAULT_CONFIG:
        print("[OK] Default config loaded successfully")
        print_config(DEFAULT_CONFIG)
    else:
        print("[FAIL] Default config loading failed")


def test_load_config_from_file():
    """Test loading config from file"""
    print_section("Test 2: Load from config.ini")
    print("Testing if load_config('config.ini') works correctly...")

    # Check if config.ini exists
    config_file = Path("config.ini")
    if not config_file.exists():
        print(f"[WARN] Config file not found: {config_file}")
        print("       Will use default config")
    else:
        print(f"[OK] Config file exists: {config_file}")

    config = load_config("config.ini")

    if config:
        print("[OK] Config loaded successfully")
        print_config(config)
    else:
        print("[FAIL] Config loading failed")


def test_load_nonexistent_file():
    """Test loading nonexistent config file"""
    print_section("Test 3: Load Nonexistent File")
    print("Testing if load_config('nonexistent.ini') gracefully degrades...")

    config = load_config("nonexistent.ini")

    if config == DEFAULT_CONFIG:
        print("[OK] Correctly returned default config (graceful degradation)")
    else:
        print("[FAIL] Should have returned default config")


def test_config_types():
    """Test config types"""
    print_section("Test 4: Config Type Check")
    print("Checking if config data types are correct...")

    config = load_config("config.ini")

    # Check types
    checks = [
        ("room_id", str, type(config.room.room_id)),
        ("auto_reconnect", bool, type(config.room.auto_reconnect)),
        ("heartbeat_interval", int, type(config.room.heartbeat_interval)),
        ("voice", str, type(config.tts.voice)),
        ("cache_enabled", bool, type(config.tts.cache_enabled)),
        ("min_length", int, type(config.filter.min_length)),
        ("max_queue_size", int, type(config.playback.max_queue_size)),
        ("volume", float, type(config.playback.volume)),
        ("level", str, type(config.log.level)),
        ("enable_console", bool, type(config.log.enable_console)),
    ]

    all_passed = True
    for name, expected, actual in checks:
        if expected == actual:
            print(f"[OK] {name}: {actual.__name__}")
        else:
            print(f"[FAIL] {name}: expected {expected.__name__}, got {actual.__name__}")
            all_passed = False

    return all_passed


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("  Configuration Module Test")
    print("=" * 60)

    # Run tests
    test_default_config()
    test_load_config_from_file()
    test_load_nonexistent_file()
    all_passed = test_config_types()

    # Summary
    print_section("Test Summary")
    if all_passed:
        print("[OK] All tests passed! Config module works correctly")
    else:
        print("[FAIL] Some tests failed, please check config")

    print("\nTest completed\n")


if __name__ == "__main__":
    main()
