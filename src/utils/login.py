import sys
import os
import subprocess
import threading
import tkinter as tk
from PIL import Image, ImageTk
import time
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum, auto

# 全局状态标志和变量
login_success = False
login_fail = False
current_process = None
qr_label = None
refresh_button = None
cmd = []
root = None
current_qr_path = None
global_login_manager = None

class LoginEvent(Enum):
    QR_GENERATED = auto()
    QR_EXPIRED = auto()
    LOGIN_SUCCESS = auto()
    LOGIN_FAILED = auto()

@dataclass
class LoginMessage:
    event: LoginEvent
    data: dict = None

@dataclass
class LoginConfig:
    bbdown_path: str
    cached_bv: str

class LoginManager:
    def __init__(self):
        self.message_queue = Queue()
        self.root = None
        self.config = self._load_config()
    
    def _load_config(self) -> LoginConfig:
        """从配置文件加载登录配置"""
        from ..utils.config import load_config
        config_data = load_config()
        return LoginConfig(
            bbdown_path=config_data.get("bbdown_path", ""),
            cached_bv=config_data.get("cached_bv", "BVAAAA1A1A1A1A1")  # 默认值
        )
    
    def check_final_login_status(self) -> bool:
        """验证最终登录状态"""
        if not self.config.bbdown_path or not self.config.cached_bv:
            print("无法验证登录：缺少必要配置")
            return False
        try:
            return check_login_status(self.config.bbdown_path, self.config.cached_bv)
        except Exception as e:
            print(f"验证登录状态时出错: {e}")
            return False
    
    def send_message(self, event: LoginEvent, data: dict = None):
        self.message_queue.put(LoginMessage(event, data))

def is_absolute_path(path):
    return os.path.isabs(path)

def center_window(window):
    """窗口居中显示"""
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")

def check_and_cleanup_qr(qr_path):
    """检查二维码文件是否存在并清理过期文件"""
    if os.path.exists(qr_path):
        try:
            os.remove(qr_path)  # 尝试删除过期文件
            print(f"清理二维码文件成功: {qr_path}")
            return True
        except Exception as e:
            print(f"清理二维码文件失败: {e}")
    return False

def get_qr_path(bbdown_path):
    """获取二维码文件路径"""
    return os.path.join(os.path.dirname(bbdown_path), "qrcode.png")

def get_possible_qr_paths():
    """获取可能的二维码文件路径列表，按优先级排序"""
    # 获取BBDown路径并推导主目录
    bbdown_path = cmd[0] if cmd else ""  # 使用全局cmd变量获取BBDown路径
    if not bbdown_path:
        print("警告：无法获取BBDown路径")
        return []

    # 获取BBDown所在目录和主目录
    bbdown_dir = os.path.dirname(os.path.abspath(bbdown_path))
    main_dir = os.path.dirname(bbdown_dir) if "tools" in bbdown_dir.lower() else bbdown_dir
    
    print(f"BBDown目录: {bbdown_dir}")
    print(f"主程序目录: {main_dir}")
    
    # 按优先级返回可能的二维码路径
    paths = [
        os.path.join(main_dir, "qrcode.png"),      # 主目录下的二维码
        os.path.join(bbdown_dir, "qrcode.png"),    # BBDown目录下的二维码
        os.path.join(os.path.expanduser("~"), "qrcode.png")  # 用户主目录下的二维码
    ]
    
    # 打印搜索路径
    for path in paths:
        print(f"将检查二维码路径: {path}")
        
    return paths

def find_qr_file():
    """查找存在的二维码文件，返回找到的路径或None"""
    for path in get_possible_qr_paths():
        if os.path.exists(path):
            print(f"找到二维码文件: {path}")
            return path
    return None

def cleanup_qr_files(reason=""):
    """清理所有可能位置的二维码文件
    reason: 清理原因，用于日志记录
    """
    for path in get_possible_qr_paths():
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"已删除二维码文件({reason}): {path}")
            except Exception as e:
                print(f"删除二维码文件失败({path}): {e}")

