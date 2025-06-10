import json
import os
import sys
from pathlib import Path

class Config:
    def __init__(self):
        self.config_file = os.path.join(os.path.expanduser("~"), "AppData", "Local", "BVDownloader", "bvconfig.json")
        self.default_config = {
            "bbdown_path": "",
            "cached_bv": "BVaaaabbddee123",
            "suffix": " --show-all --dfn-priority \"<杜比视界,8K 超高清,HDR 真彩,4K 超清,1080P 60帧,1080P 高码率,1080P 高清,720P 高清,480P 清晰,360P 流畅>\" --download-danmaku -F \"<videoTitle>[<ownerName>][<dfn><fps>][<bvid>][P<pageNumber>_<pageTitle>]\" -p ALL --save-archives-to-file --skip-ai=false --delay-per-page=2 --work-dir ",
            "is_login": False,
            "need_login": True,
            "save_path": os.path.join(os.path.expanduser("~"), "Desktop", "BVDownloader")
        }
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_file):
                # 确保目录存在
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                # 创建默认配置
                self.save_config(self.default_config)
                return self.default_config

            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 确保所有必要的键都存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config

    def save_config(self, config):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def update_bbdown_path(self, path):
        """更新BBDown路径"""
        config = self.load_config()
        config["bbdown_path"] = path
        return self.save_config(config)

    def update_save_path(self, path):
        """更新保存路径"""
        config = self.load_config()
        config["save_path"] = path
        return self.save_config(config)

    def update_login_state(self, is_login):
        """更新登录状态"""
        config = self.load_config()
        config["is_login"] = is_login
        return self.save_config(config)

    def update_need_login(self, need_login):
        """更新是否需要登录才能下载"""
        config = self.load_config()
        config["need_login"] = need_login
        return self.save_config(config)

    def update_cached_bv(self, bv: str) -> bool:
        """更新缓存的BV号"""
        try:
            config = self.load_config()
            config["cached_bv"] = bv
            return self.save_config(config)
        except Exception:
            return False

    @property
    def bbdown_path(self):
        """获取BBDown路径"""
        return self.load_config().get("bbdown_path", "")

    @property
    def save_path(self):
        """获取保存路径"""
        return self.load_config().get("save_path", "")

    @property
    def is_login(self):
        """获取登录状态"""
        return self.load_config().get("is_login", False)

    @property
    def need_login(self):
        """获取是否需要登录才能下载"""
        return self.load_config().get("need_login", False)

    @property
    def suffix(self):
        """获取命令后缀"""
        return self.load_config().get("suffix", "")

    def get_config(self):
        """获取完整配置"""
        return self.load_config()

    def get_local_bbdown_path(self):
        """获取配置文件目录中的BBDown路径"""
        return os.path.join(os.path.dirname(self.config_file), "BBDown.exe")

    def copy_bundled_bbdown(self):
        """复制打包的BBDown到配置目录"""
        try:
            # 获取程序打包后的资源目录中的BBDown.exe路径
            if hasattr(sys, '_MEIPASS'):  # 判断是否是打包后的环境
                bundled_path = os.path.join(sys._MEIPASS, "BBDown.exe")
            else:
                # 开发环境下的路径
                bundled_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "BBDown.exe")
                
            if os.path.exists(bundled_path):
                local_path = self.get_local_bbdown_path()
                if not os.path.exists(local_path):
                    import shutil
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    shutil.copy2(bundled_path, local_path)
                    return True
        except Exception as e:
            print(f"复制BBDown.exe失败: {e}")
        return False

    def initialize_bbdown(self):
        """初始化BBDown路径并更新配置"""
        # 获取有效的BBDown路径
        bbdown_path = get_bbdown_path()
        
        if bbdown_path:
            # 更新配置文件中的BBDown路径
            self.update_bbdown_path(bbdown_path)
            return True
            
        # 如果没有找到，尝试复制打包的资源
        if self.copy_bundled_bbdown():
            local_path = self.get_local_bbdown_path()
            self.update_bbdown_path(local_path)
            return True
        
        return False

