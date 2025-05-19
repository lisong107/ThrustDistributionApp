import json
import websocket


def on_message(ws, message):
    try:
        if isinstance(message, bytes) and len(message) >= 7:
            header = message[:7]
            payload = message[7:]

            reply_type = header[0]
            is_error = header[1]
            is_final_block = header[2]
            block_id = int.from_bytes(header[3:7], byteorder="big")

            try:
                json_str = payload.decode("utf-8")
                data = json.loads(json_str)
            except UnicodeDecodeError:
                print("⚠️ 编码错误，无法解码 UTF-8。原始内容:", payload)
                return
            except json.JSONDecodeError:
                print("⚠️ JSON 解码失败。原始字符串:", json_str)
                return

            print(f"✅ 接收到数据：")
            print(f"  回复类型: {reply_type}")
            print(f"  是否错误: {bool(is_error)}")
            print(f"  是否最后一块: {bool(is_final_block)}")
            print(f"  分块编号: {block_id}")
            print(f"  内容: {data}")
        else:
            print("⚠️ 接收到非预期格式数据:", message)
    except Exception as e:
        print("❌ 解析消息失败:", e)
        print("原始消息:", message)


def on_error(ws, error):
    print("❌ 发生错误:", error)


def on_close(ws, close_status_code, close_msg):
    print("🔌 连接关闭:", close_status_code, close_msg)


def on_open(ws):
    print("✅ 连接成功，发送订阅请求")

    payload_dict = {
        "Interval": 100,
        "AskField": ["1", "2", "3", "4", "7"],
        "AskType": 1,
    }

    try:
        ws.send(json.dumps(payload_dict))  # 默认以文本帧发送
        print("📤 已发送订阅请求")
    except Exception as e:
        print("❌ 发送失败:", e)


if __name__ == "__main__":
    websocket.enableTrace(False)  # 设置为 True 可查看底层通信

    ws = websocket.WebSocketApp(
        "ws://180.168.71.10:8119/111",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # 可加 `ping_interval` 和 `ping_timeout` 参数保持长连
    while True:
        try:
            ws.run_forever(ping_interval=20, ping_timeout=5)
        except KeyboardInterrupt:
            print("⛔ 手动中断")
            break
        except Exception as e:
            print("❌ WebSocket 异常，尝试重连:", e)
