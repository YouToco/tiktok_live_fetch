"""
数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class PageSnapshot:
    """页面快照数据"""

    # 必需字段 (无默认值)
    timestamp: str
    url: str
    title: str
    has_video: bool
    has_error_message: bool
    has_live_content: bool
    element_count: int
    video_count: int
    html_size: int

    # 可选字段 (有默认值)
    is_live_ended: bool = False
    has_captcha: bool = False  # 是否出现验证码
    has_page_error: bool = False  # 🆕 是否出现页面错误（"我们遇到了一些问题"）
    viewer_count: Optional[int] = None
    initial_data: Optional[dict] = None
    body_text_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "url": self.url,
            "title": self.title,
            "has_video": self.has_video,
            "has_error_message": self.has_error_message,
            "has_page_error": self.has_page_error,
            "has_live_content": self.has_live_content,
            "is_live_ended": self.is_live_ended,
            "has_captcha": self.has_captcha,
            "element_count": self.element_count,
            "video_count": self.video_count,
            "html_size": self.html_size,
            "viewer_count": self.viewer_count,
            "has_initial_data": self.initial_data is not None,
            "body_text_preview": self.body_text_preview[:200],
        }

    @property
    def is_healthy(self) -> bool:
        """页面状态是否健康（未被检测）"""
        # 如果出现验证码，不健康
        if self.has_captcha:
            return False
        # 🆕 如果出现页面错误，不健康
        if self.has_page_error:
            return False
        # 如果直播已结束，这是一个有效的最终状态，也认为是健康的
        if self.is_live_ended:
            return True
        # 否则，健康的页面应该没有错误信息并且有视频元素
        return not self.has_error_message and self.has_video


@dataclass
class MonitorSession:
    """监控会话数据"""

    username: str
    live_url: str
    start_time: str
    end_time: Optional[str] = None

    # 采集的快照列表
    snapshots: list[PageSnapshot] = field(default_factory=list)

    # 会话统计
    total_snapshots: int = 0
    healthy_snapshots: int = 0
    error_snapshots: int = 0

    def add_snapshot(self, snapshot: PageSnapshot):
        """添加快照"""
        self.snapshots.append(snapshot)
        self.total_snapshots += 1

        if snapshot.is_healthy:
            self.healthy_snapshots += 1
        else:
            self.error_snapshots += 1

    def finish(self):
        """结束会话"""
        self.end_time = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "username": self.username,
            "live_url": self.live_url,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_snapshots": self.total_snapshots,
            "healthy_snapshots": self.healthy_snapshots,
            "error_snapshots": self.error_snapshots,
            "snapshots": [s.to_dict() for s in self.snapshots],
        }


@dataclass
class LiveRoomInfo:
    """直播间信息（从初始化数据解析）"""

    room_id: Optional[str] = None
    title: Optional[str] = None
    status: Optional[int] = None
    user_count: Optional[int] = None
    stream_url: Optional[str] = None

    # 主播信息
    owner_nickname: Optional[str] = None
    owner_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "room_id": self.room_id,
            "title": self.title,
            "status": self.status,
            "user_count": self.user_count,
            "stream_url": self.stream_url,
            "owner_nickname": self.owner_nickname,
            "owner_id": self.owner_id,
        }

    @classmethod
    def from_initial_data(cls, data: dict) -> "LiveRoomInfo":
        """从页面初始化数据解析

        Args:
            data: __UNIVERSAL_DATA_FOR_REHYDRATION__ 数据

        Returns:
            直播间信息对象
        """
        info = cls()

        try:
            # 尝试提取直播间信息
            default_scope = data.get("__DEFAULT_SCOPE__", {})

            # 直播详情
            live_detail = default_scope.get("webapp.live-detail", {})
            live_room_info = live_detail.get("liveRoomInfo", {})

            info.room_id = live_room_info.get("id")
            info.title = live_room_info.get("title")
            info.status = live_room_info.get("status")
            info.user_count = live_room_info.get("userCount")
            info.stream_url = live_room_info.get("streamUrl")

            # 用户详情
            user_detail = default_scope.get("webapp.user-detail", {})
            user_info = user_detail.get("userInfo", {})
            user_data = user_info.get("user", {})

            info.owner_nickname = user_data.get("nickname")
            info.owner_id = user_data.get("id")

        except Exception as e:
            # 解析失败不抛异常，返回空对象
            pass

        return info
