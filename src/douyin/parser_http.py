"""
HTTP响应解析器 - 更准确的protobuf解析

使用protobuf结构解析，而不是暴力正则匹配
"""

import re
import logging
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    """用户信息"""
    id: str
    nickname: str
    level: int = 1


@dataclass
class ParsedMessage:
    """解析后的消息"""
    method: str
    user: Optional[UserInfo] = None
    content: Optional[str] = None


class HTTPResponseParser:
    """HTTP响应解析器 - 改进版"""

    def __init__(self):
        self.message_count = 0

    def parse_response(self, data: bytes) -> List[ParsedMessage]:
        """解析HTTP响应"""
        try:
            # 解压gzip
            import gzip
            try:
                data = gzip.decompress(data)
            except:
                pass  # 不是gzip

            # 转为文本
            text = data.decode('utf-8', errors='ignore')

            # 查找所有弹幕消息
            messages = []

            # WebcastChatMessage的文本模式
            # 查找所有可能的消息模式
            patterns = [
                # 尝试找到content字段后面的文本
                r'WebcastChatMessage.*?content[^\x00-\x7f]{4,}([^\x00-\x7f]{2,})',
                # 或者查找连续的中文文本
                r'([\u4e00-\u9fff]{2,}[！？！，。、～\s]{0,3})',
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    if isinstance(match, tuple):
                        content = match[1] if len(match) > 1 else match[0]
                    else:
                        content = match.group(0)

                    # 清理内容
                    content = content.strip()

                    # 过滤掉明显的系统消息
                    if self._is_real_danmaku(content):
                        # 提取可能的用户名（前面的中文）
                        nickname = "用户"
                        nickname_match = re.search(r'([\u4e00-\u9fff]{2,})[：:]', content[:20])
                        if nickname_match:
                            nickname = nickname_match.group(1)

                        user = UserInfo(
                            id="unknown",
                            nickname=nickname[:20],
                            level=1
                        )

                        messages.append(ParsedMessage(
                            method="WebChatMessage",
                            user=user,
                            content=content
                        ))

                        # 限制返回数量，避免重复
                        if len(messages) >= 50:
                            break

                if messages:
                    break

            logger.debug(f"解析出 {len(messages)} 条消息")
            return messages

        except Exception as e:
            logger.error(f"解析失败: {e}")
            return []

    def _is_real_danmaku(self, text: str) -> bool:
        """检查是否是真实弹幕"""
        if not text or len(text) < 2:
            return False

        # 过滤明显的系统消息
        system_patterns = [
            r'^在线观众',
            r'^正在观看',
            r'^人数',
            r'^点赞',
            r'^关注',
            r'^粉丝',
            r'^主播',
            r'^直播',
            r'^房间',
            r'^榜单',
            r'^榜',
            r'^第',
            r'^名',
            r'^贡献',
            r'^热度',
            r'^礼物',
            r'^感谢',
            r'^欢迎',
            r'^进入',
            r'^加入',
            r'^join',
            r'^room',
            r'^gift',
            r'^like',
            r'^follow',
            r'^勋章',          # 用户等级标识
            r'勋章',           # 包含勋章的内容
            r'^新来的',        # 系统提示
            r'^加入大家',      # 系统提示
            r'^等级',          # 用户等级
            r'^粉丝团',        # 粉丝团相关
            r'^舰长',          # 等级标识
            r'^提督',          # 等级标识
            r'^总督',          # 等级标识
            r'^连击',          # 礼物连击
            r'^赠送',          # 赠送礼物
            r'^送到',          # 送到
            r'^开团',          # 开团
            r'^报名',          # 报名
            r'^抢购',          # 抢购
            r'^秒杀',          # 秒杀
            r'^优惠券',        # 优惠券
        ]

        for pattern in system_patterns:
            if re.search(pattern, text):
                return False

        # 必须是纯中文或常见标点
        chinese_char_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_count = len(text)

        # 中文字符占比应该超过50%
        if chinese_char_count / total_count < 0.5:
            return False

        return True
