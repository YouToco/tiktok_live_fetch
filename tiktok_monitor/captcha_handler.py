"""
验证码远程处理模块

提供 API 接口供前端获取验证码图片和提交点击坐标
"""

import base64
import io
import threading
import time
from typing import Callable, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains

from .logger import logger


class CaptchaHandler:
    """验证码处理器

    当检测到验证码时，启动一个简单的 API 服务，
    允许用户通过前端界面手动点击验证码。
    """

    def __init__(
        self,
        driver: WebDriver,
        get_interactions_callback: Optional[Callable[[], list]] = None
    ):
        """初始化验证码处理器

        Args:
            driver: Selenium WebDriver 实例
            get_interactions_callback: 获取实时互动数据的回调函数
        """
        self.driver = driver
        self.app = Flask(__name__)
        CORS(self.app)  # 允许跨域请求

        self.captcha_image_base64: Optional[str] = None
        self.captcha_solved = False
        self.api_server_thread: Optional[threading.Thread] = None
        self.get_interactions_callback = get_interactions_callback

        # 注册路由
        self._setup_routes()

    def _setup_routes(self):
        """设置 Flask 路由"""

        @self.app.route("/api/captcha", methods=["GET"])
        def get_captcha():
            """获取验证码图片（Base64 编码）"""
            if not self.captcha_image_base64:
                return jsonify({"error": "验证码图片未准备好"}), 404

            return jsonify({
                "success": True,
                "image": self.captcha_image_base64,
                "timestamp": time.time()
            })

        @self.app.route("/api/captcha/click", methods=["POST"])
        def handle_click():
            """处理前端传来的点击坐标"""
            data = request.get_json()

            if not data or "x" not in data or "y" not in data:
                return jsonify({"error": "缺少坐标参数"}), 400

            x = data["x"]
            y = data["y"]

            logger.info(f"收到验证码点击坐标: x={x}, y={y}")

            try:
                # 执行点击
                success = self._click_at_coordinates(x, y)

                if success:
                    self.captcha_solved = True
                    return jsonify({
                        "success": True,
                        "message": "点击已执行，请等待验证..."
                    })
                else:
                    return jsonify({
                        "success": False,
                        "message": "点击执行失败"
                    }), 500

            except Exception as e:
                logger.error(f"执行验证码点击失败: {e}")
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 500

        @self.app.route("/api/captcha/status", methods=["GET"])
        def get_status():
            """获取验证码处理状态"""
            return jsonify({
                "solved": self.captcha_solved,
                "has_image": self.captcha_image_base64 is not None
            })

        @self.app.route("/api/interactions", methods=["GET"])
        def get_interactions():
            """获取实时互动数据（弹幕、礼物等）"""
            if not self.get_interactions_callback:
                return jsonify({
                    "success": True,
                    "interactions": [],
                    "message": "互动数据回调未设置"
                })

            try:
                interactions = self.get_interactions_callback()
                return jsonify({
                    "success": True,
                    "interactions": interactions,
                    "count": len(interactions),
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"获取互动数据失败: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "interactions": []
                }), 500

    def capture_captcha_image(self) -> bool:
        """捕获验证码图片

        Returns:
            是否成功捕获
        """
        try:
            logger.info("正在捕获验证码图片...")

            # 截取整个页面
            screenshot = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))

            # TODO: 如果需要，可以尝试定位验证码元素并裁剪
            # 目前直接使用整页截图

            # 转换为 Base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            self.captcha_image_base64 = f"data:image/png;base64,{img_base64}"

            logger.info("✅ 验证码图片捕获成功")
            return True

        except Exception as e:
            logger.error(f"捕获验证码图片失败: {e}")
            return False

    def _click_at_coordinates(self, x: int, y: int) -> bool:
        """在指定坐标执行点击

        Args:
            x: X 坐标（相对于页面左上角）
            y: Y 坐标（相对于页面左上角）

        Returns:
            是否成功执行点击
        """
        try:
            # 使用 JavaScript 在指定坐标执行点击
            self.driver.execute_script(
                """
                var x = arguments[0];
                var y = arguments[1];

                // 获取坐标处的元素
                var element = document.elementFromPoint(x, y);

                if (element) {
                    // 创建并触发点击事件
                    var clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y
                    });
                    element.dispatchEvent(clickEvent);

                    console.log('[验证码处理] 点击已执行:', x, y, element);
                    return true;
                } else {
                    console.error('[验证码处理] 未找到元素');
                    return false;
                }
                """,
                x,
                y,
            )

            logger.info(f"✅ 在坐标 ({x}, {y}) 执行点击")
            return True

        except Exception as e:
            logger.error(f"在坐标 ({x}, {y}) 执行点击失败: {e}")
            return False

    def start_api_server(self, port: int = 5000, host: str = "0.0.0.0"):
        """启动 API 服务器（在后台线程中）

        Args:
            port: 端口号
            host: 主机地址
        """
        logger.info(f"启动验证码处理 API 服务器: http://{host}:{port}")

        def run_server():
            # 禁用 Flask 的日志输出
            import logging

            log = logging.getLogger("werkzeug")
            log.setLevel(logging.ERROR)

            self.app.run(host=host, port=port, debug=False, use_reloader=False)

        self.api_server_thread = threading.Thread(target=run_server, daemon=True)
        self.api_server_thread.start()

        logger.info("✅ API 服务器已启动")

    def wait_for_solution(self, timeout: int = 300) -> bool:
        """等待用户手动解决验证码

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功解决验证码
        """
        logger.info(f"等待用户解决验证码（超时: {timeout}秒）...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.captcha_solved:
                logger.info("✅ 验证码已解决！")
                return True

            time.sleep(1)

        logger.warning("⚠️  验证码解决超时")
        return False

    def reset(self):
        """重置状态"""
        self.captcha_image_base64 = None
        self.captcha_solved = False
