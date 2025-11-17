"""
异常类定义
"""


class TikTokMonitorError(Exception):
    """TikTok 监控器基础异常"""

    pass


class BrowserError(TikTokMonitorError):
    """浏览器相关异常"""

    pass


class ParserError(TikTokMonitorError):
    """解析相关异常"""

    pass


class StorageError(TikTokMonitorError):
    """存储相关异常"""

    pass


class ConfigError(TikTokMonitorError):
    """配置相关异常"""

    pass


class CollectionError(TikTokMonitorError):
    """采集相关异常"""

    pass
