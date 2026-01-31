# Qwen3-ASR-Realtime Server

A private deployment WebSocket service compatible with Alibaba Cloud's Qwen3-ASR-realtime API, powered by vLLM for streaming ASR.

## Features

- **Real-time ASR**: Streaming speech recognition with low latency
- **VAD Mode**: Automatic voice activity detection for hands-free operation
- **Manual Mode**: File-based recognition with manual commit control
- **Protocol Compatible**: Drop-in replacement for Alibaba Cloud's official API
- **Web Demo**: Browser-based testing interface
- **Python SDK**: Official DashScope SDK compatible

## Quick Start

### 1. Installation

```bash
cd qwen3-asr-realtime-server
pip install -r requirements.txt
```

### 2. Configuration

Copy and edit the environment file:

```bash
cp .env.example .env
```

Key settings:
- `QWEN3_ASR_MODEL_PATH`: Model path (default: `Qwen/Qwen3-ASR-1.7B`)
- `SERVER_PORT`: Server port (default: `8001`)
- `GPU_MEMORY_UTILIZATION`: GPU memory usage (default: `0.5`)

### 3. Start Server

```bash
python main.py
```

Server will start at `ws://localhost:8001/api-ws/v1/realtime`

### 4. Test with Web Demo

```bash
cd demo
python -m http.server 8080
```

Open http://localhost:8080 in your browser.

### 5. Test with Python SDK

```bash
# Manual mode (file)
python demo/demo_sdk.py --mode manual --file test.wav

# VAD mode (microphone)
python demo/demo_sdk.py --mode vad
```

## Docker Deployment

### Build and Run

```bash
docker-compose up -d
```

Or manually:

```bash
docker build -t qwen3-asr-realtime .
docker run -d \
  -p 8001:8001 \
  --gpus all \
  -e QWEN3_ASR_MODEL_PATH=Qwen/Qwen3-ASR-1.7B \
  -e GPU_MEMORY_UTILIZATION=0.5 \
  qwen3-asr-realtime
```

## API Reference

### WebSocket Endpoint

```
ws://host:port/api-ws/v1/realtime
```

### Protocol Events

#### Client → Server

| Event | Description |
|-------|-------------|
| `session.update` | Configure session parameters |
| `input_audio_buffer.append` | Send audio chunk (base64) |
| `input_audio_buffer.commit` | Commit audio (Manual mode) |
| `session.finish` | End session |

#### Server → Client

| Event | Description |
|-------|-------------|
| `session.created` | Session initialized |
| `session.updated` | Configuration applied |
| `input_audio_buffer.speech_started` | VAD detected speech |
| `input_audio_buffer.speech_stopped` | VAD detected silence |
| `conversation.item.input_audio_transcription.text` | Interim result |
| `conversation.item.input_audio_transcription.completed` | Final result |
| `session.finished` | Session ended |
| `error` | Error occurred |

### Example: Manual Mode

```python
import asyncio
import base64
import json
import websockets

async def recognize():
    uri = "ws://localhost:8001/api-ws/v1/realtime"
    
    async with websockets.connect(uri) as ws:
        # 1. Wait for session.created
        response = await ws.recv()
        
        # 2. Configure session
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm",
                "sample_rate": 16000,
                "input_audio_transcription": {
                    "language": "auto"
                },
                "turn_detection": None  # Manual mode
            }
        }))
        
        # 3. Send audio
        with open("audio.wav", "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        
        await ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }))
        
        # 4. Commit
        await ws.send(json.dumps({
            "type": "input_audio_buffer.commit"
        }))
        
        # 5. Get results
        while True:
            response = await ws.recv()
            data = json.loads(response)
            if data['type'] == 'conversation.item.input_audio_transcription.completed':
                print(f"Result: {data['transcript']}")
                break

asyncio.run(recognize())
```

### Example: VAD Mode

```python
# Enable VAD in session.update
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

# Stream audio continuously - VAD will auto-detect speech boundaries
```

## Testing

Run the test suite:

```bash
# WebSocket protocol test
python tests/test_websocket.py

# VAD + ASR integration test
python tests/test_vad_asr.py

# SDK compatibility test
python tests/test_sdk_compatibility.py
```

## Architecture

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

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8001` | Server port |
| `QWEN3_ASR_MODEL_PATH` | `Qwen/Qwen3-ASR-1.7B` | Model path or HF ID |
| `GPU_MEMORY_UTILIZATION` | `0.5` | GPU memory fraction |
| `MAX_NEW_TOKENS` | `32` | Max tokens per inference |
| `MODEL_DTYPE` | `half` | Model dtype (half/float) |
| `VAD_ENABLED` | `true` | Enable VAD by default |
| `VAD_THRESHOLD` | `0.5` | VAD detection threshold |
| `VAD_SILENCE_DURATION_MS` | `400` | Silence duration for speech end |
| `STREAMING_CHUNK_SIZE_SEC` | `2.0` | ASR chunk size in seconds |
| `LOG_LEVEL` | `info` | Logging level |

## Troubleshooting

### Server won't start

Check GPU availability:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### Connection refused

Ensure server is running and port is correct:
```bash
curl http://localhost:8001/health
```

### No recognition results

- Verify audio format: 16kHz, 16-bit, mono PCM
- Check VAD threshold if using VAD mode
- Review server logs for errors

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) - Base ASR model
- [DashScope](https://dashscope.aliyun.com/) - Official SDK reference
- [vLLM](https://github.com/vllm-project/vllm) - Inference backend
