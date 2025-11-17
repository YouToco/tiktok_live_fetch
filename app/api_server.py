"""
Web API 服务器

提供完整的 Web 控制面板，支持：
- 启动/停止监控
- 获取实时互动
- 处理验证码
"""

import base64
import io
import logging
import threading
import time
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from PIL import Image

from tiktok_monitor.collector import LiveCollector
from tiktok_monitor.config import MonitorConfig
from tiktok_monitor.logger import logger


class MonitorAPIServer:
    """监控 API 服务器

    提供 Web 界面控制采集器的完整 API
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        """初始化 API 服务器

        Args:
            host: 主机地址
            port: 端口号
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)  # 允许跨域请求

        # 前端文件路径
        self.frontend_path = Path(__file__).with_name("index.html")

        # 采集器相关
        self.collector: Optional[LiveCollector] = None
        self.collector_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.username = ""
        self.should_stop = False

        # 实时互动缓存（用于增量推送）
        self.last_interaction_count = 0

        # 验证码相关
        self.captcha_image_base64: Optional[str] = None
        self.captcha_solved = False

        # 注册路由
        self._setup_routes()

    def _setup_routes(self):
        """设置 Flask 路由"""

        @self.app.route("/", methods=["GET"])
        def serve_index():
            """提供 Web 控制面板页面"""
            index_path = self.frontend_path
            if index_path.exists():
                return send_file(str(index_path))
            else:
                return "index.html not found", 404

        @self.app.route("/api/start", methods=["POST"])
        def start_monitoring():
            """启动监控 - 持续监控模式"""
            if self.is_running:
                return jsonify({
                    "success": False,
                    "message": "监控已在运行中"
                }), 400

            data = request.get_json()
            if not data or "username" not in data:
                return jsonify({
                    "success": False,
                    "message": "缺少 username 参数"
                }), 400

            self.username = data["username"]
            self.should_stop = False
            self.last_interaction_count = 0

            # 在后台线程中启动采集器
            self.collector_thread = threading.Thread(
                target=self._run_collector,
                daemon=True
            )
            self.collector_thread.start()

            return jsonify({
                "success": True,
                "message": f"开始监控 @{self.username}",
                "username": self.username
            })

        @self.app.route("/api/stop", methods=["POST"])
        def stop_monitoring():
            """停止监控"""
            if not self.is_running:
                return jsonify({
                    "success": False,
                    "message": "当前没有运行中的监控"
                }), 400

            self.should_stop = True

            if self.collector:
                try:
                    self.collector.cleanup()
                except:
                    pass

            return jsonify({
                "success": True,
                "message": "监控已停止"
            })

        @self.app.route("/api/status", methods=["GET"])
        def get_status():
            """获取监控状态"""
            return jsonify({
                "is_running": self.is_running,
                "username": self.username if self.is_running else None
            })

        @self.app.route("/api/interactions", methods=["GET"])
        def get_interactions():
            """获取实时互动数据"""
            if not self.collector or not self.collector.hooks:
                return jsonify({
                    "success": True,
                    "interactions": [],
                    "message": "采集器未启动"
                })

            try:
                interactions = self.collector.hooks.get_live_interactions()
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

        @self.app.route("/api/captcha", methods=["GET"])
        def get_captcha():
            """获取验证码图片"""
            if not self.captcha_image_base64:
                return jsonify({"error": "验证码图片未准备好"}), 404

            return jsonify({
                "success": True,
                "image": self.captcha_image_base64,
                "timestamp": time.time()
            })

        @self.app.route("/api/captcha/click", methods=["POST"])
        def handle_captcha_click():
            """处理验证码点击"""
            data = request.get_json()

            if not data or "x" not in data or "y" not in data:
                return jsonify({"error": "缺少坐标参数"}), 400

            x = data["x"]
            y = data["y"]

            logger.info(f"收到验证码点击坐标: x={x}, y={y}")

            if not self.collector or not self.collector.browser:
                return jsonify({
                    "success": False,
                    "message": "采集器未运行"
                }), 400

            try:
                # 执行点击
                self.collector.browser.driver.execute_script(
                    """
                    var x = arguments[0];
                    var y = arguments[1];
                    var element = document.elementFromPoint(x, y);
                    if (element) {
                        var clickEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: x,
                            clientY: y
                        });
                        element.dispatchEvent(clickEvent);
                        console.log('[验证码处理] 点击已执行:', x, y, element);
                    }
                    """,
                    x, y
                )

                self.captcha_solved = True

                return jsonify({
                    "success": True,
                    "message": "点击已执行，请等待验证..."
                })
            except Exception as e:
                logger.error(f"执行验证码点击失败: {e}")
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 500

        @self.app.route("/api/captcha/status", methods=["GET"])
        def get_captcha_status():
            """获取验证码状态"""
            return jsonify({
                "solved": self.captcha_solved,
                "has_image": self.captcha_image_base64 is not None
            })

    def _run_collector(self):
        """在后台线程中运行采集器 - 持续监控模式"""
        try:
            self.is_running = True

            # 创建配置（设置超长监控时间，但通过 should_stop 控制）
            config = MonitorConfig(
                username=self.username,
                monitor_duration=86400,  # 24小时（实际通过 should_stop 控制）
                collect_interval=60  # 快照间隔保留用于调试
            )

            # 创建采集器
            self.collector = LiveCollector(config)

            # 初始化
            self.collector.initialize()

            # 准备
            self.collector.prepare()

            # 立即采集第一个快照
            logger.info("=" * 80)
            logger.info("📊 初始数据采集")
            logger.info("=" * 80)
            print()
            self.collector.collect_once()

            # 如果第一次采集就发现直播已结束，则退出
            if self.collector.live_has_ended:
                logger.info("直播已结束")
                return

            # 持续监控模式 - 直到用户停止或直播结束
            logger.info("=" * 80)
            logger.info("⏱️  持续监控模式已启动")
            logger.info("=" * 80)
            logger.info("📺 实时互动监控已启动（等待用户停止）")
            logger.info("=" * 80)
            print()

            start_time = time.time()
            last_collect_time = 0

            while not self.should_stop:
                elapsed = time.time() - start_time

                # 定期保存快照（60秒）
                if elapsed - last_collect_time >= 60:
                    print()
                    if not self.collector.collect_once():
                        # 直播已结束或采集不健康，停止监控
                        break
                    last_collect_time = elapsed
                    print()

                # 实时检查互动（每次循环都检查）
                self.collector.process_live_interactions()

                time.sleep(0.2)  # 每 0.2 秒检查一次

            print()
            print()
            logger.info("✅ 监控已停止")

            # 完成
            self.collector.finalize()

        except Exception as e:
            logger.exception(f"采集流程异常: {e}")
            print()
            print("=" * 80)
            print("❌ 发生错误")
            print("=" * 80)
            print(f"错误: {e}")

        finally:
            # 清理
            if self.collector:
                self.collector.cleanup()

            self.is_running = False
            self.collector = None

    def capture_captcha(self):
        """捕获验证码图片"""
        if not self.collector or not self.collector.browser:
            return False

        try:
            logger.info("正在捕获验证码图片...")

            # 截取整个页面
            screenshot = self.collector.browser.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))

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

    def start(self):
        """启动 API 服务器"""
        logger.info(f"🚀 启动监控 API 服务器: http://{self.host}:{self.port}")

        # 禁用 Flask 的日志输出
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
