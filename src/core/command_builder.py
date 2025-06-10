import re
from typing import List
from ..utils.logger import VideoLogger
from ..utils.config import Config

class CommandBuilder:
    """命令生成器"""
    def __init__(self, config: Config):
        self.config = config
    
    def build_commands(self, input_text: str) -> List[str]:
        """
        从输入文本构建下载命令列表
        
        Args:
            input_text: 包含BV号的输入文本
            
        Returns:
            包含处理后命令的列表
        """
        config_data = self.config.get_config()
        prefix = config_data.get("prefix", "")
        suffix = config_data.get("suffix", "")
        bv_prefix = config_data.get("bv_prefix", "BV")
        
        # 提取BV号
        pattern = f'{bv_prefix}[A-Za-z0-9]{{10}}'
        bv_numbers = re.findall(pattern, input_text)
        
        # 构建命令
        commands = []
        for bv in bv_numbers:
            command = f"{prefix} {bv} {suffix}".strip()
            if command:
                commands.append(command)
        print(commands)
        return commands

    def build_command(self, bv: str, is_login: bool) -> List[str]:
        """构建完整的下载命令"""
        cmd = [self.config.bbdown_path]
        
        # 添加BV号
        cmd.append(bv)
        
        # 添加后缀参数（不包含work-dir）
        if self.config.suffix:
            suffix_parts = self.config.suffix.split()
            # 过滤掉--work-dir参数
            filtered_parts = []
            i = 0
            while i < len(suffix_parts):
                if suffix_parts[i] == "--work-dir":
                    i += 2  # 跳过--work-dir和它的值
                else:
                    filtered_parts.append(suffix_parts[i])
                    i += 1
            cmd.extend(filtered_parts)
            
        # 添加保存路径
        if self.config.save_path:
            cmd.extend(["--work-dir", self.config.save_path])
            
        # 如果需要登录但未登录，添加--login参数
        if self.config.need_login and not self.config.is_login:
            cmd.append("--login")
            
        return cmd

    def build_download_command(self, bv: str) -> List[str]:
        """构建下载命令参数"""
        cmd = []
        
        # 添加BV号
        cmd.append(bv)
        
        # 添加保存路径
        if self.config.save_path:
            cmd.extend(["--save-path", self.config.save_path])
            
        # 添加其他参数
        if self.config.other_params:
            cmd.extend(self.config.other_params.split())
            
        return cmd

    def extract_valid_bvs(self, text: str) -> List[str]:
        """从文本中提取有效的BV号"""
        # 使用正则表达式匹配BV号（BV后面跟着10位字符）
        pattern = r'BV[0-9A-Za-z]{10}'
        return re.findall(pattern, text)