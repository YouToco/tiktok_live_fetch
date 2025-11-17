"""
配置管理模块
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def is_running_in_docker() -> bool:
    """检测是否在 Docker 容器中运行

    Returns:
        是否在容器中
    """
    # 方法 1: 检查 /.dockerenv 文件
    if os.path.exists("/.dockerenv"):
        return True

    # 方法 2: 检查 /proc/1/cgroup
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except Exception:
        pass

    # 方法 3: 检查环境变量
    if os.getenv("DOCKER_CONTAINER") or os.getenv("USE_XVFB"):
        return True

    return False


@dataclass
class MonitorConfig:
    """监控器配置"""

    # 目标直播间
    username: str
    live_url: Optional[str] = None

    # 浏览器选项
    window_size: tuple[int, int] = (1920, 1080)
    headless: bool = False  # 不推荐使用 headless，可能被检测

    # 自定义 Chrome 路径（可选）
    chrome_binary_path: Optional[str] = None  # Chrome 浏览器路径
    chromedriver_path: Optional[str] = None  # ChromeDriver 路径

    # 容器环境（自动检测）
    in_docker: bool = field(default_factory=is_running_in_docker)

    # 监控配置
    monitor_duration: int = 60  # 监控时长（秒）
    collect_interval: int = 10  # 采集间隔（秒）

    # 超时设置
    page_load_timeout: int = 30  # 页面加载超时（秒）
    implicit_wait: int = 10  # 隐式等待（秒）

    def __post_init__(self):
        """初始化后处理"""
        # 自动生成直播间 URL
        if not self.live_url:
            self.live_url = f"https://www.tiktok.com/@{self.username}/live"

        # 容器环境日志
        if self.in_docker:
            from .logger import logger

            logger.info("检测到容器环境，使用容器优化配置")
            if os.getenv("USE_XVFB"):
                logger.info("Xvfb 虚拟显示已启用")

    @classmethod
    def from_env(cls, username: str) -> "MonitorConfig":
        """从环境变量创建配置

        Args:
            username: TikTok 用户名

        Returns:
            配置对象
        """
        return cls(
            username=username,
            headless=os.getenv("HEADLESS", "false").lower() == "true",
            monitor_duration=int(os.getenv("MONITOR_DURATION", "60")),
            collect_interval=int(os.getenv("COLLECT_INTERVAL", "10")),
            chrome_binary_path=os.getenv("CHROME_BINARY_PATH"),
            chromedriver_path=os.getenv("CHROMEDRIVER_PATH"),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "username": self.username,
            "live_url": self.live_url,
            "window_size": self.window_size,
            "headless": self.headless,
            "chrome_binary_path": self.chrome_binary_path,
            "chromedriver_path": self.chromedriver_path,
            "in_docker": self.in_docker,
            "monitor_duration": self.monitor_duration,
            "collect_interval": self.collect_interval,
        }
