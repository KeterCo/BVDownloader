import tkinter as tk
from tkinter import scrolledtext

class LogTextArea(scrolledtext.ScrolledText):
    """日志文本区域组件"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state=tk.DISABLED)
        
    def append_log(self, message: str):
        """添加日志消息"""
        self.config(state=tk.NORMAL)
        self.insert(tk.END, message + '\n')
        self.see(tk.END)
        self.config(state=tk.DISABLED)

class DownloadButton(tk.Button):
    """下载按钮组件"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.default_text = kwargs.get('text', '开始下载')
        self.config(text=self.default_text)
    
    def set_downloading_state(self):
        """设置下载中状态"""
        self.config(state=tk.DISABLED, text="下载中...")
    
    def reset_state(self):
        """重置为默认状态"""
        self.config(state=tk.NORMAL, text=self.default_text)