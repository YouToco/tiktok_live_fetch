"""
Web 服务器启动脚本

启动 Web 控制面板服务
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.api_server import MonitorAPIServer
from tiktok_monitor.logger import logger


def main():
    """启动 Web 服务器"""
    try:
        logger.info("=" * 80)
        logger.info("🌐 TikTok 直播监控 Web 控制台")
        logger.info("=" * 80)
        logger.info("📡 启动 Web 服务器...")
        logger.info("")
        logger.info("请在浏览器中访问:")
        logger.info("  👉 http://localhost:5001/")
        logger.info("  👉 http://localhost:5001/api (API 端点)")
        logger.info("")
        logger.info("=" * 80)
        print()

        # 创建并启动 API 服务器
        server = MonitorAPIServer(host="0.0.0.0", port=5001)
        server.start()

    except KeyboardInterrupt:
        print()
        logger.info("⚠️  用户中断服务")
    except Exception as e:
        logger.exception(f"服务器异常: {e}")
        raise


if __name__ == "__main__":
    main()
