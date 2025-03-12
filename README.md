# Ollama 下载加速器

这个工具用于加速 Ollama 模型的下载过程。它通过监控下载速度，在速度下降时自动重启下载来利用 Ollama 的断点续传功能，从而提高整体下载速度。

## 功能特点

- 自动监控 Ollama 模型下载速度
- 当下载速度低于设定阈值时自动重启下载
- 利用 Ollama 的断点续传功能继续下载
- 显示 Ollama 原生下载进度条，直观展示下载进度
- 详细的日志记录
- 可自定义速度阈值、检查间隔和最大重试次数

## 使用要求

- Python 3.6 或更高版本
- 已安装 Ollama
- 对于高级下载器：psutil 库（用于系统资源监控）

## 安装

1. 克隆或下载此仓库
2. 安装依赖项：

```bash
pip install -r requirements.txt
```

3. 确保脚本具有执行权限：

```bash
chmod +x ollama_download_accelerator.py
chmod +x ollama_advanced_downloader.py
chmod +x test_download.sh
```

## 使用方法

### 基本下载加速器

基本用法：

```bash
./ollama_download_accelerator.py <模型名称>
```

例如，下载 llama3.2 模型：

```bash
./ollama_download_accelerator.py llama3.2
```

#### 高级选项

您可以自定义以下参数：

- `--speed-threshold`: 下载速度阈值(MB/s)，低于此值时重启下载（默认：10）
- `--check-interval`: 检查下载速度的时间间隔(秒)（默认：3）
- `--max-retries`: 最大重试次数（默认：50）

例如：

```bash
./ollama_download_accelerator.py llama3.2 --speed-threshold 0.3 --check-interval 3 --max-retries 100
```

### 高级下载器

高级下载器增加了系统资源监控功能，可以在 CPU 或内存使用率过高时暂停下载。

基本用法：

```bash
./ollama_advanced_downloader.py <模型名称>
```

#### 高级选项

除了基本下载加速器的选项外，高级下载器还支持以下参数：

- `--cpu-threshold`: CPU使用率阈值(%)，高于此值时暂停下载（默认：80）
- `--memory-threshold`: 内存使用率阈值(%)，高于此值时暂停下载（默认：80）
- `--pause-duration`: 暂停下载的时间(秒)（默认：60）

例如：

```bash
./ollama_advanced_downloader.py llama3.2 --speed-threshold 0.3 --cpu-threshold 70 --memory-threshold 75 --pause-duration 120
```

### 测试脚本

为了方便使用，我们提供了一个测试脚本：

```bash
./test_download.sh <模型名称> [速度阈值] [检查间隔] [最大重试次数]
```

例如：

```bash
./test_download.sh llama3.2 0.5 5 50
```

## 工作原理

### 基本下载加速器

1. 脚本启动 `ollama pull` 命令下载指定模型
2. 实时显示 Ollama 原生下载进度条，同时在后台监控下载速度和进度
3. 当检测到下载速度连续3次低于设定阈值时，停止当前下载进程
4. 重新启动下载进程，Ollama 会自动从断点处继续下载
5. 重复此过程直到下载完成或达到最大重试次数

### 高级下载器

除了基本下载加速器的功能外，高级下载器还会：

1. 定期检查系统 CPU 和内存使用率
2. 当 CPU 或内存使用率超过设定阈值时，暂停下载指定时间
3. 暂停时间结束后，自动恢复下载
4. 记录暂停次数和总下载时间

## 日志

脚本会在当前目录生成日志文件，格式为 `ollama_download_<模型名称>_<时间戳>.log`。日志包含下载进度、速度、重试次数等信息。

为了不干扰 Ollama 原生进度条的显示，大部分状态信息只会记录到日志文件中，而不会直接打印到控制台。只有重要的状态变化（如重启下载、暂停下载等）才会显示在控制台上。

## 注意事项

- 此工具依赖于 Ollama 的断点续传功能，确保您使用的是支持此功能的 Ollama 版本
- 下载速度可能受网络条件、服务器负载等多种因素影响
- 如果您的网络条件较差，可以适当降低速度阈值
- 高级下载器需要 psutil 库来监控系统资源

## 许可证

MIT 