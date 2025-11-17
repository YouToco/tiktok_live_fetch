"""
日志管理模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class Logger:
    """日志管理器"""

    _instance: Optional["Logger"] = None
    _initialized: bool = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化日志器"""
        if not self._initialized:
            self._setup_logger()
            self.__class__._initialized = True

    def _setup_logger(self):
        """配置日志器"""
        # 创建日志器
        self.logger = logging.getLogger("tiktok_monitor")
        self.logger.setLevel(logging.INFO)

        # 避免重复添加 handler
        if self.logger.handlers:
            return

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 格式化
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(console_handler)

    def add_file_handler(self, log_file: Path):
        """添加文件日志处理器

        Args:
            log_file: 日志文件路径
        """
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(message)

    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)

    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)

    def error(self, message: str):
        """错误日志"""
        self.logger.error(message)

    def exception(self, message: str):
        """异常日志（包含堆栈）"""
        self.logger.exception(message)


# 全局日志实例
logger = Logger()
