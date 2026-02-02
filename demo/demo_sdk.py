#!/usr/bin/env python3
"""
Qwen3-ASR Realtime Python Demo
使用官方 DashScope SDK 连接私有后端服务

功能:
- VAD 模式: 实时录音识别
- Manual 模式: 音频文件识别
- 支持实时显示识别结果
"""

import argparse
import base64
import os
import signal
import sys
import time
from datetime import datetime

# 安装: pip install dashscope>=1.25.6
import dashscope
from dashscope.audio.qwen_omni import OmniRealtimeCallback, OmniRealtimeConversation
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams

# ==================== 配置 ====================

# 私有后端服务地址 (修改为你的服务地址)
DEFAULT_WS_URL = "ws://localhost:8080/api-ws/v1/realtime"

# API Key (私有服务通常不需要，但 SDK 要求提供，可以随便填)
DEFAULT_API_KEY = "dummy-api-key-for-local-server"


# ==================== 日志配置 ====================

def setup_logging():
    """配置日志输出"""
    import logging

    logger = logging.getLogger("dashscope")
    logger.setLevel(logging.INFO)

    # 清除已有处理器
    logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


# ==================== 回调处理 ====================


class ASRCallback(OmniRealtimeCallback):
    """实时识别回调处理"""

    def __init__(self):
        self.confirmed_text = ""
        self.stash_text = ""
        self.is_running = True

    def on_open(self):
        print("\n✅ 连接成功")

    def on_close(self, code, msg):
        print(f"\n❌ 连接关闭, code: {code}, msg: {msg}")
        self.is_running = False

    def on_event(self, response):
        event_type = response.get("type", "")

        # 会话创建
        if event_type == "session.created":
            session_id = response.get("session", {}).get("id", "unknown")
            print(f"📢 会话创建: {session_id}")

        # 会话更新
        elif event_type == "session.updated":
            print("📢 会话配置更新成功")

        # 语音开始 (VAD 模式)
        elif event_type == "input_audio_buffer.speech_started":
            print("\n🎤 [检测到语音开始]")

        # 语音结束 (VAD 模式)
        elif event_type == "input_audio_buffer.speech_stopped":
            print("🛑 [检测到语音结束]")

        # 实时识别结果
        elif event_type == "conversation.item.input_audio_transcription.text":
            text = response.get("text", "")
            stash = response.get("stash", "")
            language = response.get("language", "")
            emotion = response.get("emotion", "")

            # 更新已确认文本
            if text:
                self.confirmed_text = text
            self.stash_text = stash

            # 实时显示
            display_text = text + stash
            print(f"\r📝 识别中: {display_text[:80]}...", end="", flush=True)

        # 最终识别结果
        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = response.get("transcript", "")
            language = response.get("language", "")
            emotion = response.get("emotion", "")

            self.confirmed_text += transcript
            self.stash_text = ""

            print(f"\n✅ [识别完成]")
            print(f"   文本: {transcript}")
            print(f"   语言: {language}")
            print(f"   情感: {emotion}")

        # 会话结束
        elif event_type == "session.finished":
            print("\n🏁 会话结束")
            self.is_running = False

        # 错误
        elif event_type == "error":
            error = response.get("error", {})
            print(f"\n❌ [错误] {error.get('message', 'Unknown error')}")


# ==================== 音频处理 ====================


def list_audio_devices():
    """列出所有可用的音频输入设备"""
    try:
        import pyaudio
    except ImportError:
        print("请先安装 pyaudio: pip install pyaudio")
        return []

    audio = pyaudio.PyAudio()
    devices = []

    print("\n🎤 可用音频输入设备:")
    print("-" * 60)

    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if int(info["maxInputChannels"]) > 0:  # 仅显示输入设备
            is_default = info.get("index") == audio.get_default_input_device_info().get("index")
            default_marker = " ⭐ (默认)" if is_default else ""
            print(f"  [{i}] {info['name']}{default_marker}")
            print(f"      采样率: {int(info['defaultSampleRate'])} Hz, 输入通道: {int(info['maxInputChannels'])}")
            devices.append({"index": i, "name": info["name"], "is_default": is_default})

    print("-" * 60)
    audio.terminate()
    return devices


