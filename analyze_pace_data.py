"""
分析保存的pace_data_full.json文件
"""
import json
import re

# 读取保存的数据
with open('pace_data_full.json', 'r', encoding='utf-8') as f:
    pace_data = json.load(f)

print(f"总共有 {len(pace_data)} 个元素\n")

# 检查元素24
if len(pace_data) > 24:
    item = pace_data[24]
    print(f"元素24:")
    print(f"  类型: {type(item)}")
    print(f"  长度: {len(item) if isinstance(item, list) else 'N/A'}")

    if isinstance(item, list) and len(item) >= 2:
        print(f"  [0] 类型: {type(item[0])}")
        print(f"  [0] 值: {item[0]}")

        print(f"  [1] 类型: {type(item[1])}")
        if isinstance(item[1], str):
            content = item[1]
            print(f"  [1] 长度: {len(content)}")
            print(f"  [1] 前200字符: {content[:200]}")
            print(f"  [1] 后200字符: {content[-200:]}")

            # 测试正则表达式
            print(f"\n正则表达式测试:")

            room_match = re.search(r'"roomId":"([0-9]+)"', content)
            print(f"  \"roomId\":\"([0-9]+)\" -> {room_match}")

            if not room_match:
                # 尝试其他模式
                room_match2 = re.search(r'roomId[^\"]*"([^"]+)"', content)
                print(f"  roomId[^\"]*\"([^\"]+)\" -> {room_match2}")

                # 搜索所有包含roomId的行
                all_matches = re.findall(r'roomId["\s:]+([0-9]+)', content)
                print(f"  所有roomId匹配: {all_matches[:5]}")

            unique_match = re.search(r'"user_unique_id":"([0-9]+)"', content)
            print(f"  \"user_unique_id\":\"([0-9]+)\" -> {unique_match}")

            if not unique_match:
                unique_match2 = re.search(r'user_unique_id[^\"]*"([^"]+)"', content)
                print(f"  user_unique_id[^\"]*\"([^\"]+)\" -> {unique_match2}")
