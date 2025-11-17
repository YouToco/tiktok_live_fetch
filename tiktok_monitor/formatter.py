"""
结果格式化工具模块
"""

from .models import MonitorSession, PageSnapshot


class ResultFormatter:
    """格式化采集结果，输出到控制台使用。"""

    @staticmethod
    def format_snapshot_summary(snapshot: PageSnapshot) -> str:
        lines = [
            f"📸 快照时间: {snapshot.timestamp}",
            f"  ├─ 视频元素: {'✅' if snapshot.has_video else '❌'}",
            f"  ├─ 检测状态: {'❌ 被检测' if snapshot.has_error_message else '✅ 正常'}",
            f"  ├─ 直播内容: {'✅' if snapshot.has_live_content else '❌'}",
        ]

        # 页面错误警告
        if snapshot.has_page_error:
            lines.append("  ├─ ⚠️  页面错误: 🚨 检测到页面问题！")
        
        # 验证码警告
        if snapshot.has_captcha:
            lines.append("  ├─ ⚠️  验证码: 🚨 检测到验证码！")

        lines.extend(
            [
                f"  ├─ 元素数量: {snapshot.element_count}",
                f"  └─ HTML 大小: {snapshot.html_size:,} 字节",
            ]
        )

        if snapshot.viewer_count:
            lines.insert(-1, f"  ├─ 观众数: {snapshot.viewer_count}")

        return "\n".join(lines)

    @staticmethod
    def format_session_summary(session: MonitorSession) -> str:
        lines = [
            "=" * 80,
            "📊 监控会话摘要",
            "=" * 80,
            f"用户名: @{session.username}",
            f"开始时间: {session.start_time}",
            f"结束时间: {session.end_time or '进行中'}",
            "",
            f"总快照数: {session.total_snapshots}",
            f"正常快照: {session.healthy_snapshots} ✅",
            f"异常快照: {session.error_snapshots} ❌",
        ]

        if session.snapshots:
            last_snapshot = session.snapshots[-1]
            lines.extend(
                [
                    "",
                    "最后状态:",
                    f"  - 检测状态: {'❌ 被检测' if last_snapshot.has_error_message else '✅ 未被检测'}",
                    f"  - 页面状态: {'❌ 错误' if last_snapshot.has_page_error else '✅ 正常'}",
                    f"  - 视频播放: {'✅ 是' if last_snapshot.has_video else '❌ 否'}",
                ]
            )

        return "\n".join(lines)

