# Qwen3-ASR-Realtime Server
# 兼容阿里云 Qwen3-ASR-realtime 接口的私有部署服务

from setuptools import setup, find_packages

setup(
    name="qwen3-asr-realtime-server",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "numpy>=1.24.0",
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
        "transformers>=4.36.0",
        "silero-vad>=4.0.0",
        "opuslib>=3.0.1",
        "pydantic>=2.5.0",
        "python-multipart>=0.0.6",
        "qwen-asr",  # 本地 Qwen3-ASR 包
    ],
    python_requires=">=3.9",
    author="Your Name",
    description="Compatible Qwen3-ASR-realtime WebSocket API Server",
)
