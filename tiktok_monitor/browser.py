"""
浏览器管理模块
"""

import os
import time
from datetime import datetime
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import MonitorConfig
from .exceptions import BrowserError
from .logger import logger


class BrowserManager:
    """浏览器管理器

    负责管理 Chrome 浏览器的生命周期，包括启动、访问页面、关闭等操作。
    使用 undetected-chromedriver 绕过 TikTok 的自动化检测。
    """

    def __init__(self, config: MonitorConfig):
        """初始化浏览器管理器

        Args:
            config: 监控配置对象
        """
        self.config = config
        self.driver: Optional[WebDriver] = None

    def start(self) -> WebDriver:
        """启动浏览器

        Returns:
            WebDriver 实例

        Raises:
            BrowserError: 浏览器启动失败时抛出
        """
        logger.info("启动 Chrome 浏览器...")

        # 配置 Chrome 选项
        options = uc.ChromeOptions()

        # 自定义 Chrome 路径
        if self.config.chrome_binary_path:
            options.binary_location = self.config.chrome_binary_path
            logger.info(f"使用自定义 Chrome: {self.config.chrome_binary_path}")

        # 基础选项
        if self.config.headless:
            # Headless 模式（不推荐，可能被检测）
            logger.warning("使用 headless 模式可能被 TikTok 检测")
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            width, height = self.config.window_size
            options.add_argument(f"--window-size={width},{height}")
        else:
            # 非 headless 模式，最大化窗口以获得最佳效果
            options.add_argument("--start-maximized")

        # 反检测选项
        options.add_argument("--lang=zh-CN")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")

        try:
            # 创建驱动参数
            driver_kwargs = {
                "options": options,
                "version_main": None,  # 自动匹配 Chrome 版本
            }

            # 自定义 ChromeDriver 路径
            if self.config.chromedriver_path:
                driver_kwargs["driver_executable_path"] = self.config.chromedriver_path
                logger.info(f"使用自定义 ChromeDriver: {self.config.chromedriver_path}")

            # 创建驱动（不使用 subprocess 模式更稳定）
            self.driver = uc.Chrome(**driver_kwargs)

            # 等待浏览器完全启动并稳定（重要：线程环境下需要更长时间）
            time.sleep(3)

            # 确保窗口句柄可用
            self._ensure_window_handle()

            logger.info("浏览器启动成功")
            return self.driver

        except Exception as e:
            error_msg = f"浏览器启动失败: {e}"
            logger.error(error_msg)
            raise BrowserError(error_msg) from e

    def _ensure_window_handle(self):
        """确保窗口句柄可用（线程安全）

        在线程环境中，确保浏览器窗口句柄正确初始化
        """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 尝试获取所有窗口句柄
                handles = self.driver.window_handles
                if handles:
                    # 切换到第一个窗口
                    self.driver.switch_to.window(handles[0])
                    logger.debug(f"窗口句柄已就绪: {handles[0]}")
                    return
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"等待窗口句柄就绪... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(1)
                else:
                    logger.warning(f"无法获取窗口句柄: {e}")
                    raise

    def _close_login_modal(self):
        """自动关闭登录弹窗

        尝试多种选择器策略来关闭 TikTok 登录弹窗
        """
        try:
            logger.debug("尝试关闭登录弹窗...")

            # 等待一小段时间让弹窗可能出现
            time.sleep(2)

            # 尝试多种可能的关闭按钮选择器
            close_button_selectors = [
                # TikTok 常见的关闭按钮选择器
                'button[aria-label="Close"]',
                'button[aria-label="关闭"]',
                'div[role="dialog"] button[aria-label*="close" i]',
                'div[role="dialog"] button[aria-label*="关闭"]',
                # 通用的关闭按钮类名
                'button.tiktok-modal-close',
                'button.modal-close-btn',
                'button[class*="close"]',
                'button[class*="Close"]',
                # SVG 图标
                'svg[aria-label="Close"]',
                'svg[aria-label="关闭"]',
                # 包含 × 符号的按钮
                'button:contains("×")',
                'button:contains("✕")',
                # data 属性
                'button[data-e2e*="close"]',
                'button[data-e2e*="Close"]',
                # 其它可能的选择器
                '.login-modal__close',
                '[class*="LoginModal"] button[class*="close" i]',
            ]

            # 使用 JavaScript 查找并点击关闭按钮
            close_script = """
            // 尝试多种选择器找到关闭按钮
            const selectors = arguments[0];

            for (const selector of selectors) {
                try {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        // 找到第一个可见的关闭按钮
                        for (const element of elements) {
                            const rect = element.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                console.log('[关闭登录弹窗] 找到关闭按钮:', selector);
                                element.click();
                                return true;
                            }
                        }
                    }
                } catch (e) {
                    console.log('[关闭登录弹窗] 选择器失败:', selector, e);
                }
            }

            // 如果没有找到特定的关闭按钮，尝试查找任何对话框并按 Escape
            const dialogs = document.querySelectorAll('div[role="dialog"]');
            if (dialogs.length > 0) {
                console.log('[关闭登录弹窗] 尝试按 ESC 键关闭对话框');
                const escEvent = new KeyboardEvent('keydown', {
                    key: 'Escape',
                    code: 'Escape',
                    keyCode: 27,
                    which: 27,
                    bubbles: true
                });
                document.dispatchEvent(escEvent);
                return true;
            }

            return false;
            """

            # 执行关闭脚本
            result = self.driver.execute_script(close_script, close_button_selectors)

            if result:
                logger.info("✅ 成功关闭登录弹窗")
                time.sleep(1)  # 等待弹窗关闭动画完成
            else:
                logger.debug("未检测到登录弹窗或弹窗已关闭")

        except Exception as e:
            # 如果关闭失败也不影响主流程，只记录调试信息
            logger.debug(f"关闭登录弹窗时出现异常（可忽略）: {e}")

    def _is_browser_alive(self) -> bool:
        """检查浏览器是否仍然存活

        Returns:
            bool: 浏览器是否存活
        """
        if not self.driver:
            return False

        try:
            # 尝试获取窗口句柄，如果失败说明浏览器已关闭
            handles = self.driver.window_handles
            if not handles:
                return False
            # 尝试获取当前 URL
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    def visit_live_room(self):
        """访问直播间

        访问目标用户的直播间并等待页面完全加载。
        支持重试机制，提高线程环境下的稳定性。

        Raises:
            BrowserError: 浏览器未启动或访问失败时抛出
        """
        if not self.driver:
            raise BrowserError("浏览器未启动")

        # 检查浏览器是否被关闭
        if not self._is_browser_alive():
            raise BrowserError("浏览器窗口已被关闭，请不要手动关闭浏览器窗口")

        # 重试配置
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # 确保窗口句柄可用（每次尝试都检查）
                self._ensure_window_handle()

                logger.info(f"访问直播间: {self.config.live_url} (尝试 {attempt + 1}/{max_retries})")

                # 导航到直播间
                self.driver.get(self.config.live_url)

                # 等待页面关键元素加载
                try:
                    logger.debug("等待直播间关键元素加载...")
                    wait = WebDriverWait(self.driver, 30)  # 最长等待 30 秒

                    # 等待直播视频容器或用户头像等关键元素出现
                    # TikTok 可能会更改 CSS 选择器，这里使用一个常见的例子
                    # 您可以根据实际页面结构调整此选择器
                    # 等待多个可能的关键元素中的任何一个出现，增加鲁棒性
                    wait.until(EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='-LiveRoom']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-e2e='live-room']")),
                        EC.presence_of_element_located((By.TAG_NAME, "video"))
                    ))
                    logger.info("直播间关键元素加载成功")
                    time.sleep(1)  # 等待一些动态内容加载

                except Exception as e:
                    logger.warning(f"等待关键元素超时或失败: {e}")
                    # 即使等待失败，也继续尝试，但记录警告
                    pass

                # 检查浏览器是否仍然存活
                if not self._is_browser_alive():
                    raise BrowserError("浏览器窗口在访问直播间时被关闭")

                # 自动关闭登录弹窗
                self._close_login_modal()

                # 触发懒加载
                logger.debug("触发懒加载...")
                for i in range(3):
                    self.driver.execute_script(f"window.scrollTo(0, {(i + 1) * 300});")
                    time.sleep(0.5)  # 短暂暂停以触发懒加载

                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)  # 短暂暂停

                logger.info("直播间加载完成")
                return  # 成功，退出函数

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"访问直播间失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    # 最后一次尝试失败，抛出异常
                    error_msg = f"访问直播间失败（已重试 {max_retries} 次）: {e}"
                    logger.error(error_msg)
                    raise BrowserError(error_msg) from e

    def close(self):
        """关闭浏览器

        安全地关闭浏览器，释放资源。
        """
        if self.driver:
            logger.info("关闭浏览器...")
            time.sleep(1)  # 等待一会儿
            try:
                self.driver.quit()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.warning(f"关闭浏览器时出错: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """上下文管理器：进入"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.close()
