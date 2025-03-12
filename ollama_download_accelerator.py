#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: 朱荣胜

import subprocess
import time
import re
import signal
import sys
import os
import argparse
import threading
import tempfile
from datetime import datetime

class OllamaDownloadAccelerator:
    def __init__(self, model_name, speed_threshold=0.5, check_interval=5, max_retries=50):
        """
        初始化Ollama下载加速器
        
        参数:
            model_name (str): 要下载的模型名称
            speed_threshold (float): 下载速度阈值(MB/s)，低于此值时重启下载
            check_interval (int): 检查下载速度的时间间隔(秒)
            max_retries (int): 最大重试次数
        """
        self.model_name = model_name
        self.speed_threshold = speed_threshold
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.process = None
        self.retry_count = 0
        self.total_downloaded = 0
        self.start_time = None
        # 创建log文件夹
        os.makedirs("log", exist_ok=True)
        self.log_file = f"log/ollama_download_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.monitor_thread = None
        self.should_stop_monitor = False
        self.last_percentage = 0
        self.current_speed = 0
        self.slow_speed_count = 0
        self.temp_output_file = None
        
    def log(self, message):
        """记录日志到文件和控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
            
    def log_to_file(self, message):
        """只记录日志到文件，不打印到控制台"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
            
    def parse_download_progress(self, line):
        """解析下载进度输出"""
        try:
            # 尝试匹配下载进度信息
            # 示例: "downloading model: 45%|████████████████▌         | 2.15G/4.78G [00:42<00:51, 50.9MB/s]"
            match = re.search(r"(\d+)%.*(\d+\.?\d+ *[GMK]B/s)", line)
            if match:
                percentage = int(match.group(1))
                speed = self.convert_to_bytes(match.group(2).replace(" ", "").replace("/s", "")) / (1024 * 1024)  # 转换为MB/s
                return percentage, speed
        except Exception as e:
            self.log_to_file(f"解析进度时出错: {e}")
        return None, None
    
    def convert_to_bytes(self, size_str):
        """将大小字符串转换为字节数"""
        size_str = size_str.upper()
        if 'K' in size_str:
            return float(size_str.replace('K', '').replace('B', '')) * 1024
        elif 'M' in size_str:
            return float(size_str.replace('M', '').replace('B', '')) * 1024 * 1024
        elif 'G' in size_str:
            return float(size_str.replace('G', '').replace('B', '')) * 1024 * 1024 * 1024
        else:
            return float(size_str.replace('B', ''))
    
    def start_download(self):
        """启动下载进程"""
        self.log(f"开始下载模型: {self.model_name}")
        if self.start_time is None:
            self.start_time = time.time()
        
        # 创建临时文件用于捕获输出
        self.temp_output_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        
        # 使用shell重定向而不是tee命令，确保输出同时显示在控制台和写入临时文件
        cmd = f"ollama pull {self.model_name} 2>&1 | tee -a {self.temp_output_file.name}"
        self.log_to_file(f"执行命令: {cmd}")
        
        # 使用shell=True以便能使用管道
        self.process = subprocess.Popen(cmd, shell=True)
        
        # 启动监控线程
        self.should_stop_monitor = False
        self.monitor_thread = threading.Thread(target=self.monitor_download)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        return self.process
    
    def monitor_download(self):
        """监控下载进度和速度"""
        self.log_to_file("开始监控下载进度和速度")
        last_speed_check_time = time.time()
        
        try:
            while not self.should_stop_monitor and self.process and self.process.poll() is None:
                # 读取临时文件的最后几行
                try:
                    with open(self.temp_output_file.name, 'r') as f:
                        # 移动到文件末尾前1000个字符的位置（如果文件足够大）
                        f.seek(0, os.SEEK_END)
                        pos = f.tell()
                        seek_pos = max(0, pos - 1000)
                        f.seek(seek_pos, os.SEEK_SET)
                        
                        # 读取最后部分内容
                        last_content = f.read()
                        
                        # 分析最后一行（可能包含进度信息）
                        lines = last_content.splitlines()
                        if lines:
                            last_line = lines[-1]
                            percentage, speed = self.parse_download_progress(last_line)
                            
                            if percentage is not None:
                                # 如果百分比增加，重置慢速计数
                                if percentage > self.last_percentage:
                                    self.slow_speed_count = 0
                                    self.last_percentage = percentage
                                
                                # 检查下载速度
                                current_time = time.time()
                                if current_time - last_speed_check_time >= self.check_interval:
                                    last_speed_check_time = current_time
                                    self.current_speed = speed
                                    
                                    # 记录当前下载速度到日志文件
                                    self.log_to_file(f"当前进度: {percentage}%, 下载速度: {speed:.2f} MB/s")
                                    
                                    # 如果速度低于阈值，增加慢速计数
                                    if speed < self.speed_threshold:
                                        self.slow_speed_count += 1
                                        self.log_to_file(f"下载速度低于阈值 ({self.speed_threshold} MB/s)，计数: {self.slow_speed_count}/3")
                                        
                                        # 如果连续3次速度低于阈值，发出重启信号
                                        if self.slow_speed_count >= 3:
                                            print(f"\n下载速度持续低于阈值 ({speed:.2f} MB/s < {self.speed_threshold} MB/s)，正在重启下载...")
                                            self.log_to_file(f"下载速度持续低于阈值，正在重启下载...")
                                            self.should_stop_monitor = True
                                            self.stop_download()
                                            break
                                    else:
                                        # 速度正常，重置慢速计数
                                        self.slow_speed_count = 0
                except Exception as e:
                    self.log_to_file(f"监控线程读取文件出错: {e}")
                
                # 休眠一段时间再检查
                time.sleep(1)
                
        except Exception as e:
            self.log_to_file(f"监控线程出错: {e}")
        
        self.log_to_file("监控线程结束")
    
    def stop_download(self):
        """停止下载进程"""
        if self.process and self.process.poll() is None:
            self.log_to_file("正在停止下载进程...")
            try:
                # 发送SIGTERM信号
                self.process.send_signal(signal.SIGTERM)
                # 等待进程结束，最多等待5秒
                for _ in range(5):
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
                # 如果进程仍在运行，强制终止
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
            except Exception as e:
                self.log_to_file(f"停止进程时出错: {e}")
        
        # 停止监控线程
        self.should_stop_monitor = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        # 清理临时文件
        if self.temp_output_file:
            try:
                os.unlink(self.temp_output_file.name)
            except Exception as e:
                self.log_to_file(f"删除临时文件时出错: {e}")
    
    def run(self):
        """运行下载加速器"""
        self.log(f"启动Ollama下载加速器 - 模型: {self.model_name}")
        self.log(f"速度阈值: {self.speed_threshold} MB/s, 检查间隔: {self.check_interval}秒")
        self.log(f"详细日志将保存到: {self.log_file}")
        print("\n开始下载，Ollama原生进度条将直接显示...\n")
        
        while self.retry_count < self.max_retries:
            process = self.start_download()
            
            try:
                # 等待进程完成
                process.wait()
                
                # 停止监控线程
                self.should_stop_monitor = True
                if self.monitor_thread and self.monitor_thread.is_alive():
                    self.monitor_thread.join(timeout=2)
                
                # 检查进程是否正常结束
                if process.returncode == 0:
                    print(f"\n模型 {self.model_name} 下载完成!")
                    self.log_to_file(f"模型 {self.model_name} 下载完成!")
                    break
                else:
                    # 如果进程异常结束但不是因为我们主动停止的，尝试重新下载
                    if not self.should_stop_monitor:
                        print(f"\n下载过程异常结束，返回码: {process.returncode}，正在重试...")
                        self.log_to_file(f"下载过程异常结束，返回码: {process.returncode}，正在重试...")
                        self.retry_count += 1
                        print(f"重试次数: {self.retry_count}/{self.max_retries}")
                        self.log_to_file(f"重试次数: {self.retry_count}/{self.max_retries}")
                    else:
                        # 如果是因为速度过慢主动停止的，增加重试计数并继续
                        self.retry_count += 1
                        print(f"重试次数: {self.retry_count}/{self.max_retries}")
                        self.log_to_file(f"重试次数: {self.retry_count}/{self.max_retries}")
                        print("\n重新开始下载，进度条将显示在下方...\n")
                    
            except KeyboardInterrupt:
                print("\n用户中断下载")
                self.log_to_file("用户中断下载")
                self.stop_download()
                break
            except Exception as e:
                print(f"\n下载过程中出错: {e}")
                self.log_to_file(f"下载过程中出错: {e}")
                self.stop_download()
                self.retry_count += 1
                print(f"重试次数: {self.retry_count}/{self.max_retries}")
                self.log_to_file(f"重试次数: {self.retry_count}/{self.max_retries}")
        
        # 计算总下载时间
        total_time = time.time() - self.start_time
        print(f"总下载时间: {total_time:.2f} 秒")
        print(f"总重试次数: {self.retry_count}")
        self.log_to_file(f"总下载时间: {total_time:.2f} 秒")
        self.log_to_file(f"总重试次数: {self.retry_count}")

def main():
    parser = argparse.ArgumentParser(description="Ollama模型下载加速器")
    parser.add_argument("model_name", help="要下载的模型名称")
    parser.add_argument("--speed-threshold", type=float, default=10, help="下载速度阈值(MB/s)，低于此值时重启下载")
    parser.add_argument("--check-interval", type=int, default=3, help="检查下载速度的时间间隔(秒)")
    parser.add_argument("--max-retries", type=int, default=50, help="最大重试次数")
    
    args = parser.parse_args()
    
    accelerator = OllamaDownloadAccelerator(
        model_name=args.model_name,
        speed_threshold=args.speed_threshold,
        check_interval=args.check_interval,
        max_retries=args.max_retries
    )
    
    try:
        accelerator.run()
    except KeyboardInterrupt:
        print("\n用户中断程序")
        sys.exit(0)

if __name__ == "__main__":
    main() 