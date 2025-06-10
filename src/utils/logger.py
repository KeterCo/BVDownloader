import logging
import os
from datetime import datetime
from typing import Callable, List, Dict, Optional
from enum import Enum
from .paths import app_paths

class LogLevel(Enum):
    SUCCESS = 'SUCCESS'
    ERROR = 'ERROR'
    INFO = 'INFO'

class LogEntry:
    def __init__(self, message: str, level: LogLevel = LogLevel.INFO):
        self.message = message
        self.level = level
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"[{self.timestamp}] {self.message}"

class VideoLogger:
    def __init__(self):
        self._callbacks: List[Callable[[str, LogLevel], None]] = []
        self.log_file = app_paths.log_file
        self.max_size = 10 * 1024 * 1024  # 10MB
        self.success_count = 0
        self.failed_bvs = []
        self.failed_reasons = {}
        self.window_logs = []  # 存储窗口日志

    def register_callback(self, callback: Callable[[str, LogLevel], None]):
        """注册日志回调函数"""
        self._callbacks.append(callback)

    def _rotate_log_if_needed(self):
        """检查并轮转日志文件"""
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) >= self.max_size:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_log_file = app_paths.get_new_log_file(timestamp)
                os.rename(self.log_file, new_log_file)
        except Exception as e:
            print(f"日志轮转失败: {str(e)}")

    def log_to_file(self, message: str, level: LogLevel = LogLevel.INFO):
        """只写入文件的日志"""
        try:
            self._rotate_log_if_needed()
            with open(self.log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"写入日志失败: {str(e)}")

    def log_to_window(self, message: str, level: LogLevel = LogLevel.INFO):
        """显示在窗口的日志，同时保存到内存"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # 保存到内存
        self.window_logs.append(formatted_message)
        
        # 调用所有注册的回调函数（更新窗口显示）
        for callback in self._callbacks:
            callback(formatted_message, level)

    def save_window_logs(self):
        """将当前会话的窗口日志保存到文件"""
        try:
            self._rotate_log_if_needed()
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("\n=== 窗口日志开始 ===\n")
                for log in self.window_logs:
                    f.write(f"{log}\n")
                f.write("=== 窗口日志结束 ===\n\n")
            # 清空当前会话的窗口日志
            self.window_logs = []
        except Exception as e:
            print(f"保存窗口日志失败: {str(e)}")

    def record_download_result(self, bv: str, success: bool, reason: str = None):
        """记录下载结果"""
        if success:
            self.success_count += 1
        else:
            self.failed_bvs.append(bv)
            self.failed_reasons[bv] = reason

    def print_summary(self):
        """只在窗口显示统计信息"""
        total = self.success_count + len(self.failed_bvs)
        summary = [
            "下载任务完成统计:",
            f"总计: {total} 个视频",
            f"成功: {self.success_count} 个",
            f"失败: {len(self.failed_bvs)} 个"
        ]
        
        if self.failed_bvs:
            summary.append("\n失败详情:")
            for bv in self.failed_bvs:
                summary.append(f"- {bv}: {self.failed_reasons.get(bv, '未知原因')}")

        summary_text = "\n".join(summary)
        self.log_to_window(summary_text)
        
        # 保存窗口日志到文件
        self.save_window_logs()
        
        # 重置计数器
        self.success_count = 0
        self.failed_bvs = []
        self.failed_reasons = {}

# 创建全局logger实例
logger = VideoLogger()