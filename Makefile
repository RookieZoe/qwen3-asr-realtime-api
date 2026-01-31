.PHONY: help install install-demo install-dev install-all start stop test docker-build docker-run docker-stop clean sync lock

# Default target
help:
	@echo "Qwen3-ASR-Realtime Server - Available Commands:"
	@echo ""
	@echo "  === uv 环境管理 ==="
	@echo "  make sync          - 同步依赖到 .venv (推荐)"
	@echo "  make sync-demo     - 同步主服务 + Demo 依赖"
	@echo "  make sync-all      - 同步所有依赖 (包含 dev)"
	@echo "  make lock          - 锁定依赖版本"
	@echo ""
	@echo "  === 传统 pip 安装 (不推荐) ==="
	@echo "  make install       - 安装主服务依赖"
	@echo "  make install-demo  - 安装 Demo 依赖"
	@echo "  make install-dev   - 安装开发依赖"
	@echo ""
	@echo "  === 服务管理 ==="
	@echo "  make start         - 启动服务"
	@echo "  make stop          - 停止服务"
	@echo ""
	@echo "  === 测试 ==="
	@echo "  make test          - 运行所有测试"
	@echo "  make test-basic    - 运行基础 WebSocket 测试"
	@echo "  make test-sdk      - 运行 SDK 兼容性测试"
	@echo ""
	@echo "  === Docker ==="
	@echo "  make docker-build  - 构建 Docker 镜像"
	@echo "  make docker-run    - 使用 Docker Compose 运行"
	@echo "  make docker-stop   - 停止 Docker 容器"
	@echo "  make docker-logs   - 查看 Docker 日志"
	@echo ""
	@echo "  === 开发工具 ==="
	@echo "  make lint          - 运行代码检查"
	@echo "  make format        - 格式化代码"
	@echo "  make clean         - 清理缓存文件"
	@echo ""

# =====================
# uv 环境管理 (推荐)
# =====================

# 同步主服务依赖
sync:
	uv sync

# 同步主服务 + Demo 依赖
sync-demo:
	uv sync --extra demo

# 同步所有依赖
sync-all:
	uv sync --all-extras

# 锁定依赖版本
lock:
	uv lock

# =====================
# 传统 pip 安装 (兼容)
# =====================

# 安装主服务依赖
install:
	uv pip install -e .

# 安装 Demo 依赖
install-demo:
	uv pip install -e ".[demo]"

# 安装开发依赖
install-dev:
	uv pip install -e ".[dev]"

# 安装所有依赖
install-all:
	uv pip install -e ".[all]"

# =====================
# 服务管理
# =====================

# 启动服务
start:
	uv run python main.py

# 直接启动 (不使用 uv run)
start-direct:
	.venv/bin/python main.py

# 停止服务
stop:
	-pkill -f "python main.py" 2>/dev/null || true

# =====================
# 测试
# =====================

test: test-basic test-sdk

test-basic:
	@echo "Running basic WebSocket test..."
	uv run python tests/test_websocket.py

test-sdk:
	@echo "Running SDK compatibility test..."
	uv run python tests/test_sdk_compatibility.py

test-vad:
	@echo "Running VAD test..."
	uv run python tests/test_vad_asr.py

# =====================
# Docker
# =====================

docker-build:
	docker build -t qwen3-asr-realtime:latest .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker rmi qwen3-asr-realtime:latest 2>/dev/null || true

# =====================
# 开发工具
# =====================

# 代码检查
lint:
	uv run ruff check src/ main.py

# 格式化代码
format:
	uv run ruff format src/ main.py

# 类型检查
typecheck:
	uv run mypy src/ main.py

# 清理缓存
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/ .ruff_cache/ .mypy_cache/ 2>/dev/null || true

# 深度清理 (包括 .venv)
clean-all: clean
	rm -rf .venv/ uv.lock 2>/dev/null || true

# =====================
# 初始化
# =====================

# 开发环境初始化
dev-setup:
	cp .env.example .env
	uv sync --all-extras
	@echo ""
	@echo "✅ 开发环境初始化完成!"
	@echo "   1. 编辑 .env 配置文件"
	@echo "   2. 运行 'make start' 启动服务"

# 生产环境初始化
prod-setup:
	cp .env.example .env
	uv sync
	@echo ""
	@echo "✅ 生产环境初始化完成!"
	@echo "   1. 编辑 .env 配置文件"
	@echo "   2. 运行 'make start' 启动服务"
