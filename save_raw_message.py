"""
保存原始消息到文件用于分析
"""
import asyncio
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.douyin.cookie import CookieManager
from src.douyin.connector_real import DouyinConnectorReal
from src.douyin.protobuf import PushFrameCodec
import gzip

async def save_messages():
    room_id = "168465302284"

    cookie_manager = CookieManager()
    ttwid = cookie_manager.load_from_file()

    print(f"保存直播间 {room_id} 的原始消息...")

    connector = DouyinConnectorReal(room_id, ttwid)

    if not await connector.connect():
        print("连接失败")
        return

    message_count = 0
    saved_count = 0

    # 保存目录
    save_dir = Path("debug_messages")
    save_dir.mkdir(exist_ok=True)

    async def handle_message(raw_message):
        nonlocal message_count, saved_count
        message_count += 1

        if isinstance(raw_message, bytes) and saved_count < 10:
            frame = PushFrameCodec.decode(raw_message)

            if frame and frame.payload:
                # 解压payload
                try:
                    if frame.headers_list and frame.headers_list.get('compress_type') == 'gzip':
                        decompressed = gzip.decompress(frame.payload)

                        # 保存解压后的数据
                        filename = save_dir / f"message_{saved_count+1}_raw.bin"
                        with open(filename, 'wb') as f:
                            f.write(decompressed)

                        # 保存hex预览
                        hexfile = save_dir / f"message_{saved_count+1}_hex.txt"
                        with open(hexfile, 'w', encoding='utf-8') as f:
                            f.write(f"Message #{saved_count+1}\n")
                            f.write(f"Size: {len(decompressed)} bytes\n")
                            f.write(f"Log ID: {frame.log_id}\n")
                            f.write(f"\nFirst 1000 bytes (hex):\n")
                            f.write(decompressed[:1000].hex())
                            f.write(f"\n\nFirst 500 bytes (attempted UTF-8):\n")
                            try:
                                f.write(decompressed[:500].decode('utf-8', errors='replace'))
                            except:
                                f.write("<decode error>")

                        saved_count += 1
                        print(f"已保存消息 #{saved_count}")

                except Exception as e:
                    print(f"保存失败: {e}")

        if saved_count >= 10 or message_count >= 50:
            print(f"\n已保存 {saved_count} 条消息，退出")
            await connector.disconnect()

    try:
        listen_task = asyncio.create_task(connector.listen(handle_message))
        await asyncio.sleep(10)
        await connector.disconnect()
        try:
            await asyncio.wait_for(listen_task, timeout=5)
        except:
            pass
    except Exception as e:
        print(f"\n异常: {e}")

    print(f"\n完成！保存了 {saved_count} 条原始消息到 {save_dir}/")


if __name__ == "__main__":
    asyncio.run(save_messages())
