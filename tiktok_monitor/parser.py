"""
数据解析模块
"""

from typing import Any, Optional

from selenium.webdriver.chrome.webdriver import WebDriver

from .exceptions import ParserError
from .logger import logger
from .models import LiveRoomInfo, PageSnapshot


class PageParser:
    """页面数据解析器

    从 TikTok 直播页面中解析和提取各种数据。
    """

    def __init__(self, driver: WebDriver):
        """初始化解析器

        Args:
            driver: Selenium WebDriver 实例
        """
        self.driver = driver

    def parse_page_status(self) -> dict[str, Any]:
        """解析页面状态

        Returns:
            包含页面状态的字典

        Raises:
            ParserError: 解析失败时抛出
        """
        try:
            logger.debug("解析页面状态...")
            status = self.driver.execute_script(
                """
                try {
                    // 安全地获取文本内容
                    const getBodyText = () => {
                        try {
                            return document.body.innerText || '';
                        } catch (e) {
                            return '';
                        }
                    };
                    
                    const bodyText = getBodyText();
                    
                    return {
                        url: window.location.href,
                        title: document.title || '',
                        hasVideo: !!document.querySelector('video'),
                        videoCount: document.querySelectorAll('video').length,
                        hasErrorMessage: bodyText.includes('尝试其它浏览器') ||
                                         bodyText.includes('try another browser'),
                        // 🆕 检测页面错误（"我们遇到了一些问题"等）
                        hasPageError: (() => {
                            try {
                                return bodyText.includes('我们遇到了一些问题') ||
                                       bodyText.includes('很抱歉造成不便') ||
                                       bodyText.includes('请稍后重试') ||
                                       bodyText.includes('Something went wrong') ||
                                       bodyText.includes('We encountered an issue') ||
                                       bodyText.includes('Please try again');
                            } catch (e) {
                                return false;
                            }
                        })(),
                        isLiveEnded: bodyText.includes('直播已结束') ||
                                     bodyText.includes('Live ended'),
                        hasLiveContent: !!document.querySelector('[class*="live"]') ||
                                       !!document.querySelector('[class*="Live"]'),
                        // 验证码检测
                        hasCaptcha: (() => {
                            try {
                                const bodyTextLower = bodyText.toLowerCase();
                                const hasTextKeyword = bodyTextLower.includes('验证') ||
                                                      bodyTextLower.includes('captcha') ||
                                                      bodyTextLower.includes('verify') ||
                                                      bodyTextLower.includes('滑动验证') ||
                                                      bodyTextLower.includes('slider');

                                // 检测常见的验证码 DOM 元素
                                const hasCaptchaElement = !!document.querySelector('[class*="captcha"]') ||
                                                         !!document.querySelector('[class*="verify"]') ||
                                                         !!document.querySelector('[id*="captcha"]') ||
                                                         !!document.querySelector('[id*="verify"]') ||
                                                         !!document.querySelector('iframe[src*="captcha"]') ||
                                                         !!document.querySelector('iframe[src*="verify"]');

                                return hasTextKeyword || hasCaptchaElement;
                            } catch (e) {
                                return false;
                            }
                        })(),
                        elementCount: document.querySelectorAll('*').length,
                        viewerCount: (() => {
                            try {
                                const elements = document.querySelectorAll('[class*="viewer"]');
                                for (let el of elements) {
                                    const match = el.innerText.match(/\\d+/);
                                    if (match) return parseInt(match[0]);
                                }
                                return null;
                            } catch (e) {
                                return null;
                            }
                        })(),
                        // 安全地提取文本预览，避免特殊字符导致序列化失败
                        bodyTextPreview: (() => {
                            try {
                                // 限制长度并清理特殊字符
                                const preview = bodyText.substring(0, 500);
                                // 移除可能导致序列化问题的字符
                                return preview.replace(/[\\x00-\\x1F\\x7F-\\x9F]/g, ' ');
                            } catch (e) {
                                return '';
                            }
                        })()
                    };
                } catch (error) {
                    // 如果发生任何错误，返回基本信息
                    console.error('[Parser] Error:', error);
                    return {
                        url: window.location.href || '',
                        title: document.title || '',
                        hasVideo: false,
                        videoCount: 0,
                        hasErrorMessage: false,
                        hasPageError: false,
                        isLiveEnded: false,
                        hasLiveContent: false,
                        hasCaptcha: false,
                        elementCount: 0,
                        viewerCount: null,
                        bodyTextPreview: '',
                        error: error.toString()
                    };
                }
            """
            )
            logger.debug("页面状态解析成功")
            return status

        except Exception as e:
            error_msg = f"解析页面状态失败: {e}"
            logger.error(error_msg)
            raise ParserError(error_msg) from e

    def parse_initial_data(self) -> Optional[dict]:
        """解析页面内嵌的初始化数据

        Returns:
            初始化数据字典，如果不存在返回 None

        Raises:
            ParserError: 解析失败时抛出
        """
        try:
            logger.debug("解析初始化数据...")
            initial_data = self.driver.execute_script(
                """
                const scripts = document.querySelectorAll('script');
                for (let script of scripts) {
                    if (script.id === '__UNIVERSAL_DATA_FOR_REHYDRATION__') {
                        try {
                            return JSON.parse(script.textContent);
                        } catch (e) {
                            return null;
                        }
                    }
                }
                return null;
            """
            )

            if initial_data:
                logger.debug("初始化数据解析成功")
            else:
                logger.debug("未找到初始化数据")

            return initial_data

        except Exception as e:
            logger.warning(f"解析初始化数据失败: {e}")
            return None

    def create_snapshot(self) -> PageSnapshot:
        """创建页面快照

        Returns:
            PageSnapshot 对象

        Raises:
            ParserError: 创建快照失败时抛出
        """
        try:
            logger.debug("创建页面快照...")

            # 解析页面状态
            page_status = self.parse_page_status()

            # 解析初始化数据
            initial_data = self.parse_initial_data()

            # 获取 HTML
            html_content = self.driver.page_source

            # 导入 datetime
            from datetime import datetime

            # 创建快照对象
            snapshot = PageSnapshot(
                timestamp=datetime.now().isoformat(),
                url=page_status["url"],
                title=page_status["title"],
                has_video=page_status["hasVideo"],
                has_error_message=page_status["hasErrorMessage"],
                has_page_error=page_status.get("hasPageError", False),
                has_live_content=page_status["hasLiveContent"],
                is_live_ended=page_status.get("isLiveEnded", False),
                has_captcha=page_status.get("hasCaptcha", False),
                element_count=page_status["elementCount"],
                video_count=page_status["videoCount"],
                html_size=len(html_content),
                viewer_count=page_status.get("viewerCount"),
                initial_data=initial_data,
                body_text_preview=page_status["bodyTextPreview"],
            )

            logger.debug("页面快照创建成功")
            return snapshot

        except Exception as e:
            error_msg = f"创建页面快照失败: {e}"
            logger.error(error_msg)
            raise ParserError(error_msg) from e

    def parse_live_room_info(self, initial_data: dict) -> LiveRoomInfo:
        """解析直播间信息

        Args:
            initial_data: 页面初始化数据

        Returns:
            LiveRoomInfo 对象
        """
        logger.debug("解析直播间信息...")
        return LiveRoomInfo.from_initial_data(initial_data)


class DataExtractor:
    """数据提取工具

    从页面 HTML 或其他数据源中提取特定信息。
    """

    @staticmethod
    def extract_comments(page_html: str) -> list[dict]:
        """从 HTML 中提取评论

        Args:
            page_html: 页面 HTML

        Returns:
            评论列表
        """
        logger.debug("提取评论数据...")
        # TODO: 实现评论提取逻辑
        return []

    @staticmethod
    def extract_recommended_users(page_html: str) -> list[dict]:
        """从 HTML 中提取推荐主播

        Args:
            page_html: 页面 HTML

        Returns:
            推荐主播列表
        """
        logger.debug("提取推荐主播数据...")
        # TODO: 实现推荐主播提取逻辑
        return []