def get_executable_dir():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 如果是普通的 Python 脚本
        return os.path.dirname(os.path.abspath(__file__))

def get_bbdown_path():
    """
    获取BBDown.exe的路径，按以下优先级：
    1. 配置目录下的BBDown.exe
    2. 程序目录下的BBDown.exe
    3. 程序目录/tools/下的BBDown.exe
    注意：不使用临时目录中的BBDown.exe
    """
    # 获取配置目录路径
    config_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "BVDownloader")
    config_bbdown = os.path.join(config_dir, "BBDown.exe")
    
    # 获取exe程序主目录
    exe_dir = get_executable_dir()
    print(f"程序主目录: {exe_dir}")
    
    # 开发环境
    program_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    
    # 定义检查路径列表（按优先级）
    paths_to_check = [
        config_bbdown,  # 配置目录
        os.path.join(exe_dir, "BBDown.exe"),  # 程序目录
        os.path.join(exe_dir, "bbdown.exe"),
        os.path.join(exe_dir, "tools", "BBDown.exe"),  # exe子目录
        os.path.join(exe_dir, "tools", "bbdown.exe"),
        os.path.join(program_dir, "BBDown.exe"),#开发者环境目录
        os.path.join(program_dir, "tools", "BBDown.exe")
    ]

    # 检查配置目录中是否存在BBDown.exe
    if os.path.exists(config_bbdown):
        print(f"使用配置目录中的BBDown.exe: {config_bbdown}")
        return config_bbdown

    # 检查其他路径
    for path in paths_to_check[1:]:  # 跳过配置目录路径
        if os.path.exists(path):
            if not (hasattr(sys, '_MEIPASS') and sys._MEIPASS in path):  # 排除临时目录
                print(f"找到BBDown.exe: {path}")
                return path
            else:
                print(f"跳过临时目录中的BBDown.exe: {path}")

    print("未找到BBDown.exe")
    return ""

def save_config(config):
    """
    保存配置到config.json文件
    """
    try:
        config_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "BVDownloader", "bvconfig.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        print(f"配置已保存到: {config_path}")
    except Exception as e:
        print(f"保存配置失败: {str(e)}")

def load_config():
    """
    从config.json加载配置，如果文件不存在则返回默认配置
    """
    try:
        config_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "BVDownloader", "bvconfig.json")
        if not os.path.exists(config_path):
            print(f"配置文件不存在，将创建默认配置: {config_path}")
            #default_config = {"bbdown_path": "", "cached_bv": "BVaaaabbddee123"}
            default_config = {
            "bbdown_path": "",
            "cached_bv": "BVaaaabbddee123",
            "suffix": " --show-all --dfn-priority \"<杜比视界,8K 超高清,HDR 真彩,4K 超清,1080P 60帧,1080P 高码率,1080P 高清,720P 高清,480P 清晰,360P 流畅>\" --download-danmaku -F \"<videoTitle>[<ownerName>][<dfn><fps>][<bvid>][P<pageNumber>_<pageTitle>]\" -p ALL --save-archives-to-file --skip-ai=false --delay-per-page=2 --work-dir ",
            "is_login": False,
            "need_login": True,
            "save_path": os.path.join(os.path.expanduser("~"), "Desktop", "BVDownloader")
        }
            save_config(default_config)
            return default_config
            
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            print(f"已加载配置文件: {config_path}")
            return config
    except Exception as e:
        print(f"加载配置失败: {str(e)}")
        return {"bbdown_path": "", "cached_bv": "BVaaaabbddee123"}

# 程序启动时，自动获取并保存BBDown路径
config = load_config()
bbdown_path = get_bbdown_path()
if bbdown_path != config.get("bbdown_path", ""):
    print(f"更新BBDown路径: {bbdown_path}")
    config["bbdown_path"] = bbdown_path
    save_config(config)