def read_audio_chunks(file_path, chunk_size=3200):
    """按块读取音频文件 (3200 bytes = 0.1s PCM16/16kHz)"""
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def send_audio_file(conversation, file_path, delay=0.1):
    """发送音频文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"音频文件不存在: {file_path}")

    print(f"📁 正在处理: {file_path}")
    print(f"⏱️  发送间隔: {delay}s (模拟实时采集)")
    print("🛑 按 Ctrl+C 停止\n")

    total_bytes = 0
    start_time = time.time()

    for chunk in read_audio_chunks(file_path):
        audio_b64 = base64.b64encode(chunk).decode("ascii")
        conversation.append_audio(audio_b64)
        total_bytes += len(chunk)
        time.sleep(delay)

    elapsed = time.time() - start_time
    print(f"\n📊 发送完成: {total_bytes} bytes in {elapsed:.1f}s")


# ==================== 主程序 ====================


def run_vad_mode(url, api_key, language="auto", device_index=None):
    """
    VAD 模式: 实时录音识别

    需要安装: pip install pyaudio

    Args:
        url: WebSocket 服务地址
        api_key: API Key
        language: 识别语言
        device_index: 音频输入设备索引 (None 表示使用默认设备)
    """
    try:
        import pyaudio
    except ImportError:
        print("请先安装 pyaudio: pip install pyaudio")
        return

    print("=" * 60)
    print("🎙️ VAD 模式 - 实时录音识别")
    print("=" * 60)
    print(f"服务端: {url}")
    print(f"语言: {language}")

    # 获取设备信息
    audio = pyaudio.PyAudio()
    if device_index is not None:
        try:
            device_info = audio.get_device_info_by_index(device_index)
            print(f"音频设备: [{device_index}] {device_info['name']}")
        except Exception as e:
            print(f"❌ 无效的设备索引 {device_index}: {e}")
            audio.terminate()
            return
    else:
        device_info = audio.get_default_input_device_info()
        print(f"音频设备: [默认] {device_info['name']}")

    print("按 Ctrl+C 停止录音\n")

    # 创建回调
    callback = ASRCallback()

    # 创建会话
    conversation = OmniRealtimeConversation(
        model="qwen3-asr-flash-realtime", url=url, callback=callback
    )

    # 配置
    transcription_params = TranscriptionParams(
        language=language, sample_rate=16000, input_audio_format="pcm"
    )

    # 连接
    conversation.connect()

    conversation.update_session(
        output_modalities=["text"],
        enable_turn_detection=True,
        turn_detection_type="server_vad",
        turn_detection_threshold=0.3,
        turn_detection_silence_duration_ms=500,
        enable_input_audio_transcription=True,
        transcription_params=transcription_params,
    )

    # 录音参数
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000

    # 初始化录音 (复用已创建的 audio 实例)
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
        input_device_index=device_index,
    )

    print("🎤 开始录音...\n")

    try:
        while callback.is_running:
            # 读取音频数据
            data = stream.read(CHUNK, exception_on_overflow=False)

            # 转换为 base64 发送
            audio_b64 = base64.b64encode(data).decode("ascii")
            conversation.append_audio(audio_b64)

    except KeyboardInterrupt:
        print("\n\n🛑 停止录音")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # 结束会话
        conversation.end_session()
        time.sleep(2)
        conversation.close()

        print(f"\n{'=' * 60}")
        print(f"📝 最终识别结果:\n{callback.confirmed_text}")
        print(f"{'=' * 60}")


def run_manual_mode(url, api_key, audio_file, language="auto", delay=0.1):
    """
    Manual 模式: 音频文件识别
    """
    print("=" * 60)
    print("📁 Manual 模式 - 音频文件识别")
    print("=" * 60)
    print(f"服务端: {url}")
    print(f"文件: {audio_file}")
    print(f"语言: {language}")
    print(f"发送间隔: {delay}s\n")

    # 创建回调
    callback = ASRCallback()

    # 创建会话
    conversation = OmniRealtimeConversation(
        model="qwen3-asr-flash-realtime", url=url, callback=callback
    )

    # 配置
    transcription_params = TranscriptionParams(
        language=language, sample_rate=16000, input_audio_format="pcm"
    )

    # 连接
    conversation.connect()

    conversation.update_session(
        output_modalities=["text"],
        enable_turn_detection=False,  # Manual 模式关闭 VAD
        enable_input_audio_transcription=True,
        transcription_params=transcription_params,
    )

    # 等待会话配置完成
    time.sleep(1)

    try:
        # 发送音频
        send_audio_file(conversation, audio_file, delay)

        # 提交识别 (Manual 模式需要)
        print("\n📤 提交识别...")
        conversation.commit()

        # 等待识别完成
        time.sleep(3)

        # 结束会话
        print("🏁 结束会话...")
        conversation.end_session()

        # 等待结果
        timeout = 30
        start = time.time()
        while callback.is_running and time.time() - start < timeout:
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
    finally:
        conversation.close()

        print(f"\n{'=' * 60}")
        print(f"📝 最终识别结果:\n{callback.confirmed_text}")
        print(f"{'=' * 60}")


# ==================== 命令行入口 ====================


def main():
    parser = argparse.ArgumentParser(
        description="Qwen3-ASR Realtime Python Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出可用音频设备
  python demo_sdk.py --list-devices

  # VAD 模式 (使用默认音频设备)
  python demo_sdk.py --mode vad --url ws://localhost:8080/api-ws/v1/realtime

  # VAD 模式 (指定音频设备)
  python demo_sdk.py --mode vad --device 2

  # Manual 模式 (音频文件)
  python demo_sdk.py --mode manual --file test.wav --url ws://localhost:8080/api-ws/v1/realtime

  # 指定语言
  python demo_sdk.py --mode manual --file test.wav --language zh
        """,
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["vad", "manual"],
        default="manual",
        help="识别模式: vad=实时录音, manual=音频文件 (默认: manual)",
    )

    parser.add_argument(
        "--url", "-u", default=DEFAULT_WS_URL, help=f"WebSocket 服务地址 (默认: {DEFAULT_WS_URL})"
    )

    parser.add_argument(
        "--file",
        "-f",
        help="音频文件路径 (Manual 模式必需, 支持 WAV/PCM 格式, 16kHz, 16-bit, 单声道)",
    )

    parser.add_argument(
        "--language",
        "-l",
        default="auto",
        choices=["auto", "zh", "en", "ja", "ko"],
        help="识别语言 (默认: auto)",
    )

    parser.add_argument(
        "--delay", "-d", type=float, default=0.1, help="音频发送间隔, 秒 (默认: 0.1)"
    )

    parser.add_argument(
        "--api-key", "-k", default=DEFAULT_API_KEY, help="API Key (本地服务可随意填写)"
    )

    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="列出所有可用的音频输入设备",
    )

    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="音频输入设备索引 (使用 --list-devices 查看可用设备)",
    )

    args = parser.parse_args()

    # 列出设备模式
    if args.list_devices:
        list_audio_devices()
        return

    # 设置日志
    setup_logging()

    # 设置 API Key
    dashscope.api_key = args.api_key

    # 运行
    if args.mode == "vad":
        run_vad_mode(args.url, args.api_key, args.language, args.device)
    else:
        if not args.file:
            print("❌ Manual 模式需要指定 --file 参数")
            parser.print_help()
            sys.exit(1)
        run_manual_mode(args.url, args.api_key, args.file, args.language, args.delay)


if __name__ == "__main__":
    main()
