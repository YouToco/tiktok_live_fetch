"""
JavaScript Hook 注入模块

通过注入 JavaScript 代码来拦截和获取直播间数据
"""

from typing import Any, Optional

from selenium.webdriver.chrome.webdriver import WebDriver

from .logger import logger


class JavaScriptHook:
    """JavaScript Hook 注入器

    在页面中注入 JavaScript 代码来拦截各种数据源。
    """

    def __init__(self, driver: WebDriver):
        """初始化 Hook 注入器

        Args:
            driver: Selenium WebDriver 实例
        """
        self.driver = driver
        self.hooks_installed = False

    def install_websocket_hook(self) -> bool:
        """安装 WebSocket Hook

        拦截 WebSocket 消息，捕获实时数据。

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装 WebSocket Hook...")

            hook_script = """
            (function() {
                // 存储捕获的消息
                window.__tiktok_ws_messages = [];

                // Hook WebSocket
                const OriginalWebSocket = window.WebSocket;
                window.WebSocket = function(...args) {
                    const ws = new OriginalWebSocket(...args);

                    console.log('[Hook] WebSocket 连接:', args[0]);

                    // Hook onmessage
                    const originalOnMessage = ws.onmessage;
                    ws.onmessage = function(event) {
                        console.log('[Hook] WebSocket 消息接收');

                        // 存储消息
                        window.__tiktok_ws_messages.push({
                            timestamp: new Date().toISOString(),
                            data: event.data,
                            type: typeof event.data
                        });

                        // 调用原始处理函数
                        if (originalOnMessage) {
                            originalOnMessage.call(this, event);
                        }
                    };

                    // Hook send
                    const originalSend = ws.send;
                    ws.send = function(data) {
                        console.log('[Hook] WebSocket 发送消息');
                        return originalSend.call(this, data);
                    };

                    return ws;
                };

                console.log('[Hook] WebSocket Hook 已安装');
            })();
            """

            self.driver.execute_script(hook_script)
            logger.info("✅ WebSocket Hook 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装 WebSocket Hook 失败: {e}")
            return False

    def install_fetch_hook(self) -> bool:
        """安装 Fetch Hook

        拦截 fetch 请求，捕获 API 数据。

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装 Fetch Hook...")

            hook_script = """
            (function() {
                // 存储捕获的请求
                window.__tiktok_fetch_requests = [];

                // Hook fetch
                const originalFetch = window.fetch;
                window.fetch = async function(...args) {
                    const url = args[0];
                    console.log('[Hook] Fetch 请求:', url);

                    // 调用原始 fetch
                    const response = await originalFetch(...args);

                    // 克隆响应以便读取
                    const clonedResponse = response.clone();

                    // 尝试读取响应数据
                    try {
                        const text = await clonedResponse.text();

                        // 存储请求信息
                        window.__tiktok_fetch_requests.push({
                            timestamp: new Date().toISOString(),
                            url: url.toString(),
                            status: response.status,
                            responseText: text.substring(0, 10000) // 限制大小
                        });
                    } catch (e) {
                        console.log('[Hook] 读取响应失败:', e);
                    }

                    return response;
                };

                console.log('[Hook] Fetch Hook 已安装');
            })();
            """

            self.driver.execute_script(hook_script)
            logger.info("✅ Fetch Hook 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装 Fetch Hook 失败: {e}")
            return False

    def install_xhr_hook(self) -> bool:
        """安装 XMLHttpRequest Hook

        拦截 XHR 请求，捕获 API 数据。

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装 XHR Hook...")

            hook_script = """
            (function() {
                // 存储捕获的请求
                window.__tiktok_xhr_requests = [];

                // Hook XMLHttpRequest
                const OriginalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    const xhr = new OriginalXHR();

                    const originalOpen = xhr.open;
                    const originalSend = xhr.send;

                    let requestInfo = {
                        timestamp: new Date().toISOString(),
                        method: '',
                        url: '',
                        response: null,
                        status: 0
                    };

                    // Hook open
                    xhr.open = function(method, url, ...args) {
                        requestInfo.method = method;
                        requestInfo.url = url;
                        console.log('[Hook] XHR 请求:', method, url);
                        return originalOpen.call(this, method, url, ...args);
                    };

                    // Hook send
                    xhr.send = function(...args) {
                        // Hook onload
                        const originalOnLoad = xhr.onload;
                        xhr.onload = function() {
                            requestInfo.status = xhr.status;
                            requestInfo.response = xhr.responseText?.substring(0, 10000);

                            // 存储请求信息
                            window.__tiktok_xhr_requests.push(requestInfo);

                            if (originalOnLoad) {
                                originalOnLoad.call(this);
                            }
                        };

                        return originalSend.call(this, ...args);
                    };

                    return xhr;
                };

                console.log('[Hook] XHR Hook 已安装');
            })();
            """

            self.driver.execute_script(hook_script)
            logger.info("✅ XHR Hook 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装 XHR Hook 失败: {e}")
            return False

    def install_login_modal_closer(self) -> bool:
        """安装登录弹窗自动关闭 Hook

        监听登录弹窗的出现并自动关闭它，避免阻挡直播画面。

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装登录弹窗自动关闭 Hook...")

            hook_script = """
            (function() {
                console.log('[Hook] 登录弹窗自动关闭器已启动');

                // 尝试关闭登录弹窗的函数
                function closeLoginModal() {
                    // 多种可能的关闭按钮选择器
                    const closeButtonSelectors = [
                        '[data-e2e="modal-close-inner-button"]',
                        'div[aria-label="关闭"]',
                        'div[aria-label="Close"]',
                        'button[aria-label="关闭"]',
                        'button[aria-label="Close"]',
                        'div[role="button"][aria-label="关闭"]',
                        'div[role="button"][aria-label="Close"]',
                        '.tiktok-19goahw',
                        'div[role="dialog"] div[role="button"]:first-child'
                    ];

                    // 尝试查找并点击关闭按钮
                    for (const selector of closeButtonSelectors) {
                        try {
                            const closeButtons = document.querySelectorAll(selector);
                            for (const btn of closeButtons) {
                                // 检查按钮是否可见
                                const rect = btn.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    console.log('[Hook] 找到登录弹窗关闭按钮，准备点击:', selector);
                                    btn.click();
                                    console.log('[Hook] ✅ 已点击关闭按钮');
                                    return true;
                                }
                            }
                        } catch (e) {
                            // 继续尝试下一个选择器
                        }
                    }

                    // 如果没有找到关闭按钮，尝试查找登录对话框并按 ESC
                    const loginModal = document.querySelector('#login-modal') || 
                                     document.querySelector('div[role="dialog"][aria-labelledby*="login"]');
                    if (loginModal) {
                        console.log('[Hook] 尝试按 ESC 键关闭登录对话框');
                        const escEvent = new KeyboardEvent('keydown', {
                            key: 'Escape',
                            code: 'Escape',
                            keyCode: 27,
                            which: 27,
                            bubbles: true,
                            cancelable: true
                        });
                        document.dispatchEvent(escEvent);
                        return true;
                    }

                    return false;
                }

                // 立即尝试关闭（页面加载时可能已经存在弹窗）
                setTimeout(closeLoginModal, 1000);
                setTimeout(closeLoginModal, 3000);
                setTimeout(closeLoginModal, 5000);

                // 使用 MutationObserver 监听登录弹窗的出现
                const observer = new MutationObserver(function(mutations) {
                    for (const mutation of mutations) {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === 1) { // 元素节点
                                // 检查是否是登录相关的弹窗
                                const isLoginModal = (
                                    (node.id && node.id.includes('login')) ||
                                    (node.getAttribute && node.getAttribute('id') === 'login-modal') ||
                                    (node.getAttribute && node.getAttribute('role') === 'dialog' && 
                                     node.getAttribute('aria-labelledby') === 'login-modal-title') ||
                                    (node.querySelector && node.querySelector('#login-modal')) ||
                                    (node.querySelector && node.querySelector('[id*="login"][role="dialog"]')) ||
                                    (node.querySelector && node.querySelector('h2[data-e2e="login-title"]'))
                                );

                                if (isLoginModal) {
                                    console.log('[Hook] 🔍 检测到登录弹窗出现！');
                                    // 稍微延迟一下再关闭，确保弹窗完全渲染
                                    setTimeout(closeLoginModal, 500);
                                    setTimeout(closeLoginModal, 1500);
                                }
                            }
                        }
                    }
                });

                // 监听整个 document.body
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                console.log('[Hook] 登录弹窗自动关闭器监听器已启动');
            })();
            """

            self.driver.execute_script(hook_script)
            logger.info("✅ 登录弹窗自动关闭 Hook 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装登录弹窗自动关闭 Hook 失败: {e}")
            return False

    def install_event_hook(self) -> bool:
        """安装 DOM 事件监听 Hook

        监听 TikTok 直播间的 DOM 变化，捕获弹幕、礼物等用户互动。
        使用 MutationObserver 监听特定的 DOM 容器。

        Returns:
            是否安装成功
        """
        try:
            logger.info("安装 DOM 事件监听 Hook...")

            hook_script = """
            (function() {
                // 存储捕获的直播互动
                window.__tiktok_live_interactions = [];

                // 系统消息关键词（用于过滤）
                const systemMessageKeywords = [
                    '网络连接',
                    '切换到更清晰',
                    '画质',
                    '网络状况',
                    '连接状态',
                    '系统提示',
                    '提示：',
                    '温馨提示',
                    '已为你',
                    '为你切换',
                    '正在为你',
                    '网速',
                    '加载中',
                    '请稍候',
                    '网络异常',
                    '连接已恢复',
                    '清晰度',
                    '视频质量',
                    '欢迎使用 TikTok 直播',
                    '创作者必须年满',
                    '观众必须年满',
                    '社区自律公约',
                    '点击即可点赞',
                    'Click to like',
                    'Tap to like',
                    '点击即可'
                ];

                function normalizeText(text) {
                    return (text || '').replace(/\s+/g, '').toLowerCase();
                }

                function isSystemMessage(text) {
                    if (!text || text.length < 2) return false;
                    const normalized = normalizeText(text);
                    return systemMessageKeywords.some(keyword =>
                        normalized.includes(normalizeText(keyword))
                    );
                }

                // 辅助函数：提取文本内容
                function extractText(element, selector) {
                    try {
                        const el = element.querySelector(selector);
                        return el ? el.textContent.trim() : '';
                    } catch(e) {
                        return '';
                    }
                }

                // 监听弹幕/聊天消息
                function observeChatMessages() {
                    const chatObserver = new MutationObserver(function(mutations) {
                        mutations.forEach(function(mutation) {
                            mutation.addedNodes.forEach(function(node) {
                                if (node.nodeType === 1) {
                                    // 检查是否是聊天消息元素
                                    const isChatMessage = node.querySelector && (
                                        node.getAttribute('data-e2e') === 'chat-message' ||
                                        node.querySelector('[data-e2e="chat-message"]')
                                    );

                                    if (isChatMessage) {
                                        const messageEl = node.getAttribute('data-e2e') === 'chat-message' ?
                                            node : node.querySelector('[data-e2e="chat-message"]');

                                        // 提取用户名
                                        const username = extractText(messageEl, '[data-e2e="message-owner-name"]');

                                        // 提取消息内容（排除用户名部分）
                                        const contentEl = messageEl.querySelector('.break-words.align-middle');
                                        const content = contentEl ? contentEl.textContent.trim() : '';

                                        if (username && content) {
                                            window.__tiktok_live_interactions.push({
                                                timestamp: new Date().toISOString(),
                                                type: 'chat',
                                                username: username,
                                                content: content
                                            });
                                            console.log('[Hook] 捕获弹幕:', username, '-', content);
                                        }
                                    }
                                }
                            });
                        });
                    });

                    // 观察整个文档（弹幕可能在任何地方出现）
                    chatObserver.observe(document.body, {
                        childList: true,
                        subtree: true
                    });

                    console.log('[Hook] 弹幕监听器已启动');
                }

                // 监听礼物动画（改进版）
                function observeGifts() {
                    const giftObserver = new MutationObserver(function(mutations) {
                        mutations.forEach(function(mutation) {
                            mutation.addedNodes.forEach(function(node) {
                                if (node.nodeType === 1) {
                                    // 多种礼物检测方式
                                    const text = node.textContent || '';
                                    const isGift = (
                                        // 检查 data-e2e 属性
                                        (node.getAttribute && node.getAttribute('data-e2e') &&
                                         node.getAttribute('data-e2e').includes('gift')) ||
                                        // 检查 class 包含 gift
                                        (node.className && typeof node.className === 'string' &&
                                         node.className.toLowerCase().includes('gift')) ||
                                        // 检查文本包含礼物关键词
                                        text.includes('sent') && text.includes('×') ||
                                        text.includes('送出') ||
                                        text.includes('赠送') ||
                                        // 检查是否包含礼物图标或名称
                                        node.querySelector && node.querySelector('[class*="gift"]')
                                    );

                                    if (isSystemMessage(text)) {
                                        console.log('[Hook] 跳过系统提示（礼物区）:', text.trim());
                                        return;
                                    }

                                    if (isGift && text && text.length < 500 && text.length > 2) {
                                        // 尝试解析用户名和礼物信息
                                        const username = extractText(node, '[class*="username"]') ||
                                                       extractText(node, '[data-e2e*="name"]') || '';

                                        window.__tiktok_live_interactions.push({
                                            timestamp: new Date().toISOString(),
                                            type: 'gift',
                                            username: username,
                                            content: text.trim()
                                        });
                                        console.log('[Hook] 捕获礼物:', username, '-', text.trim());
                                    }
                                }
                            });
                        });
                    });

                    giftObserver.observe(document.body, {
                        childList: true,
                        subtree: true
                    });

                    console.log('[Hook] 礼物监听器已启动');
                }

                // 监听其他互动（点赞、进入、关注、分享等 - 改进版）
                function observeOtherInteractions() {
                    const interactionObserver = new MutationObserver(function(mutations) {
                        mutations.forEach(function(mutation) {
                            mutation.addedNodes.forEach(function(node) {
                                if (node.nodeType === 1 && node.textContent) {
                                    const text = node.textContent.trim();
                                    const e2eAttr = node.getAttribute ? node.getAttribute('data-e2e') : '';
                                    const className = node.className && typeof node.className === 'string' ?
                                                    node.className.toLowerCase() : '';

                                    // 跳过过长的文本（可能不是单条互动）
                                    if (text.length > 200 || text.length < 2) return;

                                    // 🆕 过滤系统消息
                                    if (isSystemMessage(text)) {
                                        console.log('[Hook] 跳过系统消息:', text);
                                        return;
                                    }

                                    let interactionType = null;
                                    let username = '';
                                    let content = text;

                                    // 1. 检测进场/加入（更严格的条件）
                                    if (
                                        (text.includes('joined') || 
                                         text.includes('entered') ||
                                         text.includes('已加入') ||
                                         (text.includes('已') && text.includes('加入'))) ||
                                        (e2eAttr && (e2eAttr.includes('join') || e2eAttr.includes('enter'))) ||
                                        className.includes('join') ||
                                        className.includes('enter')
                                    ) {
                                        interactionType = 'join';
                                    }

                                    // 2. 检测点赞/心
                                    else if (
                                        text.includes('liked') ||
                                        text.includes('❤') ||
                                        text.includes('点赞') ||
                                        text.includes('喜欢') ||
                                        (e2eAttr && (e2eAttr.includes('like') || e2eAttr.includes('heart'))) ||
                                        className.includes('like') ||
                                        className.includes('heart')
                                    ) {
                                        interactionType = 'like';
                                    }

                                    // 3. 检测关注
                                    else if (
                                        text.includes('followed') ||
                                        text.includes('关注') ||
                                        text.includes('following') ||
                                        (e2eAttr && e2eAttr.includes('follow')) ||
                                        className.includes('follow')
                                    ) {
                                        interactionType = 'follow';
                                    }

                                    // 4. 检测分享
                                    else if (
                                        text.includes('shared') ||
                                        text.includes('分享') ||
                                        (e2eAttr && e2eAttr.includes('share')) ||
                                        className.includes('share')
                                    ) {
                                        interactionType = 'share';
                                    }

                                    // 如果识别到互动类型，记录它
                                    if (interactionType) {
                                        // 尝试提取用户名（从节点或父节点）
                                        username = extractText(node, '[class*="username"]') ||
                                                 extractText(node, '[data-e2e*="name"]') ||
                                                 extractText(node.parentElement, '[class*="username"]') || '';

                                        window.__tiktok_live_interactions.push({
                                            timestamp: new Date().toISOString(),
                                            type: interactionType,
                                            username: username,
                                            content: content
                                        });
                                        console.log('[Hook] 捕获互动:', interactionType, '-', username, '-', content);
                                    }
                                }
                            });
                        });
                    });

                    interactionObserver.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: false
                    });

                    console.log('[Hook] 其他互动监听器已启动');
                }

                // 启动所有监听器
                observeChatMessages();
                observeGifts();
                observeOtherInteractions();

                console.log('[Hook] DOM 事件监听 Hook 已全部安装');
            })();
            """

            self.driver.execute_script(hook_script)
            logger.info("✅ DOM 事件监听 Hook 安装成功")
            return True

        except Exception as e:
            logger.error(f"安装 DOM 事件监听 Hook 失败: {e}")
            return False

    def install_all_hooks(self) -> bool:
        """安装所有 Hook

        安装 DOM 事件监听 Hook 和登录弹窗自动关闭 Hook。
        DOM Hook 用于捕获直播间弹幕、礼物等互动。
        登录弹窗关闭器用于自动关闭登录弹窗，避免阻挡直播画面。

        Returns:
            是否全部安装成功
        """
        logger.info("开始安装所有 Hook...")

        # 安装登录弹窗自动关闭器（优先安装，确保不会被登录弹窗阻挡）
        login_closer_success = self.install_login_modal_closer()

        # 安装 DOM 事件监听
        event_hook_success = self.install_event_hook()

        # 只要有一个成功就算成功（登录关闭器是额外功能）
        self.hooks_installed = event_hook_success

        if login_closer_success and event_hook_success:
            logger.info("✅ 所有 Hook 安装完成")
        elif event_hook_success:
            logger.info("✅ DOM 监听 Hook 安装完成（登录弹窗关闭器安装失败）")
        else:
            logger.warning("⚠️ Hook 安装失败")

        return self.hooks_installed

    def get_live_interactions(self) -> list[dict]:
        """获取捕获的直播互动（弹幕、礼物等）

        Returns:
            直播互动列表
        """
        try:
            interactions = self.driver.execute_script(
                "return window.__tiktok_live_interactions || [];"
            )
            logger.debug(f"获取到 {len(interactions)} 条直播互动")
            return interactions or []
        except Exception as e:
            logger.error(f"获取直播互动失败: {e}")
            return []

    def get_all_captured_data(self) -> dict[str, Any]:
        """获取所有捕获的数据

        Returns:
            包含所有类型数据的字典
        """
        return {
            "live_interactions": self.get_live_interactions(),
        }

    def clear_captured_data(self):
        """清空所有捕获的数据"""
        try:
            self.driver.execute_script(
                "window.__tiktok_live_interactions = [];"
            )
            logger.debug("已清空捕获的直播互动数据")
        except Exception as e:
            logger.error(f"清空数据失败: {e}")

    def inject_data_extractor(self) -> bool:
        """注入数据提取器

        直接从页面对象中提取数据。

        Returns:
            是否注入成功
        """
        try:
            logger.info("注入数据提取器...")

            extractor_script = """
            (function() {
                window.__tiktok_data_extractor = {
                    // 提取直播间信息
                    getLiveRoomInfo: function() {
                        try {
                            // 尝试从多个可能的位置获取数据
                            const data = window.__UNIVERSAL_DATA_FOR_REHYDRATION__ ||
                                       window.__INITIAL_STATE__ ||
                                       window.__NEXT_DATA__ ||
                                       {};

                            return {
                                timestamp: new Date().toISOString(),
                                data: data
                            };
                        } catch (e) {
                            return { error: e.toString() };
                        }
                    },

                    // 提取评论列表
                    getComments: function() {
                        try {
                            const comments = [];
                            // 查找评论元素（需要根据实际 DOM 结构调整）
                            const commentElements = document.querySelectorAll('[data-e2e="comment-item"]');

                            commentElements.forEach(el => {
                                const username = el.querySelector('[data-e2e="comment-username"]')?.textContent;
                                const content = el.querySelector('[data-e2e="comment-content"]')?.textContent;

                                if (username && content) {
                                    comments.push({
                                        username: username.trim(),
                                        content: content.trim(),
                                        timestamp: new Date().toISOString()
                                    });
                                }
                            });

                            return comments;
                        } catch (e) {
                            return { error: e.toString() };
                        }
                    },

                    // 提取观众数
                    getViewerCount: function() {
                        try {
                            const elements = document.querySelectorAll('[class*="viewer"]');
                            for (let el of elements) {
                                const match = el.textContent.match(/\\d+/);
                                if (match) {
                                    return parseInt(match[0]);
                                }
                            }
                            return null;
                        } catch (e) {
                            return null;
                        }
                    }
                };

                console.log('[Hook] 数据提取器已注入');
            })();
            """

            self.driver.execute_script(extractor_script)
            logger.info("✅ 数据提取器注入成功")
            return True

        except Exception as e:
            logger.error(f"注入数据提取器失败: {e}")
            return False

    def extract_live_room_data(self) -> Optional[dict]:
        """使用注入的提取器获取直播间数据

        Returns:
            直播间数据字典
        """
        try:
            data = self.driver.execute_script(
                "return window.__tiktok_data_extractor?.getLiveRoomInfo();"
            )
            return data
        except Exception as e:
            logger.error(f"提取直播间数据失败: {e}")
            return None

    def extract_comments(self) -> list[dict]:
        """使用注入的提取器获取评论

        Returns:
            评论列表
        """
        try:
            comments = self.driver.execute_script(
                "return window.__tiktok_data_extractor?.getComments();"
            )
            return comments or []
        except Exception as e:
            logger.error(f"提取评论失败: {e}")
            return []

    def extract_viewer_count(self) -> Optional[int]:
        """使用注入的提取器获取观众数

        Returns:
            观众数
        """
        try:
            count = self.driver.execute_script(
                "return window.__tiktok_data_extractor?.getViewerCount();"
            )
            return count
        except Exception as e:
            logger.error(f"提取观众数失败: {e}")
            return None
