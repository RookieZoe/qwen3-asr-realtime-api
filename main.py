#!/usr/bin/env python3
"""
Qwen3-ASR-Realtime Server
Compatible with Alibaba Cloud Qwen3-ASR-realtime API
"""

import os
import sys
import signal
import asyncio
import threading
import time
import warnings
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any
import json

# 忽略已知无害的警告
warnings.filterwarnings("ignore", message="Casting torch.bfloat16 to torch.float16")
warnings.filterwarnings("ignore", message="Please use the new API settings to control TF32")
warnings.filterwarnings("ignore", message="The following generation flags are not valid")
warnings.filterwarnings("ignore", message="We must use the `spawn` multiprocessing start method")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# 加载 .env 文件
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# 将 src 目录添加到 Python 路径
src_path = Path(__file__).parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from fastapi import FastAPI, WebSocket
import uvicorn
from uvicorn import Server, Config

from handlers.websocket_handler import WebSocketHandler
from models.asr_manager import ASRManager
from utils.logger import get_logger

logger = get_logger(__name__)

# 全局状态
should_exit = False
server_instance = None

# 监控指标
metrics = {
    "server_start_time": None,
    "total_connections": 0,
    "active_connections": 0,
    "total_sessions": 0,
    "total_audio_seconds": 0.0,
    "requests_per_minute": [],
    "errors_total": 0,
}


def handle_signal(signum, frame):
    global should_exit
    signame = signal.Signals(signum).name
    logger.info(f"Received {signame}, shutting down...")
    should_exit = True
    
    # 强制退出定时器（如果 10 秒后还没退出，强制退出）
    def force_exit():
        time.sleep(10)
        if not should_exit:
            return
        logger.error("Force exiting...")
        os._exit(1)
    
    threading.Thread(target=force_exit, daemon=True).start()


# 注册信号处理器
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


class GracefulServer(Server):
    """自定义 Server 类，支持优雅关闭"""
    
    async def shutdown(self, sockets=None):
        logger.info("Shutting down uvicorn server...")
        await super().shutdown(sockets=sockets)
    
    async def main_loop(self):
        while not should_exit and not self.should_exit:
            await asyncio.sleep(0.1)
        
        if should_exit:
            logger.info("Exit signal received, initiating shutdown...")
            await self.shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global metrics
    metrics["server_start_time"] = datetime.utcnow()
    
    logger.info("=" * 60)
    logger.info("Starting Qwen3-ASR-Realtime Server")
    logger.info("=" * 60)
    logger.info(f"Model: {os.getenv('QWEN3_ASR_MODEL_PATH', 'Qwen/Qwen3-ASR-1.7B')}")
    logger.info(f"GPU Memory: {os.getenv('GPU_MEMORY_UTILIZATION', '0.5')}")
    logger.info(f"Server Port: {os.getenv('SERVER_PORT', '8001')}")
    logger.info("=" * 60)
    
    app.state.asr_manager = ASRManager()
    
    try:
        await app.state.asr_manager.load_model()
        logger.info("ASR Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    
    yield
    
    logger.info("Shutting down server...")
    if hasattr(app.state, 'asr_manager'):
        try:
            await asyncio.wait_for(
                app.state.asr_manager.unload_model(),
                timeout=10.0
            )
            logger.info("Model unloaded")
        except asyncio.TimeoutError:
            logger.warning("Model unload timeout, forcing exit...")
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    logger.info("Server shutdown complete")


app = FastAPI(
    title="Qwen3-ASR-Realtime Server",
    description="Compatible with Alibaba Cloud Qwen3-ASR-realtime API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "service": "Qwen3-ASR-Realtime Server",
        "version": "1.0.0",
        "websocket_endpoint": "/api-ws/v1/realtime",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": hasattr(app.state, 'asr_manager') and app.state.asr_manager.is_ready(),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    uptime_seconds = 0
    if metrics["server_start_time"]:
        uptime_seconds = (datetime.utcnow() - metrics["server_start_time"]).total_seconds()
    
    # Calculate requests per minute
    now = time.time()
    recent_requests = [t for t in metrics["requests_per_minute"] if now - t < 60]
    metrics["requests_per_minute"] = recent_requests
    rpm = len(recent_requests)
    
    return {
        "server": {
            "uptime_seconds": uptime_seconds,
            "start_time": metrics["server_start_time"].isoformat() if metrics["server_start_time"] else None,
        },
        "connections": {
            "total": metrics["total_connections"],
            "active": metrics["active_connections"],
        },
        "sessions": {
            "total": metrics["total_sessions"],
        },
        "audio": {
            "total_seconds_processed": round(metrics["total_audio_seconds"], 2),
        },
        "requests": {
            "per_minute": rpm,
            "errors_total": metrics["errors_total"],
        }
    }


@app.get("/stats")
async def get_stats():
    """Detailed statistics endpoint"""
    return {
        "service": "Qwen3-ASR-Realtime Server",
        "version": "1.0.0",
        "model": {
            "path": os.getenv('QWEN3_ASR_MODEL_PATH', 'Qwen/Qwen3-ASR-1.7B'),
            "loaded": hasattr(app.state, 'asr_manager') and app.state.asr_manager.is_ready(),
        },
        "configuration": {
            "gpu_memory_utilization": float(os.getenv('GPU_MEMORY_UTILIZATION', '0.5')),
            "max_new_tokens": int(os.getenv('MAX_NEW_TOKENS', '32')),
            "vad_enabled": os.getenv('VAD_ENABLED', 'true').lower() == 'true',
            "vad_threshold": float(os.getenv('VAD_THRESHOLD', '0.5')),
        },
        "metrics": await get_metrics(),
    }


@app.websocket("/api-ws/v1/realtime")
async def realtime_websocket(websocket: WebSocket):
    global metrics
    metrics["total_connections"] += 1
    metrics["active_connections"] += 1
    metrics["requests_per_minute"].append(time.time())
    
    try:
        handler = WebSocketHandler(websocket, app.state.asr_manager)
        await handler.handle()
    except Exception as e:
        metrics["errors_total"] += 1
        logger.error(f"WebSocket error: {e}")
        raise
    finally:
        metrics["active_connections"] -= 1


def run_server():
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8001"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    config = Config(
        app="main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,
        timeout_graceful_shutdown=30,
        ws_ping_interval=30.0,
        ws_ping_timeout=60.0,
        ws_per_message_deflate=False
    )
    
    server = GracefulServer(config=config)
    
    global server_instance
    server_instance = server
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"WebSocket: ws://{host}:{port}/api-ws/v1/realtime")
    logger.info("Press Ctrl+C to stop")
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
        should_exit = True
    finally:
        logger.info("Server stopped")


if __name__ == "__main__":
    run_server()
