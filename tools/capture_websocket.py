#!/usr/bin/env python3
"""
WebSocket 拦截工具

使用mitmproxy拦截浏览器访问抖音直播间时的WebSocket连接。
"""

import argparse
import logging
from mitmproxy import http

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)


class WebSocketInterceptor:
    """WebSocket拦截器"""

    def __init__(self):
        self.found_websocket = False
        self.ws_url = None
        self.ws_headers = None

    def request(self, flow: http.HTTPFlow) -> None:
        """处理请求"""
        # 检查是否是WebSocket升级请求
        if flow.request.pretty_host.endswith("douyin.com"):
            logger.info(f"请求: {flow.request.method} {flow.request.pretty_url}")

    def response(self, flow: http.HTTPFlow) -> None:
        """处理响应"""
        # 检查WebSocket连接
        if flow.websocket:
            self.found_websocket = True
            self.ws_url = f"wss://{flow.request.pretty_host}{flow.request.path}"
            self.ws_headers = dict(flow.request.headers)

            logger.info("="*60)
            logger.info("发现WebSocket连接！")
            logger.info("="*60)
            logger.info(f"URL: {self.ws_url}")
            logger.info(f"Headers: {self.ws_headers}")
            logger.info("="*60)

            # 保存到文件
            self.save_to_file()

    def save_to_file(self):
        """保存到文件"""
        import json
        from pathlib import Path

        result = {
            "url": self.ws_url,
            "headers": dict(self.ws_headers) if self.ws_headers else {},
            "found": True
        }

        output_file = Path("websocket_url.json")
        output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        logger.info(f"WebSocket信息已保存到: {output_file.absolute()}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="拦截抖音直播间WebSocket连接")
    parser.add_argument("--port", type=int, default=8080, help="代理端口 (默认: 8080)")
    args = parser.parse_args()

    logger.info("="*60)
    logger.info("WebSocket 拦截工具")
    logger.info("="*60)
    logger.info(f"代理端口: {args.port}")
    logger.info("")
    logger.info("使用步骤:")
    logger.info("1. 启动本工具")
    logger.info("2. 配置浏览器代理: 127.0.0.1:8080")
    logger.info("3. 访问: https://live.douyin.com/<房间ID>")
    logger.info("4. 查看控制台输出的WebSocket URL")
    logger.info("5. URL会自动保存到 websocket_url.json")
    logger.info("")
    logger.info("按 Ctrl+C 停止")
    logger.info("="*60)

    from mitmproxy.tools.main import mitmproxy
    sys.argv = ["mitmproxy", "--listen-port", str(args.port)]

    try:
        mitmproxy()
    except KeyboardInterrupt:
        logger.info("\n已停止")


if __name__ == "__main__":
    main()
