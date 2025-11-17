"""
TikTok 直播监控器

基于 undetected-chromedriver 的 TikTok 直播数据采集工具
"""

__version__ = "1.0.0"
__author__ = "TikTok Monitor Team"
__all__ = [
    # 核心类
    "LiveCollector",
    "MonitorConfig",
    "BrowserManager",
    # 数据模型
    "PageSnapshot",
    "MonitorSession",
    "LiveRoomInfo",
    # 异常
    "TikTokMonitorError",
    "BrowserError",
    "ParserError",
    "StorageError",
    "ConfigError",
    "CollectionError",
    # 日志
    "logger",
    # Hooks
    "JavaScriptHook",
]

from .browser import BrowserManager
from .collector import LiveCollector
from .config import MonitorConfig
from .exceptions import (
    BrowserError,
    CollectionError,
    ConfigError,
    ParserError,
    StorageError,
    TikTokMonitorError,
)
from .hooks import JavaScriptHook
from .logger import logger
from .models import LiveRoomInfo, MonitorSession, PageSnapshot
