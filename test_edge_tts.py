#!/usr/bin/env python3
"""
Edge-TTS 引擎测试脚本

测试文字转语音功能是否正常工作。
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.tts.edge_tts import EdgeTTSEngine


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


async def test_print_voices():
    """测试打印可用音色"""
    print_section("Test 1: Print Available Voices")

    EdgeTTSEngine.print_voices()

    print("[OK] 音色列表打印成功")
    return True


async def test_convert_text():
    """测试文本转音频数据"""
    print_section("Test 2: Convert Text to Audio Data")

    engine = EdgeTTSEngine()

    test_text = "主播好厉害！"
    print(f"测试文本: {test_text}")

    audio_data = await engine.convert(test_text)

    if audio_data and len(audio_data) > 0:
        print(f"[OK] 转换成功")
        print(f"  音频数据大小: {len(audio_data)} 字节")
        print(f"  格式: MP3")
        return True
    else:
        print("[FAIL] 转换失败")
        return False


async def test_convert_to_file():
    """测试转换并保存到文件"""
    print_section("Test 3: Convert Text to File")

    engine = EdgeTTSEngine()

    test_text = "这是测试语音播报，感谢大家支持！"
    output_path = Path("cache/test_output.mp3")

    print(f"测试文本: {test_text}")
    print(f"输出路径: {output_path}")

    success = await engine.convert_to_file(test_text, output_path)

    if success and output_path.exists():
        file_size = output_path.stat().st_size
        print(f"[OK] 文件保存成功")
        print(f"  文件大小: {file_size} 字节")
        print(f"  文件路径: {output_path.absolute()}")
        return True
    else:
        print("[FAIL] 文件保存失败")
        return False


async def test_convert_with_cache():
    """测试带缓存的转换"""
    print_section("Test 4: Convert with Cache")

    engine = EdgeTTSEngine()
    cache_dir = Path("cache")

    test_text = "测试缓存功能"
    print(f"测试文本: {test_text}")
    print(f"缓存目录: {cache_dir}")

    # 第一次转换（应该生成新文件）
    print("\n第一次转换...")
    result1 = await engine.convert_with_cache(test_text, cache_dir)

    if not result1:
        print("[FAIL] 第一次转换失败")
        return False

    print(f"[OK] 第一次转换成功: {result1.name}")

    # 第二次转换（应该命中缓存）
    print("\n第二次转换（应该命中缓存）...")
    result2 = await engine.convert_with_cache(test_text, cache_dir)

    if result2 and result1 == result2:
        print(f"[OK] 缓存命中成功")
        print(f"  使用相同文件: {result2.name}")
        return True
    else:
        print("[FAIL] 缓存未命中")
        return False


async def test_different_voices():
    """测试不同音色"""
    print_section("Test 5: Test Different Voices")

    voices_to_test = [
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural",
    ]

    all_passed = True
    for voice in voices_to_test:
        print(f"\n测试音色: {voice}")
        engine = EdgeTTSEngine(voice=voice)

        test_text = "测试不同音色效果"
        audio_data = await engine.convert(test_text)

        if audio_data and len(audio_data) > 0:
            voice_name = EdgeTTSEngine.AVAILABLE_VOICES.get(voice, voice)
            print(f"[OK] {voice_name} 转换成功")
        else:
            print(f"[FAIL] {voice} 转换失败")
            all_passed = False

    return all_passed


async def test_rate_and_volume():
    """测试语速和音量调整"""
    print_section("Test 6: Test Rate and Volume")

    test_cases = [
        {"rate": "+20%", "volume": "+10%"},
        {"rate": "-20%", "volume": "-10%"},
        {"rate": "+50%", "volume": "+50%"},
    ]

    all_passed = True
    for params in test_cases:
        print(f"\n测试参数: rate={params['rate']}, volume={params['volume']}")

        engine = EdgeTTSEngine(
            rate=params["rate"],
            volume=params["volume"]
        )

        test_text = "测试语速和音量调整"
        audio_data = await engine.convert(test_text)

        if audio_data and len(audio_data) > 0:
            print(f"[OK] 参数 {params} 转换成功")
        else:
            print(f"[FAIL] 参数 {params} 转换失败")
            all_passed = False

    return all_passed


async def test_empty_text():
    """测试空文本处理"""
    print_section("Test 7: Test Empty Text Handling")

    engine = EdgeTTSEngine()

    test_cases = [
        "",
        "   ",
        None,
    ]

    all_passed = True
    for text in test_cases:
        print(f"\n测试文本: {repr(text)}")
        result = await engine.convert(text)

        if result is None:
            print("[OK] 空文本正确返回 None")
        else:
            print("[FAIL] 空文本应该返回 None")
            all_passed = False

    return all_passed


async def test_long_text():
    """测试长文本处理"""
    print_section("Test 8: Test Long Text")

    engine = EdgeTTSEngine()

    # 构造较长的测试文本
    long_text = "这是一段很长的测试文本。" * 10

    print(f"文本长度: {len(long_text)} 字符")
    print(f"文本内容: {long_text[:50]}...")

    output_path = Path("cache/test_long_text.mp3")
    success = await engine.convert_to_file(long_text, output_path)

    if success and output_path.exists():
        file_size = output_path.stat().st_size
        print(f"[OK] 长文本转换成功")
        print(f"  文件大小: {file_size} 字节")
        return True
    else:
        print("[FAIL] 长文本转换失败")
        return False


async def test_stats():
    """测试统计信息"""
    print_section("Test 9: Test Statistics")

    engine = EdgeTTSEngine()

    # 执行几次转换
    texts = ["测试1", "测试2", "测试3"]
    for text in texts:
        await engine.convert(text)

    # 获取统计信息
    stats = engine.get_stats()

    print(f"统计信息:")
    print(f"  总转换次数: {stats['total_conversions']}")
    print(f"  总字符数: {stats['total_chars']}")
    print(f"  当前音色: {stats['voice']}")
    print(f"  当前语速: {stats['rate']}")
    print(f"  当前音量: {stats['volume']}")

    if stats['total_conversions'] == len(texts):
        print("[OK] 统计信息正确")
        return True
    else:
        print("[FAIL] 统计信息不正确")
        return False


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Edge-TTS Engine Test")
    print("=" * 60)

    # 确保缓存目录存在
    Path("cache").mkdir(exist_ok=True)

    # 运行测试
    results = []
    results.append(await test_print_voices())
    results.append(await test_convert_text())
    results.append(await test_convert_to_file())
    results.append(await test_convert_with_cache())
    results.append(await test_different_voices())
    results.append(await test_rate_and_volume())
    results.append(await test_empty_text())
    results.append(await test_long_text())
    results.append(await test_stats())

    # 汇总
    print_section("Test Summary")

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Edge-TTS engine works correctly")
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")

    print("\nTest completed\n")


if __name__ == "__main__":
    asyncio.run(main())