def show_qr():
    """显示二维码"""
    global qr_label, qr_photo, root
    
    # 先清除现有内容
    for widget in root.winfo_children():
        widget.destroy()

    # 配置窗口
    root.deiconify()
    root.geometry("400x450")
    
    # 查找二维码文件
    qr_path = find_qr_file()
    if not qr_path:
        print("二维码文件不存在")
        tk.Label(root, text="二维码文件不存在或已过期", font=("", 12), fg="red").pack(pady=20)
        return

    try:
        # 打开并调整图片大小
        img = Image.open(qr_path)
        img = img.resize((300, 300), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
        
        # 全局保存PhotoImage对象
        global qr_photo
        qr_photo = ImageTk.PhotoImage(img)

        # 显示图片
        frame = tk.Frame(root)
        frame.pack(expand=True, fill="both", padx=20, pady=20)
        qr_label = tk.Label(frame, image=qr_photo)
        qr_label.pack(expand=True)
        
        # 添加提示文本
        tk.Label(root, text="请使用哔哩哔哩APP扫描二维码登录", font=("", 12)).pack(pady=10)
        
        # 居中并刷新
        center_window(root)
        print(f"二维码显示成功，使用路径: {qr_path}")

    except Exception as e:
        print(f"显示二维码失败: {e}")
        tk.Label(root, text=f"显示二维码失败: {e}", font=("", 12), fg="red").pack(pady=20)

def expire_qr():
    """处理二维码过期"""
    global qr_label, refresh_button, root, global_login_manager
    
    # 清理过期的二维码文件
    cleanup_qr_files("二维码过期")
    
    if qr_label:
        qr_label.destroy()
        qr_label = None
    
    # 添加过期提示标签
    expire_label = tk.Label(root, text="二维码已过期", font=("", 12))
    expire_label.pack(pady=10)
    
    # 添加刷新按钮
    refresh_button = tk.Button(
        root,
        text="点击重新获取二维码",
        command=lambda: [expire_label.destroy(), restart_login(global_login_manager)]
    )
    refresh_button.pack(pady=10)
    
    center_window(root)
    
    # 终止当前进程
    if current_process and current_process.poll() is None:
        current_process.terminate()

def countdown_and_close(remaining, success_label):
    """倒计时关闭窗口"""
    if remaining > 0:
        success_label.config(text=f"登录成功\n{remaining}秒后自动关闭")
        root.after(1000, countdown_and_close, remaining - 1, success_label)
    else:
        root.destroy()

def success_login():
    global login_success, root, qr_label
    login_success = True
    
    # 清除现有内容
    for widget in root.winfo_children():
        widget.destroy()
    
    # 创建成功提示标签
    success_label = tk.Label(
        root,
        text="登录成功\n3秒后自动关闭",
        font=("黑体", 24, "bold"),
        fg="green"
    )
    success_label.pack(expand=True)
    
    # 开始3秒倒计时
    countdown_and_close(3, success_label)
    
    # 居中显示窗口
    center_window(root)
    
    # 确保窗口可见
    root.deiconify()

def restart_login(login_manager):
    global qr_label, refresh_button
    if qr_label:
        qr_label.destroy()
    if refresh_button:
        refresh_button.destroy()
    start_login(login_manager)

def on_closing():
    """处理窗口关闭事件"""
    global login_fail, current_process, root, login_success
    login_fail = True
    login_success = False
    
    # 清理二维码文件
    cleanup_qr_files("窗口关闭")
    
    if current_process and current_process.poll() is None:
        current_process.terminate()
    root.destroy()

def on_login_failed(error_msg: str):
    """处理登录失败的情况"""
    if root:
        tk.Label(root, text=f"登录失败: {error_msg}", font=("", 12), fg="red").pack(pady=20)
        root.after(2000, root.destroy)  # 2秒后关闭窗口

def monitor_output(login_manager):
    """监控BBDown输出"""
    while True:
        line = current_process.stdout.readline()
        if not line:
            if current_process.poll() is not None:
                break
            continue
        
        line = line.strip()
        if "██" not in line:  # 过滤掉二维码ASCII图案
            print(f"[DEBUG] BBDown output: {line}")

        if "生成二维码成功" in line:
            time.sleep(0.5)  # 等待文件写入完成
            login_manager.send_message(LoginEvent.QR_GENERATED)
            
        elif "二维码已过期" in line:
            login_manager.send_message(LoginEvent.QR_EXPIRED)
            
        elif "登录成功" in line:
            time.sleep(0.5)
            if login_manager.check_final_login_status():
                login_manager.send_message(LoginEvent.LOGIN_SUCCESS)
                # 登录成功后清理二维码文件
                cleanup_qr_files("登录成功")
            else:
                login_manager.send_message(LoginEvent.LOGIN_FAILED, {"error": "登录验证失败"})
                cleanup_qr_files("登录失败")

            #login_manager.check_login_status_on_start()

def start_login(login_manager):
    global current_process, cmd, root, qr_label, refresh_button, login_success, login_fail
    login_success = False
    login_fail = False
    if qr_label:
        qr_label.destroy()
    if refresh_button:
        refresh_button.destroy()
    root.withdraw()
    
    try:
        # 打印完整的登录命令
        cmd_str = " ".join(cmd)
        print(f"执行登录命令: {cmd_str}")
        
        # 创建 STARTUPINFO 对象来隐藏控制台窗口
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        # 启动BBDown进程
        current_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True, 
            bufsize=1,
            startupinfo=startupinfo
        )
        
        # 启动监控线程 - 这部分之前漏掉了
        t = threading.Thread(target=monitor_output, args=(login_manager,), daemon=True)
        t.start()
        print("登录监控线程已启动")
        
    except Exception as e:
        print("启动登录进程失败:", e)
        login_fail = True
        root.destroy()
        return
