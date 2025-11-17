"""
核心采集器模块
"""

import time
from datetime import datetime
from typing import Optional

from .browser import BrowserManager
from .captcha_handler import CaptchaHandler
from .config import MonitorConfig
from .exceptions import CollectionError
from .hooks import JavaScriptHook
from .logger import logger
from .models import MonitorSession
from .parser import PageParser
from .formatter import ResultFormatter


class LiveCollector:
    """TikTok 直播采集器

    这是整个系统的核心类，负责协调浏览器、解析器和存储器。
    采用分层架构，职责清晰，易于扩展。

    示例:
        >>> from tiktok_monitor import LiveCollector, MonitorConfig
        >>>
        >>> # 创建配置
        >>> config = MonitorConfig(username="tkb_no_kyoi")
        >>>
        >>> # 创建采集器并运行
        >>> collector = LiveCollector(config)
        >>> collector.run()
    """

    def __init__(self, config: MonitorConfig):
        """初始化采集器

        Args:
            config: 监控配置对象
        """
        self.config = config
        self.browser = BrowserManager(config)
        self.parser: Optional[PageParser] = None
        self.hooks: Optional[JavaScriptHook] = None
        self.captcha_handler: Optional[CaptchaHandler] = None
        self.session: Optional[MonitorSession] = None
        self.live_has_ended = False

        # 消息计数器（用于跟踪已处理的消息）
        self.processed_interaction_count = 0
        
        # 🆕 页面错误重试计数器
        self.page_error_retry_count = 0
        self.max_page_error_retries = 3  # 最多重试3次

        logger.debug(f"采集器初始化完成: {config.to_dict()}")

    def initialize(self):
        """初始化采集器

        启动浏览器，创建解析器和会话对象。

        Raises:
            CollectionError: 初始化失败时抛出
        """
        try:
            logger.info("=" * 80)
            logger.info("🚀 TikTok 直播采集器")
            logger.info("=" * 80)
            logger.info(f"目标用户: @{self.config.username}")
            logger.info(f"直播间地址: {self.config.live_url}")
            logger.info(f"监控时长: {self.config.monitor_duration} 秒")
            logger.info(f"采集间隔: {self.config.collect_interval} 秒")

            # 启动浏览器
            self.browser.start()

            # 创建解析器
            self.parser = PageParser(self.browser.driver)
            logger.debug("解析器创建成功")

            # 创建会话
            self.session = MonitorSession(
                username=self.config.username,
                live_url=self.config.live_url,
                start_time=datetime.now().isoformat(),
            )
            logger.debug("会话创建成功")

        except Exception as e:
            error_msg = f"初始化失败: {e}"
            logger.error(error_msg)
            raise CollectionError(error_msg) from e

    def prepare(self):
        """准备工作：访问首页和直播间

        Raises:
            CollectionError: 准备失败时抛出
        """
        try:
            logger.info("=" * 80)
            logger.info("📋 准备阶段")
            logger.info("=" * 80)

            # 访问直播间
            self.browser.visit_live_room()

            # 安装 JavaScript Hooks
            logger.info("正在安装 JavaScript Hooks...")
            self.hooks = JavaScriptHook(self.browser.driver)

            # 安装所有 Hook
            if self.hooks.install_all_hooks():
                logger.info("✅ JavaScript Hooks 安装成功")
            else:
                logger.warning("⚠️  部分 JavaScript Hooks 安装失败，但不影响基本采集功能")

            # 注入数据提取器
            if self.hooks.inject_data_extractor():
                logger.info("✅ 数据提取器注入成功")

        except Exception as e:
            error_msg = f"准备阶段失败: {e}"
            logger.error(error_msg)
            raise CollectionError(error_msg) from e

    def collect_once(self) -> bool:
        """执行一次数据采集

        Returns:
            是否采集成功（页面状态正常）

        Raises:
            CollectionError: 采集失败时抛出
        """
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            logger.info(f"📸 采集快照 [{current_time}]")

            # 解析页面创建快照
            snapshot = self.parser.create_snapshot()

            # 🆕 检测页面错误并处理（"我们遇到了一些问题"）
            if snapshot.has_page_error:
                print()
                print("=" * 80)
                print("⚠️  页面错误检测")
                print("=" * 80)
                print("检测到页面显示：我们遇到了一些问题，很抱歉造成不便")
                print()
                
                if self.page_error_retry_count < self.max_page_error_retries:
                    self.page_error_retry_count += 1
                    logger.warning(f"尝试刷新页面修复... (尝试 {self.page_error_retry_count}/{self.max_page_error_retries})")
                    print(f"🔄 正在刷新页面... (尝试 {self.page_error_retry_count}/{self.max_page_error_retries})")
                    
                    # 刷新页面
                    self.browser.driver.refresh()
                    time.sleep(5)  # 等待页面加载
                    
                    # 重新安装 Hook
                    if self.hooks:
                        self.hooks.install_all_hooks()
                        self.hooks.inject_data_extractor()
                    
                    print("✅ 页面已刷新，重新采集...")
                    print("=" * 80)
                    print()
                    
                    # 递归重试
                    return self.collect_once()
                else:
                    logger.error(f"页面错误重试次数已达上限 ({self.max_page_error_retries} 次)，停止采集")
                    print(f"❌ 页面刷新失败，已重试 {self.max_page_error_retries} 次")
                    print("=" * 80)
                    print()
                    return False
            
            # 如果页面正常，重置错误计数器
            if not snapshot.has_page_error:
                self.page_error_retry_count = 0

            # 检测验证码并处理
            if snapshot.has_captcha:
                print()
                print("=" * 80)
                print("🚨 验证码告警！")
                print("=" * 80)
                print("⚠️  检测到 TikTok 验证码弹窗！")
                print()

                # 尝试处理验证码
                if self._handle_captcha():
                    print("✅ 验证码已成功处理！")
                    print("=" * 80)
                    print()
                    # 验证码解决后，重新采集一次确认
                    return self.collect_once()
                else:
                    print("❌ 验证码处理失败或超时")
                    print("=" * 80)
                    print()
                    logger.warning("验证码处理失败，停止采集")
                    return False

            # 添加到会话
            self.session.add_snapshot(snapshot)

            # 打印摘要
            summary = ResultFormatter.format_snapshot_summary(snapshot)
            print(summary)
            print()

            # 检查直播是否已结束
            if snapshot.is_live_ended:
                logger.info("🔴 直播已结束，停止采集。")
                self.live_has_ended = True
                return False  # 返回 False 表示停止

            return snapshot.is_healthy

        except Exception as e:
            error_msg = f"采集失败: {e}"
            logger.error(error_msg)
            raise CollectionError(error_msg) from e

    def _handle_captcha(self, timeout: int = 300) -> bool:
        """处理验证码

        启动 API 服务器，等待用户通过前端界面点击验证码。

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功处理验证码
        """
        try:
            logger.info("开始处理验证码...")

            # 创建验证码处理器
            if not self.captcha_handler:
                self.captcha_handler = CaptchaHandler(
                    self.browser.driver,
                    get_interactions_callback=lambda: self.hooks.get_live_interactions() if self.hooks else []
                )

            # 重置状态
            self.captcha_handler.reset()

            # 捕获验证码图片
            if not self.captcha_handler.capture_captcha_image():
                logger.error("捕获验证码图片失败")
                return False

            # 启动 API 服务器（如果还未启动）
            if not self.captcha_handler.api_server_thread or not self.captcha_handler.api_server_thread.is_alive():
                self.captcha_handler.start_api_server(port=5000)

            # 显示提示信息
            print("📡 验证码处理 API 已启动")
            print()
            print("请在浏览器中打开前端界面进行验证码点击：")
            print()
            print("  API 端点：")
            print("  - GET  http://localhost:5000/api/captcha         (获取验证码图片)")
            print("  - POST http://localhost:5000/api/captcha/click   (提交点击坐标)")
            print("  - GET  http://localhost:5000/api/captcha/status  (查询状态)")
            print()
            print(f"⏳ 等待验证码处理（超时: {timeout}秒）...")
            print()

            # 等待用户解决验证码
            solved = self.captcha_handler.wait_for_solution(timeout)

            if solved:
                logger.info("验证码处理成功")
                # 等待几秒让页面更新
                time.sleep(3)
                return True
            else:
                logger.warning("验证码处理超时")
                return False

        except Exception as e:
            logger.error(f"处理验证码时出错: {e}")
            return False

    def process_live_interactions(self):
        """处理并显示实时直播互动

        从 Hooks 获取新的 DOM 互动（弹幕、礼物等），并实时输出到控制台。
        """
        if not self.hooks:
            return

        try:
            # 获取所有直播互动
            all_interactions = self.hooks.get_live_interactions()
            new_interactions = all_interactions[self.processed_interaction_count :]

            # 处理新的互动
            for interaction in new_interactions:
                self._display_interaction(interaction)

            # 更新计数器
            self.processed_interaction_count = len(all_interactions)

        except Exception as e:
            logger.debug(f"处理实时互动时出错: {e}")

    def _display_interaction(self, interaction: dict):
        """显示直播互动

        Args:
            interaction: 互动数据字典
        """
        try:
            timestamp = interaction.get("timestamp", "")
            interaction_type = interaction.get("type", "")
            username = interaction.get("username", "")
            content = interaction.get("content", "")

            # 提取时间（只保留时:分:秒）
            time_str = timestamp[11:19] if len(timestamp) >= 19 else timestamp

            # 根据类型显示不同的图标和格式
            if interaction_type == "chat":
                # 弹幕消息
                print(f"💬 [{time_str}] {username}: {content}")

            elif interaction_type == "gift":
                # 礼物消息
                print(f"🎁 [{time_str}] 礼物: {content}")

            elif interaction_type == "like":
                # 点赞
                print(f"❤️  [{time_str}] {content}")

            elif interaction_type == "follow":
                # 关注
                print(f"➕ [{time_str}] {content}")

            elif interaction_type == "share":
                # 分享
                print(f"🔗 [{time_str}] {content}")

            elif interaction_type == "join":
                # 进入直播间
                print(f"👋 [{time_str}] {content}")

            else:
                # 其他类型
                if content:
                    print(f"📡 [{time_str}] {interaction_type}: {content}")

        except Exception as e:
            logger.debug(f"显示互动失败: {e}")

    def monitor(self):
        """执行持续监控

        按照配置的时长和间隔持续采集数据。

        Raises:
            CollectionError: 监控失败时抛出
        """
        logger.info("=" * 80)
        logger.info(
            f"⏱️  开始监控（时长: {self.config.monitor_duration}s，快照间隔: {self.config.collect_interval}s）"
        )
        logger.info("=" * 80)
        logger.info("📺 实时互动监控已启动（按 Ctrl+C 停止）")
        logger.info("=" * 80)
        print()

        start_time = time.time()
        last_collect_time = 0

        try:
            while time.time() - start_time < self.config.monitor_duration:
                elapsed = time.time() - start_time

                # 到达采集间隔（保存快照）
                if elapsed - last_collect_time >= self.config.collect_interval:
                    print()  # 换行，避免快照信息和进度条混在一起
                    if not self.collect_once():
                        # 直播已结束或采集不健康，停止监控
                        break
                    last_collect_time = elapsed
                    print()  # 再换一行

                # 实时检查互动（每次循环都检查）
                self.process_live_interactions()

                # 显示进度（每秒更新一次）
                remaining = int(self.config.monitor_duration - elapsed)
                print(f"\r⏳ 监控中... 剩余 {remaining}s  ", end="", flush=True)

                time.sleep(0.2)  # 每 0.2 秒检查一次，提高实时性

            print()
            print()
            logger.info("✅ 监控完成")

        except KeyboardInterrupt:
            print()
            print()
            logger.warning("⚠️  用户中断监控")

        except Exception as e:
            error_msg = f"监控过程出错: {e}"
            logger.error(error_msg)
            raise CollectionError(error_msg) from e

    def finalize(self):
        """完成采集，保存结果

        Raises:
            CollectionError: 完成阶段失败时抛出
        """
        try:
            logger.info("=" * 80)
            logger.info("💾 保存结果")
            logger.info("=" * 80)

            # 结束会话
            self.session.finish()

            # 打印会话摘要
            print()
            summary = ResultFormatter.format_session_summary(self.session)
            print(summary)

        except Exception as e:
            error_msg = f"完成阶段失败: {e}"
            logger.error(error_msg)
            raise CollectionError(error_msg) from e

    def cleanup(self):
        """清理资源

        关闭浏览器，释放资源。
        """
        if self.browser:
            self.browser.close()

    def run(self):
        """运行完整的采集流程

        这是最简单的使用方式，执行完整的采集流程。
        包括：初始化 → 准备 → 采集 → 监控 → 完成 → 清理

        Raises:
            CollectionError: 流程执行失败时抛出
        """
        try:
            # 初始化
            self.initialize()

            # 准备
            self.prepare()

            # 立即采集第一个快照
            logger.info("=" * 80)
            logger.info("📊 初始数据采集")
            logger.info("=" * 80)
            print()
            self.collect_once()

            # 如果第一次采集就发现直播已结束，则不进入监控模式
            if not self.live_has_ended:
                self.monitor()

            # 完成
            self.finalize()

        except CollectionError:
            # 已经记录过日志，直接抛出
            raise

        except Exception as e:
            logger.exception(f"采集流程异常: {e}")
            print()
            print("=" * 80)
            print("❌ 发生错误")
            print("=" * 80)
            print(f"错误: {e}")
            raise CollectionError(f"采集流程失败: {e}") from e

        finally:
            # 清理
            self.cleanup()

    def run_single_collect(self):
        """运行单次采集

        用于快速测试或只需要一次快照的场景。
        包括：初始化 → 准备 → 采集一次 → 完成 → 清理

        Raises:
            CollectionError: 流程执行失败时抛出
        """
        try:
            # 初始化
            self.initialize()

            # 准备
            self.prepare()

            # 采集一次
            logger.info("=" * 80)
            logger.info("📊 单次数据采集")
            logger.info("=" * 80)
            print()
            self.collect_once()

            # 完成
            self.finalize()

        except CollectionError:
            # 已经记录过日志，直接抛出
            raise

        except Exception as e:
            logger.exception(f"单次采集异常: {e}")
            print()
            print("=" * 80)
            print("❌ 发生错误")
            print("=" * 80)
            print(f"错误: {e}")
            raise CollectionError(f"单次采集失败: {e}") from e

        finally:
            # 清理
            self.cleanup()
