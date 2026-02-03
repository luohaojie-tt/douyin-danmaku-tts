"""
改进的弹幕解析器 - 基于真实消息样例分析

真实弹幕消息结构（从danmaku_candidates.txt分析）：
- 消息类型: WebcastChatMessage
- 用户昵称: 重复出现多次，可能包含*号（如"苏***"、"岁***"）
- 弹幕内容: 用户昵称后的短文本（如"芭比Q"、"[赞][赞][赞]"）
- 用户ID: MS4wLj...开头长字符串
"""

import gzip
import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str = ""
    nickname: str = "匿名用户"


@dataclass
class ParsedMessage:
    """解析后的消息"""
    method: str = "Unknown"
    user: Optional[UserInfo] = None
    content: Optional[str] = None
    raw_data: Optional[bytes] = None
    raw_strings: Optional[List[dict]] = None


class ImprovedMessageParser:
    """
    改进的消息解析器

    基于真实消息样例优化的解析逻辑
    """

    def __init__(self):
        self.message_count = 0
        self.danmaku_count = 0

    def parse_message(self, raw_data: bytes) -> Optional[ParsedMessage]:
        """
        解析二进制消息

        Args:
            raw_data: 原始二进制数据

        Returns:
            ParsedMessage: 解析后的消息
        """
        try:
            self.message_count += 1

            # 提取字段8（gzip压缩的protobuf数据）
            decompressed = self._extract_field_8(raw_data)

            if not decompressed:
                return None

            # 提取所有字符串
            strings = self._extract_all_strings(decompressed)

            if not strings:
                return None

            # 分析消息类型
            message_type = self._detect_message_type(strings)

            logger.debug(f"[Parser] 消息类型: {message_type}, 提取到 {len(strings)} 个字符串")

            # 如果是聊天消息，提取弹幕
            if message_type == "WebChatMessage":
                danmaku = self._extract_danmaku_improved(strings)
                if danmaku:
                    self.danmaku_count += 1
                    danmaku.raw_strings = strings
                    logger.info(f"[Parser] *** 提取到弹幕: [{danmaku.user.nickname}] {danmaku.content[:30]} ***")
                    return danmaku

            # 对于其他消息类型，也返回（用于调试）
            result = ParsedMessage(
                method=message_type,
                raw_data=raw_data,
                raw_strings=strings if strings else None
            )

            return result

        except Exception as e:
            logger.debug(f"解析消息失败: {e}")
            return None

    def _extract_field_8(self, raw_data: bytes) -> Optional[bytes]:
        """提取字段8并解压"""
        pos = 0

        while pos < len(raw_data):
            try:
                # 读取tag
                tag, pos = self._read_varint(raw_data, pos)

                if pos >= len(raw_data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                # 查找字段8
                if field_number == 8 and wire_type == 2:
                    # 读取长度
                    length, pos = self._read_varint(raw_data, pos)

                    if pos + length <= len(raw_data):
                        field_8_data = raw_data[pos:pos + length]

                        # 尝试解压
                        try:
                            return gzip.decompress(field_8_data)
                        except:
                            # 解压失败，返回原始数据
                            return field_8_data

                # 跳过这个字段
                if wire_type == 0:  # varint
                    _, pos = self._read_varint(raw_data, pos)
                elif wire_type == 2:  # length-delimited
                    length, pos = self._read_varint(raw_data, pos)
                    pos += length
                else:
                    pos += 1

            except:
                break

        return None

    def _extract_all_strings(self, data: bytes) -> List[dict]:
        """
        提取所有字符串

        Returns:
            List[dict]: 字符串列表，每项包含field和text
        """
        strings = []
        pos = 0

        while pos < len(data):
            try:
                # 读取tag
                tag, pos = self._read_varint(data, pos)

                if pos >= len(data):
                    break

                field_number = tag >> 3
                wire_type = tag & 0x07

                if wire_type == 2:  # length-delimited
                    length, pos = self._read_varint(data, pos)

                    if pos + length > len(data):
                        break

                    value = data[pos:pos + length]
                    pos += length

                    # 尝试解析为字符串
                    try:
                        text = value.decode('utf-8', errors='ignore')

                        # 只保留合理的字符串（放宽长度限制）
                        if 1 <= len(text) <= 500:
                            # 检查是否包含可打印字符
                            printable_count = sum(1 for c in text if c.isprintable())
                            if printable_count > len(text) * 0.2:  # 降低阈值
                                strings.append({
                                    'field': field_number,
                                    'text': text
                                })
                    except:
                        pass

                elif wire_type == 0:  # varint
                    _, pos = self._read_varint(data, pos)
                else:
                    pos += 1

            except:
                break

        return strings

    def _detect_message_type(self, strings: List[dict]) -> str:
        """
        检测消息类型

        修复：正确识别 WebcastChatMessage
        """
        for s in strings:
            text = s['text']

            # 修复：WebcastChatMessage 应该映射为 WebChatMessage
            if 'WebcastChatMessage' in text:
                return "WebChatMessage"
            elif 'WebcastRoomCommentTopicMessage' in text:
                return "WebChatMessage"  # 话题讨论消息
            elif 'WebcastGiftMessage' in text:
                return "WebGiftMessage"
            elif 'WebcastRoomStatsMessage' in text:
                return "WebcastRoomStatsMessage"
            elif 'WebcastRoomUserSeqMessage' in text:
                return "WebcastRoomUserSeqMessage"
            elif 'WebcastLikeMessage' in text:
                return "WebcastLikeMessage"
            elif 'MemberMessage' in text:
                return "MemberMessage"
            elif 'ControlMessage' in text:
                return "ControlMessage"
            elif 'WebcastRoomRankMessage' in text:
                return "WebcastRoomRankMessage"
            elif 'WebcastSocialMessage' in text:
                return "WebcastSocialMessage"
            elif 'WebcastInRoomBannerMessage' in text:
                return "WebcastInRoomBannerMessage"
            elif 'WebcastRoomStreamAdaptationMessage' in text:
                return "WebcastRoomStreamAdaptationMessage"
            elif 'WebcastRanklistHourEntranceMessage' in text:
                return "WebcastRanklistHourEntranceMessage"

        return "Unknown"

    def _extract_danmaku_improved(self, strings: List[dict]) -> Optional[ParsedMessage]:
        """
        改进的弹幕提取逻辑

        基于真实样例分析：
        1. 用户昵称特征：
           - 长度2-6字符
           - 可能包含***（如"苏***"、"岁***"）
           - 重复出现多次
           - 通常以中文字符开头

        2. 弹幕内容特征：
           - 在用户昵称之后出现
           - 长度1-50字符
           - 不是URL、不是路径
           - 可能包含表情符号如[赞]
        """
        # 统计字符串出现次数
        string_counts = {}
        for s in strings:
            text = s['text']
            string_counts[text] = string_counts.get(text, 0) + 1

        # 找出重复出现2次以上的字符串（这些可能是用户昵称）
        repeat_candidates = [text for text, count in string_counts.items()
                            if count >= 2 and 2 <= len(text) <= 6]

        user = UserInfo()
        content = None

        # 过滤掉系统消息
        filtered_strings = []
        for s in strings:
            text = s['text']
            if not self._is_system_message(text):
                filtered_strings.append(text)

        # 第一步：查找用户昵称
        for text in filtered_strings:
            # 用户昵称特征：2-6字符，可能包含***
            if 2 <= len(text) <= 6:
                # 包含中文或以中文开头
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
                if has_chinese:
                    # 检查是否在重复候选列表中
                    if text in repeat_candidates:
                        user.nickname = text
                        # 提取用户ID（在昵称附近的MS4wLj开头的长字符串）
                        user.id = self._find_user_id(filtered_strings, text)
                        break

        # 第二步：查找弹幕内容
        # 弹幕内容通常是：
        # 1. 长度1-50的短文本
        # 2. 不包含URL/路径
        # 3. 不是系统消息
        # 4. 不是重复的昵称
        # 5. 可能包含[表情]格式

        for text in filtered_strings:
            # 跳过用户昵称
            if text == user.nickname or text in repeat_candidates:
                continue

            # 检查是否是有效弹幕
            if self._is_valid_danmaku(text):
                content = text
                break

        if content:
            return ParsedMessage(
                method="WebChatMessage",
                user=user if user.nickname else None,
                content=content
            )

        return None

    def _find_user_id(self, strings: List[str], nickname: str) -> str:
        """查找用户昵称对应的用户ID"""
        # 找到昵称的位置，查找附近的MS4wLj开头的字符串
        for i, text in enumerate(strings):
            if text == nickname:
                # 查看前后5个字符串
                start = max(0, i - 5)
                end = min(len(strings), i + 6)
                for j in range(start, end):
                    if j != i and strings[j].startswith('MS4wLj'):
                        return strings[j]

        return ""

    def _is_system_message(self, text: str) -> bool:
        """检查是否是系统消息"""
        system_keywords = [
            'http', 'https', '.png', '.jpg', '.image', '.webp',
            'webcast', 'douyinpic', 'douyinstatic',
            '荣誉等级', '勋章', '粉丝团', '在线观众', '等级勋章',
            '小时榜', '人气榜', '任务', '礼物', '直播间',
            'sslocal://', 'webcast_redirect',
            'internal_src', 'first_req_ms', 'wss_push',
            'compress_type', 'im-cursor', 'webcast_im',
            'webcast/preview', 'webcast/small_', 'webcast/fansclub',
            'webcast/new_user_grade', 'webcast/aweme_pay_grade',
            'userlabel', 'DefAvatar', 'mosaic-legacy',
            'WebcastChatMessage', 'WebcastRoom', 'WebcastRank',
            'WebcastSocial', 'WebcastLike', 'WebcastGift',
            'WebcastMember', 'WebcastControl', 'WebcastStats',
            'BannerMessage', 'EntranceMessage', 'Adaptation',
            '小时榜', '人气榜', '大家在说', '人在聊',
            '观众充能', '能量', '点亮礼物', '多阶段任务',
            'banner_detail', 'role2views', 'schema_url',
            'tieba', 'weibo', 'qq', 'wechat',
            'v_', 'banners', 'component', 'task_props',
            'condition_text', 'award_icon', 'pro_conf',
            'growth_', 'anchor_', 'audience', 'gift_task',
            'quota_task', 'task_items', 'phase_name',
            'webcast_profile', 'user_id', 'click_user_position',
        ]

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in system_keywords)

    def _is_valid_danmaku(self, text: str) -> bool:
        """检查是否是有效的弹幕内容"""
        # 长度限制：1-50字符
        if not (1 <= len(text) <= 50):
            return False

        # 过滤掉系统消息
        if self._is_system_message(text):
            return False

        # 过滤掉颜色代码（#开头，6位十六进制）
        if text.startswith('#') and len(text) in [7, 9]:  # #RRGGBB 或 #RRGGBBAA
            return False

        # 必须包含中文或合理的字符
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
        has_bracket = '[' in text and ']' in text  # [表情]格式
        has_alpha = any(c.isalpha() for c in text)

        if not (has_chinese or has_bracket or has_alpha):
            return False

        # 过滤掉URL和路径
        if any(s in text for s in ['http', 'https', '/', '.png', '.jpg', 'sslocal://']):
            return False

        # 过滤掉纯数字
        if text.isdigit():
            return False

        # 过滤掉过长的字母数字混合（可能是ID）
        if len(text) > 15:
            alpha_num = sum(1 for c in text if c.isalnum())
            if alpha_num / len(text) > 0.8:
                return False

        # 过滤掉只有标点符号的
        if all(not c.isalnum() and c not in '[【{（' for c in text):
            return False

        # 允许[表情]格式
        # 允许特殊字符如！？～等
        # 允许中文、英文、数字混合

        return True

    def _read_varint(self, data: bytes, pos: int) -> tuple:
        """
        读取varint编码的整数

        Returns:
            tuple: (value, new_pos)
        """
        result = 0
        shift = 0

        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift

            if not (byte & 0x80):
                break

            shift += 7

        return result, pos
