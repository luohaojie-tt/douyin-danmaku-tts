#!/usr/bin/env python3
"""
Pygame播放器测试脚本

测试音频播放功能是否正常工作。
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.player.pygame_player import PygamePlayer, play_audio_file


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_initialization():
    """测试播放器初始化"""
    print_section("Test 1: Player Initialization")

    try:
        player = PygamePlayer(volume=0.7)

        print(f"[OK] 播放器初始化成功")
        print(f"  音量: {player.get_volume()}")
        print(f"  是否播放中: {player.is_playing()}")
        return True

    except Exception as e:
        print(f"[FAIL] 初始化失败: {e}")
        return False


def test_play_audio_file():
    """测试播放音频文件"""
    print_section("Test 2: Play Audio File")

    # 检查是否有测试音频文件
    test_audio = Path("cache/test_output.mp3")

    if not test_audio.exists():
        print(f"[WARN] 测试音频不存在: {test_audio}")
        print(f"  提示: 先运行 test_edge_tts.py 生成测试音频")
        return None  # 跳过测试

    try:
        player = PygamePlayer(volume=0.8)

        print(f"测试音频: {test_audio.name}")
        print(f"开始播放...")

        # 非阻塞播放
        success = player.play(test_audio, blocking=False)

        if success:
            print(f"[OK] 开始播放成功")

            # 等待一小段时间确认播放中
            import time
            time.sleep(0.5)

            if player.is_playing():
                print(f"[OK] 确认正在播放")
            else:
                # 音频可能很短，已经播放完成
                print(f"[OK] 播放完成或很短暂")

            # 停止播放
            player.stop()
            print(f"[OK] 停止播放成功")
            return True
        else:
            print(f"[FAIL] 播放失败")
            return False

    except Exception as e:
        print(f"[FAIL] 播放异常: {e}")
        return False


def test_blocking_play():
    """测试阻塞播放"""
    print_section("Test 3: Blocking Play")

    # 检查测试音频
    test_audio = Path("cache/test_output.mp3")

    if not test_audio.exists():
        print(f"[WARN] 测试音频不存在: {test_audio}")
        print(f"  提示: 先运行 test_edge_tts.py 生成测试音频")
        return None

    try:
        player = PygamePlayer(volume=0.6)

        print(f"测试音频: {test_audio.name}")
        print(f"阻塞播放（会等待播放完成）...")

        import time
        start_time = time.time()

        success = player.play(test_audio, blocking=True)

        duration = time.time() - start_time

        if success:
            print(f"[OK] 阻塞播放成功")
            print(f"  播放耗时: {duration:.2f} 秒")
            return True
        else:
            print(f"[FAIL] 阻塞播放失败")
            return False

    except Exception as e:
        print(f"[FAIL] 阻塞播放异常: {e}")
        return False


def test_volume_control():
    """测试音量控制"""
    print_section("Test 4: Volume Control")

    try:
        player = PygamePlayer(volume=0.5)

        print(f"初始音量: {player.get_volume()}")

        # 测试不同的音量值
        test_volumes = [0.0, 0.3, 0.5, 0.7, 1.0]

        for vol in test_volumes:
            player.set_volume(vol)
            actual = player.get_volume()

            if abs(actual - vol) < 0.01:
                print(f"[OK] 设置音量 {vol} -> {actual}")
            else:
                print(f"[FAIL] 设置音量 {vol} -> {actual} (不匹配)")
                return False

        # 测试超出范围的值
        print("\n测试边界值:")
        player.set_volume(1.5)
        if player.get_volume() == 1.0:
            print(f"[OK] 音量 1.5 被限制为 1.0")
        else:
            print(f"[FAIL] 音量限制失败")
            return False

        player.set_volume(-0.5)
        if player.get_volume() == 0.0:
            print(f"[OK] 音量 -0.5 被限制为 0.0")
        else:
            print(f"[FAIL] 音量限制失败")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] 音量控制异常: {e}")
        return False


def test_stop():
    """测试停止播放"""
    print_section("Test 5: Stop Playback")

    test_audio = Path("cache/test_output.mp3")

    if not test_audio.exists():
        print(f"[WARN] 测试音频不存在: {test_audio}")
        return None

    try:
        player = PygamePlayer(volume=0.7)

        # 开始播放
        print(f"开始播放...")
        player.play(test_audio, blocking=False)

        import time
        time.sleep(0.5)  # 播放一小段时间

        if player.is_playing():
            print(f"[OK] 确认正在播放")
        else:
            print(f"[WARN] 音频可能太短已播放完成")
            return True

        # 停止播放
        print(f"停止播放...")
        player.stop()

        time.sleep(0.1)

        if not player.is_playing():
            print(f"[OK] 停止成功")
            return True
        else:
            print(f"[FAIL] 停止后仍在播放")
            return False

    except Exception as e:
        print(f"[FAIL] 停止播放异常: {e}")
        return False


def test_multiple_plays():
    """测试连续播放"""
    print_section("Test 6: Multiple Plays")

    # 查找所有测试音频
    cache_dir = Path("cache")
    audio_files = list(cache_dir.glob("*.mp3"))

    if len(audio_files) < 2:
        print(f"[WARN] 测试音频不足，至少需要2个音频文件")
        print(f"  当前: {len(audio_files)} 个")
        return None

    try:
        player = PygamePlayer(volume=0.7)

        print(f"找到 {len(audio_files)} 个音频文件")

        # 播放前3个音频
        count = min(3, len(audio_files))
        for i in range(count):
            audio = audio_files[i]
            print(f"\n播放 {i+1}/{count}: {audio.name}")

            success = player.play(audio, blocking=True)

            if success:
                print(f"[OK] 播放成功")
            else:
                print(f"[FAIL] 播放失败")
                return False

        print(f"\n[OK] 连续播放测试完成")
        return True

    except Exception as e:
        print(f"[FAIL] 连续播放异常: {e}")
        return False


def test_statistics():
    """测试统计信息"""
    print_section("Test 7: Statistics")

    try:
        player = PygamePlayer(volume=0.7)

        # 获取初始统计
        stats = player.get_stats()
        print(f"初始统计:")
        print(f"  播放次数: {stats['total_played']}")
        print(f"  音量: {stats['volume']}")
        print(f"  播放中: {stats['is_playing']}")

        # 如果有测试音频，播放几次
        test_audio = Path("cache/test_output.mp3")
        if test_audio.exists():
            print(f"\n播放测试音频...")
            player.play(test_audio, blocking=True)
            player.play(test_audio, blocking=True)

            # 获取更新后的统计
            stats = player.get_stats()
            print(f"\n更新后统计:")
            print(f"  播放次数: {stats['total_played']}")
            print(f"  音量: {stats['volume']}")
            print(f"  播放中: {stats['is_playing']}")

            if stats['total_played'] >= 2:
                print(f"[OK] 统计信息正确")
                return True
            else:
                print(f"[FAIL] 统计信息不正确")
                return False
        else:
            print(f"[WARN] 测试音频不存在，跳过播放测试")
            return True

    except Exception as e:
        print(f"[FAIL] 统计信息异常: {e}")
        return False


def test_cleanup():
    """测试资源清理"""
    print_section("Test 8: Cleanup")

    try:
        player = PygamePlayer(volume=0.7)

        print(f"清理前初始化状态: {player._initialized}")

        # 清理
        player.cleanup()

        print(f"清理后初始化状态: {player._initialized}")

        if not player._initialized:
            print(f"[OK] 清理成功")
            return True
        else:
            print(f"[FAIL] 清理后仍显示已初始化")
            return False

    except Exception as e:
        print(f"[FAIL] 清理异常: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Pygame Player Test")
    print("=" * 60)

    # 运行测试
    results = []
    results.append(test_initialization())
    results.append(test_play_audio_file())
    results.append(test_blocking_play())
    results.append(test_volume_control())
    results.append(test_stop())
    results.append(test_multiple_plays())
    results.append(test_statistics())
    results.append(test_cleanup())

    # 汇总
    print_section("Test Summary")

    # 过滤掉 None（跳过的测试）
    valid_results = [r for r in results if r is not None]

    passed = sum(1 for r in valid_results if r)
    total = len(valid_results)
    skipped = len(results) - len(valid_results)

    print(f"Passed: {passed}/{total}")
    if skipped > 0:
        print(f"Skipped: {skipped}")

    if passed == total:
        print("\n[OK] All tests passed! Pygame player works correctly")
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")

    print("\nTest completed\n")


if __name__ == "__main__":
    main()
