# Qwen3-ASR-Realtime Server

兼容阿里云 Qwen3-ASR-realtime API 的私有部署 WebSocket 服务，基于 vLLM 实现流式 ASR。

## 功能特性

- **实时 ASR**: 低延迟流式语音识别
- **VAD 模式**: 自动语音活动检测，免提操作
- **Manual 模式**: 文件识别，手动控制提交
- **协议兼容**: 可直接替换阿里云官方 API
- **Web Demo**: 浏览器测试界面
- **Python SDK**: 兼容官方 DashScope SDK

## 快速开始

### 1. 安装 uv (推荐)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 克隆项目

```bash
git clone <your-repo-url>
cd qwen3-asr-realtime-server
```

### 3. 初始化环境

```bash
# 生产环境 (仅主服务依赖)
make prod-setup

# 开发环境 (包含所有依赖)
make dev-setup
```

或手动执行:

```bash
# 复制配置文件
cp .env.example .env

# 同步依赖 (自动创建 .venv)
uv sync

# 如需 Demo 依赖
uv sync --extra demo

# 如需所有依赖 (开发)
uv sync --all-extras
```

### 4. 配置

编辑 `.env` 文件:

```bash
QWEN3_ASR_MODEL_PATH=Qwen/Qwen3-ASR-1.7B  # 模型路径或 HuggingFace ID
SERVER_PORT=8001                          # 服务端口
GPU_MEMORY_UTILIZATION=0.5                # GPU 显存使用率
```

### 5. 启动服务

```bash
make start
# 或
uv run python main.py
```

服务启动后访问: `ws://localhost:8001/api-ws/v1/realtime`

### 6. 测试

```bash
# Web Demo
cd demo && python -m http.server 8080
# 访问 http://localhost:8080

# Python SDK Demo (需要先安装 demo 依赖)
uv sync --extra demo
uv run python demo/demo_sdk.py --mode manual --file test.wav
```

## 项目结构

```
qwen3-asr-realtime-server/
├── .venv/                  # uv 管理的虚拟环境
├── pyproject.toml          # 项目配置和依赖定义
├── uv.lock                 # 依赖锁定文件
├── main.py                 # 服务入口
├── .env                    # 环境配置
├── src/                    # 源代码
│   ├── handlers/           # WebSocket 处理器
│   ├── models/             # ASR/VAD 模型
│   └── utils/              # 工具函数
├── demo/                   # 演示代码
│   ├── index.html          # Web Demo
│   ├── demo_sdk.py         # Python SDK Demo
│   └── requirements.txt    # Demo 专用依赖
└── tests/                  # 测试脚本
```

## 依赖管理

### 依赖分组

| 分组 | 说明 | 安装命令 |
|------|------|----------|
| 默认 | 主服务依赖 | `uv sync` |
| demo | SDK 演示 | `uv sync --extra demo` |
| audio | 音频处理 | `uv sync --extra audio` |
| dev | 开发工具 | `uv sync --extra dev` |
| all | 所有依赖 | `uv sync --all-extras` |

### 常用命令

```bash
# 同步依赖
make sync           # 主服务依赖
make sync-demo      # + Demo 依赖
make sync-all       # 所有依赖

# 锁定依赖版本
make lock

# 清理环境
make clean          # 清理缓存
make clean-all      # 清理 .venv 和 uv.lock
```

## Docker 部署

### 使用 Docker Compose

```bash
docker-compose up -d
```

### 手动构建

```bash
docker build -t qwen3-asr-realtime .
docker run -d \
  -p 8001:8001 \
  --gpus all \
  -e QWEN3_ASR_MODEL_PATH=Qwen/Qwen3-ASR-1.7B \
  -e GPU_MEMORY_UTILIZATION=0.5 \
  qwen3-asr-realtime
```

## API 参考

### WebSocket 端点

```
ws://host:port/api-ws/v1/realtime
```

### HTTP 端点

| 端点 | 说明 |
|------|------|
| `GET /` | 服务信息 |
| `GET /health` | 健康检查 |
| `GET /metrics` | 监控指标 |
| `GET /stats` | 详细统计 |
| `GET /docs` | API 文档 |

### 协议事件

#### 客户端 → 服务端

| 事件 | 说明 |
|------|------|
| `session.update` | 配置会话参数 |
| `input_audio_buffer.append` | 发送音频 (base64) |
| `input_audio_buffer.commit` | 提交音频 (Manual 模式) |
| `session.finish` | 结束会话 |

#### 服务端 → 客户端

