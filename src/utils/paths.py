from appdirs import user_data_dir
import os

class AppPaths:
    def __init__(self):
        # 修改应用程序信息
        self.app_name = "BVDownloader"
        self.app_author = "BVDownloader"
        
        # 获取应用程序数据目录
        self.app_data_dir = user_data_dir(self.app_name, self.app_author)
        
        # 定义具体文件路径
        self.config_path = os.path.join(self.app_data_dir, "bvconfig.json")
        self.log_dir = os.path.join(self.app_data_dir, "logs")
        self.log_file = os.path.join(self.log_dir, "bilibili_downloader.log")
        
        # 确保目录存在
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保所有必要的目录都存在"""
        os.makedirs(self.app_data_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

    def get_new_log_file(self, timestamp):
        """获取新的日志文件路径"""
        return os.path.join(self.log_dir, f"bilibili_downloader_{timestamp}.log")

# 创建全局实例
app_paths = AppPaths() 