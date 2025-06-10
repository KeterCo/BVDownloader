import subprocess
import os
from typing import Callable
import threading
from ..utils.logger import VideoLogger, LogLevel
from ..utils.config import Config
from .command_builder import CommandBuilder
import locale


class VideoDownloader:
    def __init__(self, logger: VideoLogger):
        self.logger = logger
        self.active_downloads = 0
        self.config = Config()
        self.command_builder = CommandBuilder(self.config)
        self._lock = threading.Lock()
        # 获取系统默认编码
        self.system_encoding = locale.getpreferredencoding()

    def start_download(self, bv: str, is_login: bool, callback=None):
        """开始下载视频"""
        try:
            # 构建命令
            cmd = self.command_builder.build_command(bv, is_login)
            cmd_str = " ".join(cmd)
            self.logger.log_to_file(f"执行命令: {cmd_str}")
            
            # 执行命令
            process = self.run_bbdown(cmd_str)
            
            # 读取输出
            output = []
            success = False
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    line = line.strip()
                    output.append(line)
                    # 只输出到本地日志
                    self.logger.log_to_file(line)
                    # 检查是否包含成功标志
                    if "任务完成" in line:
                        success = True
            
            # 获取返回码
            return_code = process.poll()
            
            # 合并输出
            full_output = "\n".join(output)
            
            # 检查是否成功（根据任务完成标志或返回码）
            if success or return_code == 0:
                if callback:
                    callback(True)
            else:
                if callback:
                    callback(False, full_output)
                    
        except Exception as e:
            if callback:
                callback(False, str(e))

    def is_all_complete(self) -> bool:
        with self._lock:
            return self.active_downloads == 0

    def _check_bbdown(self) -> bool:
        try:
            subprocess.run(["bbdown", "--version"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False

    def run_bbdown(self, command):
        """Run BBDown with hidden console window"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            command,
            shell=True,
            startupinfo=startupinfo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return process