def loginmain(abs_bbdown_path, on_login_result=None):
    global cmd, root, global_login_manager, login_success
    
    # 重置登录状态
    login_success = False
    
    # 创建登录管理器
    login_manager = LoginManager()
    global_login_manager = login_manager
    
    # 保持使用 Toplevel
    root = tk.Toplevel()
    login_manager.root = root
    root.title("BBDown 登录")
    root.geometry("400x450")
    
    sys.argv = [
        'login.py',
        abs_bbdown_path
    ]
    if len(sys.argv) < 2:
        print("用法: python script.py <BBDown 可执行文件路径>")
        sys.exit(1)
    path = sys.argv[1]

    # 设置全局cmd变量
    cmd = [path, "login"]
    print(f"设置登录命令: {' '.join(cmd)}")

    # 设置窗口关闭处理
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 先显示一个"正在获取二维码..."的消息
    loading_label = tk.Label(root, text="正在获取二维码...", font=("", 14))
    loading_label.pack(pady=20)
    root.update()
    
    # 居中显示窗口
    center_window(root)
    
    # 使窗口可见，与后面的withdraw对应
    root.update_idletasks()
    
    # 隐藏窗口，等待二维码生成
    root.withdraw()
    
    def process_messages():
        try:
            while True:
                try:
                    msg = login_manager.message_queue.get_nowait()
                    if msg.event == LoginEvent.QR_GENERATED:
                        root.after(0, show_qr)
                    elif msg.event == LoginEvent.QR_EXPIRED:
                        root.after(0, expire_qr)
                    elif msg.event == LoginEvent.LOGIN_SUCCESS:
                        root.after(0, success_login)
                        if on_login_result:
                            on_login_result(True)
                    elif msg.event == LoginEvent.LOGIN_FAILED:
                        error_msg = msg.data.get("error", "未知错误") if msg.data else "未知错误"
                        print(f"登录失败: {error_msg}")
                        root.after(0, lambda: on_login_failed(error_msg))
                        if on_login_result:
                            on_login_result(False)
                except Empty:
                    break
        finally:
            if root.winfo_exists():
                root.after(100, process_messages)
    
    # 启动消息处理
    root.after(0, process_messages)
    
    # 启动登录流程
    start_login(login_manager)
    
    return login_success


def check_login_status(bbdown_path, bv):
    """
    检查登录状态，返回True表示已登录，False表示未登录。
    使用-info命令快速检查登录状态。
    """
    if not bbdown_path or not os.path.exists(bbdown_path):
        print("登录判断：配置文件中bbdown为空或不存在")
        return False
    try:
        # 构建命令
        bv = bv+"1"
        cmd = [bbdown_path, "-info", bv]
        cmd_str = " ".join(cmd)
        print(f"执行检测登录状态的命令: {cmd_str}")
        
        # 创建 STARTUPINFO 对象来隐藏控制台窗口
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # 使用-info命令快速检查登录状态，添加 startupinfo 参数
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3,
            startupinfo=startupinfo
        )
        output = result.stdout.lower()
        
        # 记录命令输出到日志
        print(f"命令输出:\n{result.stdout}")
        
        # 检查输出中是否包含未登录的提示
        if "尚未登录" in output or "未登录" in output:
            print(f"登录状态检查：未登录，BV号: {bv}")
            return False
            
        # 检查输出中是否包含登录成功的标志
        if "加载本地cookie" in output or "获取aid" in output:
            print(f"登录状态检查：已登录，BV号: {bv}")
            return True
            
        # 如果既没有未登录提示，也没有登录成功标志，默认为未登录
        print(f"登录状态检查：未登录（无法确定状态），BV号: {bv}")
        return False
        
    except subprocess.TimeoutExpired:
        print(f"登录状态检查超时，BV号: {bv}")
        return False
    except Exception as e:
        print(f"登录状态检查出错: {e}")
        return False

# loginresult_=False
# loginresult_=loginmain(r"D:\Softwares\BBDown_1.6.3_20240814_win-x64\bbdown.exe")
# print(loginresult_)

import re

# —— 测试示例 ——
# if __name__ == "__main__":
#     path = r"D:\Softwares\BBDown_1.6.3_20240814_win-x64\bbdown.exe"
#     bv   = "BV1232133213"
#     status = check_login_status(path, bv)
#     print("登录状态：", status)


# 测试地方：# 休息cmd
  #  cmd = [path, "--version"]
#   if os.path.exists(os.path.join(os.path.expanduser("~"), "qrcode.png")):
#                 root.after(0, show_qr)
# if not login_success and not expired_found:
#         pass
#         #login_fail = True
#         #root.after(0, root.destroy)