| 事件 | 说明 |
|------|------|
| `session.created` | 会话创建 |
| `session.updated` | 配置更新 |
| `input_audio_buffer.speech_started` | VAD 检测到语音开始 |
| `input_audio_buffer.speech_stopped` | VAD 检测到语音结束 |
| `conversation.item.input_audio_transcription.text` | 中间结果 |
| `conversation.item.input_audio_transcription.completed` | 最终结果 |
| `session.finished` | 会话结束 |
| `error` | 错误 |

### 示例: Manual 模式

```python
import asyncio
import base64
import json
import websockets

async def recognize():
    uri = "ws://localhost:8001/api-ws/v1/realtime"
    
    async with websockets.connect(uri) as ws:
        # 1. 等待 session.created
        await ws.recv()
        
        # 2. 配置会话
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm",
                "sample_rate": 16000,
                "turn_detection": None  # Manual 模式
            }
        }))
        
        # 3. 发送音频
        with open("audio.wav", "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        
        await ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }))
        
        # 4. 提交
        await ws.send(json.dumps({
            "type": "input_audio_buffer.commit"
        }))
        
        # 5. 获取结果
        while True:
            data = json.loads(await ws.recv())
            if data['type'] == 'conversation.item.input_audio_transcription.completed':
                print(f"结果: {data['transcript']}")
                break

asyncio.run(recognize())
```

### 示例: VAD 模式

```python
# 在 session.update 中启用 VAD
await ws.send(json.dumps({
    "type": "session.update",
    "session": {
        "input_audio_format": "pcm",
        "sample_rate": 16000,
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "silence_duration_ms": 400
        }
    }
}))

# 持续发送音频，VAD 会自动检测语音边界
```

## 测试

```bash
# 运行所有测试
make test

# 单独测试
make test-basic    # WebSocket 协议测试
make test-sdk      # SDK 兼容性测试
make test-vad      # VAD 集成测试
```

## 架构

```
┌─────────────┐     WebSocket      ┌─────────────────┐
│   Client    │◄──────────────────►│  WebSocket      │
│  (SDK/Web)  │                    │   Handler       │
└─────────────┘                    └────────┬────────┘
                                            │
                       ┌────────────────────┼────────────────────┐
                       │                    │                    │
                       ▼                    ▼                    ▼
                ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                │    VAD      │    │    ASR      │    │   Session   │
                │  Manager    │    │  Manager    │    │   Handler   │
                └─────────────┘    └──────┬──────┘    └─────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │    vLLM     │
                                   │   Backend   │
                                   └─────────────┘
```

## 配置选项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SERVER_HOST` | `0.0.0.0` | 服务绑定地址 |
| `SERVER_PORT` | `8001` | 服务端口 |
| `QWEN3_ASR_MODEL_PATH` | `Qwen/Qwen3-ASR-1.7B` | 模型路径或 HF ID |
| `GPU_MEMORY_UTILIZATION` | `0.5` | GPU 显存使用率 |
| `MAX_NEW_TOKENS` | `32` | 每次推理最大 token 数 |
| `MODEL_DTYPE` | `half` | 模型数据类型 (half/float) |
| `VAD_ENABLED` | `true` | 默认启用 VAD |
| `VAD_THRESHOLD` | `0.5` | VAD 检测阈值 |
| `VAD_SILENCE_DURATION_MS` | `400` | 静音时长 (毫秒) |
| `STREAMING_CHUNK_SIZE_SEC` | `2.0` | ASR 分块大小 (秒) |
| `LOG_LEVEL` | `info` | 日志级别 |

## 故障排除

### 服务无法启动

检查 GPU 可用性:
```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
```

### 连接被拒绝

确认服务正在运行:
```bash
curl http://localhost:8001/health
```

### 无识别结果

- 检查音频格式: 16kHz, 16-bit, 单声道 PCM
- 调整 VAD 阈值 (如使用 VAD 模式)
- 查看服务日志

## 迁移部署

项目使用 uv 管理依赖，迁移时只需:

1. 复制整个项目目录
2. 在目标机器安装 uv
3. 运行 `uv sync` 重建环境

无需复制 `.venv` 目录，`uv.lock` 确保依赖版本一致。

## 许可证

MIT License

## 致谢

- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) - 基础 ASR 模型
- [DashScope](https://dashscope.aliyun.com/) - 官方 SDK 参考
- [vLLM](https://github.com/vllm-project/vllm) - 推理后端
- [uv](https://github.com/astral-sh/uv) - 包管理工具
