"""
抖音Cookie管理器

负责加载、验证和管理抖音直播间所需的ttwid cookie。
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CookieManager:
    """
    抖音Cookie管理器

    负责从文件或字符串加载ttwid cookie，并验证其格式。
    """

    # ttwid最小长度（抖音的ttwid通常是100-200字符）
    MIN_TTWID_LENGTH = 50

    # ttwid允许的字符模式（字母、数字、下划线、连字符、百分号）
    TTWID_PATTERN = re.compile(r'^[\w\-%]+$')

    def __init__(self, config_path: str = "cookies.txt"):
        """
        初始化Cookie管理器

        Args:
            config_path: Cookie文件路径（默认: cookies.txt）
        """
        self.config_path = Path(config_path)

    def load_from_file(self, path: Optional[str] = None) -> Optional[str]:
        """
        从文件加载ttwid

        Args:
            path: Cookie文件路径（如果为None，使用初始化时指定的路径）

        Returns:
            str | None: ttwid字符串，如果加载失败返回None
        """
        cookie_file = Path(path) if path else self.config_path

        # 1. 检查文件是否存在
        if not cookie_file.exists():
            logger.error(f"Cookie文件不存在: {cookie_file}")
            self._print_usage_guide()
            return None

        # 2. 读取文件内容
        try:
            content = cookie_file.read_text(encoding='utf-8').strip()
        except Exception as e:
            logger.error(f"读取Cookie文件失败: {e}")
            return None

        # 3. 解析ttwid
        ttwid = self._parse_ttwid(content)

        if not ttwid:
            logger.error(f"未在 {cookie_file} 中找到 ttwid")
            self._print_usage_guide()
            return None

        # 4. 验证ttwid格式
        if not self.validate_ttwid(ttwid):
            logger.warning("ttwid 格式可能不正确")
            logger.warning(f"当前长度: {len(ttwid)}, 期望长度: {self.MIN_TTWID_LENGTH}+")
            logger.warning("程序可能无法正常连接直播间")

        return ttwid

    def load_from_string(self, ttwid: str) -> Optional[str]:
        """
        从字符串加载ttwid

        Args:
            ttwid: ttwid字符串

        Returns:
            str | None: 验证后的ttwid，如果验证失败返回None
        """
        if not ttwid:
            logger.error("ttwid 字符串为空")
            return None

        if not self.validate_ttwid(ttwid):
            logger.error("ttwid 格式验证失败")
            return None

        logger.info(f"ttwid 加载成功 (长度: {len(ttwid)})")
        return ttwid

    def validate_ttwid(self, ttwid: str) -> bool:
        """
        验证 ttwid 格式是否正确

        Args:
            ttwid: ttwid字符串

        Returns:
            bool: True表示格式正确，False表示格式错误
        """
        # 1. 检查是否为空
        if not ttwid:
            logger.error("ttwid 为空")
            return False

        # 2. 检查长度（ttwid通常是长字符串）
        if len(ttwid) < self.MIN_TTWID_LENGTH:
            logger.warning(f"ttwid 长度过短: {len(ttwid)} < {self.MIN_TTWID_LENGTH}")
            return False

        # 3. 检查是否包含有效字符（字母、数字、常见特殊字符）
        if not self.TTWID_PATTERN.match(ttwid):
            logger.warning(f"ttwid 包含非法字符")
            logger.warning(f"允许的字符: 字母、数字、下划线、连字符、百分号")
            return False

        logger.debug(f"ttwid 验证通过 (长度: {len(ttwid)})")
        return True

    def _parse_ttwid(self, content: str) -> Optional[str]:
        """
        从文件内容中解析ttwid

        支持的格式：
        - ttwid=xxx
        - ttwid = xxx
        - # ttwid=xxx (注释行)

        Args:
            content: 文件内容

        Returns:
            str | None: 解析出的ttwid，如果未找到返回None
        """
        ttwid = None

        for line in content.split('\n'):
            line = line.strip()

            # 跳过注释行
            if line.startswith('#'):
                continue

            # 跳过空行
            if not line:
                continue

            # 解析 "ttwid=xxx" 或 "ttwid = xxx"
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key == 'ttwid':
                    ttwid = value
                    break

        return ttwid

    def _print_usage_guide(self):
        """打印Cookie获取指南"""
        logger.info("=" * 60)
        logger.info("请按以下步骤获取 ttwid:")
        logger.info("=" * 60)
        logger.info("1. 打开浏览器访问 https://live.douyin.com")
        logger.info("2. 按 F12 打开开发者工具")
        logger.info("3. 切换到 Application / 存储 标签")
        logger.info("4. 在左侧找到 Cookies → https://live.douyin.com")
        logger.info("5. 找到名为 ttwid 的 Cookie")
        logger.info("6. 复制 ttwid 的值")
        logger.info("7. 粘贴到 cookies.txt 文件中（格式: ttwid=你的值）")
        logger.info("=" * 60)

    def save_to_file(self, ttwid: str, path: Optional[str] = None) -> bool:
        """
        保存ttwid到文件

        Args:
            ttwid: ttwid字符串
            path: 保存路径（如果为None，使用初始化时指定的路径）

        Returns:
            bool: 保存是否成功
        """
        cookie_file = Path(path) if path else self.config_path

        try:
            # 确保目录存在
            cookie_file.parent.mkdir(parents=True, exist_ok=True)

            # 写入ttwid
            cookie_file.write_text(f"ttwid={ttwid}\n", encoding='utf-8')

            logger.info(f"Cookie已保存到: {cookie_file}")
            return True

        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False


# 默认Cookie管理器实例
default_cookie_manager = CookieManager()
