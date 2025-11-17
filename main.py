"""
TikTok 直播监控器 - 主入口

这个脚本提供了快速启动监控器的命令行接口。
"""

import argparse
import sys

from tiktok_monitor import LiveCollector, MonitorConfig


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="TikTok 直播监控器 - 采集直播间实时数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 监控用户 tkb_no_kyoi，默认 60 秒
  python main.py tkb_no_kyoi

  # 监控 5 分钟，每 30 秒采集一次
  python main.py tkb_no_kyoi --duration 300 --interval 30

  # 单次采集
  python main.py tkb_no_kyoi --single

  # 使用环境变量配置
  export OUTPUT_DIR=./data
  python main.py tkb_no_kyoi
        """,
    )

    # 位置参数
    parser.add_argument(
        "username",
        help="TikTok 用户名（例如: tkb_no_kyoi）",
    )

    # 可选参数
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=60,
        help="监控时长（秒），默认 60",
    )

    parser.add_argument(
        "-i", "--interval",
        type=int,
        default=10,
        help="采集间隔（秒），默认 10",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="使用 headless 模式（不推荐，可能被检测）",
    )

    parser.add_argument(
        "--single",
        action="store_true",
        help="只采集一次，不进行持续监控",
    )

    # 解析参数
    args = parser.parse_args()

    # 创建配置
    config = MonitorConfig(
        username=args.username,
        headless=args.headless,
        monitor_duration=args.duration,
        collect_interval=args.interval,
    )

    # 创建采集器
    collector = LiveCollector(config)

    # 运行
    try:
        if args.single:
            collector.run_single_collect()
        else:
            collector.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
