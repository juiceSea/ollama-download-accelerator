#!/bin/bash

# 测试 Ollama 下载加速器的示例脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Ollama 下载加速器测试 =====${NC}"
echo ""

# 检查是否安装了 Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}警告: 未检测到 Ollama 命令。请确保已安装 Ollama。${NC}"
    echo "可以通过以下命令安装 Ollama (Linux):"
    echo "curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

# 检查是否提供了模型名称
if [ $# -eq 0 ]; then
    echo "请提供要下载的模型名称。"
    echo "用法: $0 <模型名称> [下载器类型] [速度阈值] [检查间隔] [最大重试次数]"
    echo ""
    echo "下载器类型: basic (基本下载器) 或 advanced (高级下载器，默认)"
    echo "例如: $0 llama3.2 advanced 0.5 5 50"
    echo ""
    echo "可用的模型列表:"
    ollama list | grep -v "NAME" | awk '{print "- " $1}'
    exit 1
fi

MODEL_NAME=$1
DOWNLOADER_TYPE=${2:-"advanced"}  # 默认使用高级下载器
SPEED_THRESHOLD=${3:-0.5}  # 默认值: 0.5 MB/s
CHECK_INTERVAL=${4:-5}     # 默认值: 5秒
MAX_RETRIES=${5:-50}       # 默认值: 50次

# 高级下载器的额外参数
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
PAUSE_DURATION=60

echo -e "将使用以下参数下载模型 ${GREEN}$MODEL_NAME${NC}:"
echo -e "下载器类型: ${GREEN}$DOWNLOADER_TYPE${NC}"
echo "- 速度阈值: $SPEED_THRESHOLD MB/s"
echo "- 检查间隔: $CHECK_INTERVAL 秒"
echo "- 最大重试次数: $MAX_RETRIES"

if [ "$DOWNLOADER_TYPE" = "advanced" ]; then
    echo "- CPU使用率阈值: $CPU_THRESHOLD%"
    echo "- 内存使用率阈值: $MEMORY_THRESHOLD%"
    echo "- 暂停时间: $PAUSE_DURATION 秒"
fi

echo ""

# 确认是否继续
read -p "是否继续? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消下载。"
    exit 0
fi

# 运行下载加速器
echo -e "${GREEN}开始下载...${NC}"
echo "按 Ctrl+C 可随时中断下载"
echo ""
echo -e "${YELLOW}下载进度将显示在下方，详细日志保存在日志文件中${NC}"
echo ""

# 根据下载器类型选择使用哪个脚本
if [ "$DOWNLOADER_TYPE" = "basic" ]; then
    # 使用基本下载加速器
    python3 ./ollama_download_accelerator.py "$MODEL_NAME" \
        --speed-threshold "$SPEED_THRESHOLD" \
        --check-interval "$CHECK_INTERVAL" \
        --max-retries "$MAX_RETRIES"
else
    # 使用高级下载器
    python3 ./ollama_advanced_downloader.py "$MODEL_NAME" \
        --speed-threshold "$SPEED_THRESHOLD" \
        --check-interval "$CHECK_INTERVAL" \
        --max-retries "$MAX_RETRIES" \
        --cpu-threshold "$CPU_THRESHOLD" \
        --memory-threshold "$MEMORY_THRESHOLD" \
        --pause-duration "$PAUSE_DURATION"
fi

# 检查下载结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}下载完成!${NC}"
else
    echo -e "${YELLOW}下载过程中出现错误。${NC}"
fi 