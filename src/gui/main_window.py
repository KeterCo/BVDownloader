import tkinter as tk
from tkinter import scrolledtext, filedialog
import threading
import os
import time
import subprocess
from ..core.downloader import VideoDownloader
from ..utils.logger import VideoLogger
from ..utils.config import Config
from queue import Queue, Empty
from ..utils.logger import LogLevel

class BilibiliDownloaderGUI:
    

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("哔哩哔哩视频下载器（BV号）")
        
        # 设置最小窗口尺寸
        self.root.minsize(750, 500)  # 设置最小宽度800，高度600
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 初始化窗口组件
        self.config = Config()
        self.logger = VideoLogger()
        self.downloader = VideoDownloader(self.logger)
        
        # 添加任务队列
        self.task_queue = Queue()
        # 添加下载线程
        self.download_thread = None
        # CD状态
        self.download_cooldown = False
        
        # 添加UI更新队列
        self.ui_update_queue = Queue()
        # 启动UI更新处理器
        self._start_ui_updater()

        self._init_ui()
        # 启动任务处理线程
        self._start_task_processor()
        
        # 等待窗口部件创建完成后再设置位置
        self.root.update_idletasks()
        
        # 获取窗口尺寸
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 计算位置（水平居中，垂直偏上10%）
        x = int((screen_width - window_width) / 2)  # 水平居中
        y = int(screen_height * 0.2)  # 屏幕高度的10%位置
        
        # 设置窗口位置
        self.root.geometry(f"+{x}+{y}")
        
        # 添加日志文件路径
        self.log_file = "bilibili_downloader.log"

        # 程序启动时检查登录状态
        self.logger.log_to_file("准备检查登录状态...", LogLevel.INFO)
        self.check_login_status_on_start()

    def _start_ui_updater(self):
        """启动UI更新处理器"""
        def process_ui_updates():
            try:
                while True:
                    # 检查队列中的更新请求
                    update_func = self.ui_update_queue.get_nowait()
                    update_func()
            except Empty:
                # 队列为空时，等待100ms后再次检查
                self.root.after(100, process_ui_updates)
                
        self.root.after(100, process_ui_updates)

    def update_ui(self, update_func):
        """安全地更新UI"""
        self.ui_update_queue.put(update_func)

    def _init_ui(self):
        # 添加登录区域（移到最上面）
        self._create_login_area()
        
        # 添加保存路径设置区域
        self._create_save_path_area()
        
        # 输入框
        self._create_input_area()
        # 下载按钮
        self._create_download_button()
        # 日志输出区
        self._create_log_area()

    def _create_login_area(self):
        """创建登录区域"""
        # 创建登录框架
        login_frame = tk.Frame(self.root)
        login_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 在框架中添加登录按钮和状态标签
        self.login_button = tk.Button(login_frame, text="登录", command=self.login)
        self.login_button.config(state=tk.DISABLED)
        self.login_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.login_status_label = tk.Label(login_frame, text="登录状态: 检查中...")
        self.login_status_label.pack(side=tk.LEFT)
        
        # 强制登录选项 (移到登录区域)
        self.need_login_var = tk.IntVar(value=int(self.config.need_login))
        login_checkbutton = tk.Checkbutton(
            login_frame,
            text="强制登录？勾选可阻止低画质下载。但必须登录才能下载。",
            variable=self.need_login_var,
            command=self._on_need_login_changed
        )
        login_checkbutton.pack(side=tk.LEFT, padx=(20, 0))

    def _create_save_path_area(self):
        # 创建保存路径框架
        path_frame = tk.Frame(self.root)
        path_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 添加标签
        path_label = tk.Label(path_frame, text="保存路径：")
        path_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 添加路径显示标签
        self.save_path_label = tk.Label(
            path_frame, 
            text=self.config.save_path,
            wraplength=400,  # 文本过长时换行
            justify=tk.LEFT
        )
        self.save_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加按钮框架
        button_frame = tk.Frame(path_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # 添加打开目录按钮
        open_dir_btn = tk.Button(
            button_frame,
            text="打开目录",
            command=self._open_save_dir
        )
        open_dir_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 添加修改路径按钮
        change_path_btn = tk.Button(
            button_frame,
            text="修改路径",
            command=self._change_save_path
        )
        change_path_btn.pack(side=tk.RIGHT, padx=(5, 0))

    def _create_input_area(self):
        label_input = tk.Label(self.root, text="输入BV号：")
        label_input.pack()
        
        # 创建输入框 - 将height从10增加到12
        self.text_input = scrolledtext.ScrolledText(
            self.root, width=100, height=12,  # 这里从10改为12
            undo=True  # 启用撤销功能
        )
        
        # 绑定快捷键
        self.text_input.bind('<Control-Key-z>', self._undo)
        self.text_input.bind('<Control-Key-y>', self._redo)
        self.text_input.bind('<Control-Key-Z>', self._redo)  # Shift+Ctrl+Z
        
        # 绑定右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="撤销", command=self._undo)
        self.context_menu.add_command(label="重做", command=self._redo)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制", command=self._copy)
        self.context_menu.add_command(label="粘贴", command=self._paste)
        self.context_menu.add_command(label="剪切", command=self._cut)
        
        self.text_input.bind('<Button-3>', self._show_context_menu)
        self.text_input.pack()

    def _create_download_button(self):
        self.download_button = tk.Button(
            self.root,
            text="开始下载",
            command=self._handle_download_click,
            state=tk.DISABLED
        )
        self.download_button.pack()

    def _create_log_area(self):
        label_output = tk.Label(self.root, text="输出日志：")
        label_output.pack()
        
        # 创建带标签的文本框 - 将height从10增加到11
        self.text_output = scrolledtext.ScrolledText(
            self.root, width=100, height=11,  # 这里从10改为11
            state=tk.DISABLED
        )
        self.text_output.pack()
        
        # 配置标签颜色
        self.text_output.tag_configure("success", foreground="green")
        self.text_output.tag_configure("error", foreground="red")
        self.text_output.tag_configure("info", foreground="black")
        
        # 注册日志回调
        self.logger.register_callback(self._update_log)

    def _update_log(self, message: str, level: LogLevel):
        """更新日志显示"""
        def _update():
            self.text_output.config(state=tk.NORMAL)
            
            # 根据日志级别选择颜色
            tag = {
                LogLevel.SUCCESS: "success",
                LogLevel.ERROR: "error",
                LogLevel.INFO: "info"
            }.get(level, "info")
            
            # 插入带颜色的文本
            self.text_output.insert(tk.END, message + "\n", tag)
            self.text_output.see(tk.END)
            self.text_output.config(state=tk.DISABLED)
            
        self.root.after(0, _update)

    def _on_need_login_changed(self):
        """处理是否需要登录的设置变更"""
        need_login = bool(self.need_login_var.get())
        if self.config.update_need_login(need_login):
            self.logger.log_to_window(f"强制登录设置已更新: {'启用' if need_login else '禁用'}")
            # 如果启用强制登录但当前未登录，提示用户
            if need_login and not self.config.is_login:
                self.logger.log_to_window("提醒：已启用强制登录但当前未登录，请先登录", LogLevel.ERROR)
        else:
            self.logger.log_to_window("强制登录设置更新失败", LogLevel.ERROR)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        self.context_menu.post(event.x_root, event.y_root)

    def _copy(self):
        """复制选中文本"""
        try:
            selected_text = self.text_input.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass  # 没有选中文本

    def _paste(self):
        """粘贴文本"""
        try:
            text = self.root.clipboard_get()
            self.text_input.insert("insert", text)
        except tk.TclError:
            pass  # 剪贴板为空

    def _cut(self):
        """剪切选中文本"""
        self._copy()
        try:
            self.text_input.delete("sel.first", "sel.last")
        except tk.TclError:
            pass  # 没有选中文本

    def _undo(self, event=None):
        """撤销操作"""
        try:
            self.text_input.edit_undo()
        except tk.TclError:
            pass
        return 'break'  # 阻止默认行为

    def _redo(self, event=None):
        """重做操作"""
        try:
            self.text_input.edit_redo()
        except tk.TclError:
            pass
        return 'break'  # 阻止默认行为

    def _handle_download_click(self):
        """处理下载按钮点击"""
        if self.download_cooldown:
            return
                
        self.download_cooldown = True
        self.download_button.config(state=tk.DISABLED)
        
        # 获取输入文本
        input_text = self.text_input.get("1.0", tk.END).strip()
        
        if not input_text:
            self.logger.log_to_window("错误：请输入BV号！", LogLevel.ERROR)
            self._start_cooldown_timer()
            return
        
        # 检查登录要求和状态
        if self.config.need_login:
            if not self.config.is_login:
                message = "您已勾选强制登录，需登录后才能下载。"
                self.logger.log_to_window(message, LogLevel.ERROR)
                self.logger.log_to_file(message, LogLevel.ERROR)
                self._start_cooldown_timer()
                return
            else:
                message = "已启用高画质下载模式。"
                self.logger.log_to_window(message, LogLevel.INFO)
                self.logger.log_to_file(message, LogLevel.INFO)
        else:
            message = "当前为低画质下载模式，您需要登录才能高画质下载。"
            self.logger.log_to_window(message, LogLevel.INFO)
            self.logger.log_to_file(message, LogLevel.INFO)
                
        # 清空日志显示
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)
        self.text_output.config(state=tk.DISABLED)
        
        # 在开始新的下载任务前重置统计
        self.logger.success_count = 0
        self.logger.failed_bvs = []
        self.logger.failed_reasons = {}
        
        # 将下载任务添加到队列
        self.task_queue.put(input_text)

    def _start_task_processor(self):
        """启动任务处理线程"""
        def process_tasks():
            while True:
                try:
                    input_text = self.task_queue.get()
                    bv_list = self.downloader.command_builder.extract_valid_bvs(input_text)
                    
                    if not bv_list:
                        self.logger.log_to_window("错误：未找到有效的BV号！", LogLevel.ERROR)
                        self.root.after(0, self._start_cooldown_timer)
                        continue
                        
                    self.logger.log_to_window(f"找到 {len(bv_list)} 个有效BV号，下载中...", LogLevel.INFO)
                    
                    for bv in bv_list:
                        self._download_single_video(bv)
                    
                    # 所有视频处理完成后，显示统计信息
                    self.logger.print_summary()
                    
                    # 启动CD
                    self.root.after(0, self._start_cooldown_timer)
                    
                except Exception as e:
                    self.logger.log_to_window(f"处理任务时出错: {str(e)}", LogLevel.ERROR)
                    self.root.after(0, self._start_cooldown_timer)
                finally:
                    self.task_queue.task_done()

        task_thread = threading.Thread(target=process_tasks, daemon=True)
        task_thread.start()

    def _download_single_video(self, bv: str):
        """下载单个视频"""
        try:
            # 如果启用了强制登录选项，先检查登录状态
            if self.need_login_var.get():
                if not self.config.is_login:
                    error_msg = "你启用了强制登录下载，但当前未登录。请先登录或取消勾选强制登录选项以低画质下载。"
                    self.logger.log_to_window(f"{bv} 下载失败！{error_msg}", LogLevel.ERROR)
                    self.logger.record_download_result(bv, False, error_msg)
                    return
            
            event = threading.Event()
            
            def callback(success, error_msg=None):
                if success:
                    self.logger.log_to_window(f"{bv} 下载成功！", LogLevel.SUCCESS)
                    self.logger.record_download_result(bv, True)
                    # 下载成功后更新缓存的BV号
                    if len(bv) == 12 and bv.startswith('BV'):  # 确保是有效的BV号
                        self.config.update_cached_bv(bv)
                else:
                    # 提取失败原因
                    if error_msg:
                        if "must to be 12 char" in error_msg:
                            error_msg = "BV号长度不正确"
                        elif "未找到此" in error_msg:
                            error_msg = "原视频已被删除。"
                        else:
                            error_msg = "其他原因"
                    
                    error_message = f"{bv} 下载失败！{error_msg if error_msg else ''}"
                    self.logger.log_to_window(error_message, LogLevel.ERROR)
                    self.logger.record_download_result(bv, False, error_msg)
                event.set()
            
            # 只记录到本地日志，不显示在窗口
            self.logger.log_to_file(f"{bv} 正在处理...")
            self.downloader.start_download(bv, self.config.is_login, callback)
            event.wait()
            
        except Exception as e:
            error_msg = str(e)
            self.logger.log_to_window(f"{bv} 下载出错: {error_msg}", LogLevel.ERROR)
            self.logger.record_download_result(bv, False, error_msg)

    def _start_cooldown_timer(self):
        """启动CD计时器"""
        def cooldown():
            time.sleep(1)  # 1秒CD
            self.download_cooldown = False
            self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
        
        # 创建CD计时线程
        cooldown_thread = threading.Thread(target=cooldown, daemon=True)
        cooldown_thread.start()

    def _change_save_path(self):
        """处理修改保存路径的操作"""
        initial_dir = self.config.save_path if os.path.exists(self.config.save_path) else "/"
        new_path = filedialog.askdirectory(
            title="选择保存路径",
            initialdir=initial_dir
        )
        
        if new_path:  # 用户选择了新路径
            # 转换路径格式（处理正反斜杠）
            new_path = new_path.replace("/", "\\")
            
            if self.config.update_save_path(new_path):
                # 更新显示的路径
                self.save_path_label.config(text=new_path)
                self.logger.log_to_window(f"保存路径已更新: {new_path}")
            else:
                self.logger.log_to_window("保存路径更新失败")

    def _open_save_dir(self):
        """打开保存目录"""
        try:
            if not self.config.save_path:
                self.logger.log_to_window("保存路径为空，请先设置有效的保存路径", LogLevel.ERROR)
                return
                
            # 如果目录不存在，尝试创建
            if not os.path.exists(self.config.save_path):
                try:
                    os.makedirs(self.config.save_path, exist_ok=True)
                    self.logger.log_to_window(f"已创建保存目录: {self.config.save_path}", LogLevel.SUCCESS)
                except Exception as e:
                    self.logger.log_to_window(f"创建目录失败: {str(e)}", LogLevel.ERROR)
                    return
            
            # 使用explorer打开目录
            subprocess.run(['explorer', self.config.save_path])
            
        except Exception as e:
            self.logger.log_to_window(f"打开目录失败: {str(e)}", LogLevel.ERROR)

    def check_login_status_on_start(self):
        
        """程序启动时检查登录状态"""
        def _check():
            self.download_button.config(state="disabled")
            self.logger.log_to_file("开始检查登录状态...", LogLevel.INFO)
            from src.utils.login import check_login_status
            from src.utils.config import load_config

            config = load_config()
            bbdown_path = config.get("bbdown_path", "")
            cached_bv = config.get("cached_bv", "BVaaaabbddee123")

            self.logger.log_to_file(f"BBDown路径: {bbdown_path}", LogLevel.INFO)
            self.logger.log_to_file(f"缓存的BV号: {cached_bv}", LogLevel.INFO)

            if not bbdown_path:
                self.logger.log_to_file("无法判断登录状态，无bbdown。", LogLevel.ERROR)
                self.update_ui(lambda: self.login_status_label.config(text="无法判断登录状态，无bbdown。"))
                self.download_button.config(state="normal")
                return

            self.logger.log_to_window("正在检查登录状态...", LogLevel.INFO)
            is_logged_in = check_login_status(bbdown_path, cached_bv)
            
            # 更新配置中的登录状态
            self.config.update_login_state(is_logged_in)
            
            if is_logged_in:
                self.update_ui(lambda: [
                    self.logger.log_to_window("登录状态检查：已登录", LogLevel.SUCCESS),
                    self.login_status_label.config(text="登录状态: 已登录"),
                    self.login_button.config(state="disabled")

                ])
            else:
                self.update_ui(lambda: [
                    self.logger.log_to_window("登录状态检查：未登录", LogLevel.INFO),
                    self.login_status_label.config(text="登录状态: 未登录"),
                    self.login_button.config(state="normal")
                ])
            self.download_button.config(state="normal")

        # 在新线程中异步检查登录状态
        self.logger.log_to_file("启动登录状态检查线程...", LogLevel.INFO)
        threading.Thread(target=_check, daemon=True).start()

    def login(self):
        """登录按钮回调函数"""
        from src.utils.login import loginmain
        from src.utils.config import load_config

        self.login_button.config(state="disabled")
        self.login_status_label.config(text="登录状态: 正在登录...")

        config = load_config()
        bbdown_path = config.get("bbdown_path", "")

        if not bbdown_path:
            self.logger.log_to_file("无法登录：BBDown路径未找到，BBDown文件丢失。", LogLevel.ERROR)
            self.logger.log_to_window("无法登录：BBDown路径未找到，BBDown文件丢失。", LogLevel.ERROR)
            self._update_login_ui(False)
            return

        self.logger.log_to_window("正在打开登录窗口...", LogLevel.INFO)

        # 直接在主线程调用loginmain，不要用线程
        def on_login_result(success):
            self.update_ui(lambda: self._handle_login_result(success))

        loginmain(bbdown_path, on_login_result)

    def _handle_login_result(self, success: bool):
        """处理登录结果"""
        self.config.update_login_state(success)
        self._update_login_ui(success)
        
        if success:
            self.logger.log_to_window("登录成功！", LogLevel.SUCCESS)
            self.login_status_label.config(text="登录状态: 已登录")
            self.login_button.config(state="disabled")
        else:
            self.logger.log_to_window("登录失败或取消", LogLevel.ERROR)
            self.login_status_label.config(text="登录状态: 未登录")
            self.login_button.config(state="normal")

    def _update_login_ui(self, is_logged_in: bool):
        """更新登录相关的UI组件"""
        if is_logged_in:
            self.login_status_label.config(text="登录状态: 已登录")
            self.login_button.config(state="disabled")
        else:
            self.login_status_label.config(text="登录状态: 未登录")
            self.login_button.config(state="normal")

    def run(self):
        """启动GUI"""
        self.root.mainloop()
