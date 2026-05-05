import time
import os
from playwright.sync_api import sync_playwright
import config
from logger import debug_log

def open_login_page(page):
    try:
        page.goto(config.LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)
        return True
    except Exception as e:
        debug_log(f"[Auth] 页面加载失败: {e}", "red")
        return False

def get_token():
    token = None
    debug_log("[Auth] 启动浏览器环境...", "yellow")
    
    with sync_playwright() as p:
        # 遵循 config 中的无头模式设置
        browser = p.chromium.launch(headless=config.AUTH_HEADLESS, args=['--disable-blink-features=AutomationControlled', '--no-sandbox'])
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent=config.UA
        )
        
        def on_request(req):
            nonlocal token
            if token: return
            for k, v in req.headers.items():
                if k.lower() == "cube-authorization" and len(v) > 20:
                    token = v
                    break
        
        context.on("request", on_request)
        page = context.new_page()
        
        if not open_login_page(page):
            browser.close(); return None, None

        try:
            debug_log("[Auth] 正在切换至账号密码登录面板...", "blue")
            # 同步 login.py 的核心动作
            page.click("text=账号密码登录")
            page.wait_for_timeout(2000)
            
            debug_log("[Auth] 正在填充凭证...", "blue")
            page.fill('input[placeholder="请输入账号"]', config.USERNAME)
            page.fill('input[placeholder="请输入密码"]', config.PASSWORD)
            page.wait_for_timeout(1000)
            
            debug_log("[Auth] 提交登录...", "blue")
            page.click('button.formBtn')
            
            # 动态等待 Token 捕获
            for _ in range(30):
                if token: break
                # 尝试从 LocalStorage 提取作为备份
                try:
                    js_t = page.evaluate("localStorage.getItem('Cube-Authorization')")
                    if js_t and len(js_t) > 20:
                        token = js_t
                        break
                except: pass
                time.sleep(1)
            
            # 如果还没拿到，尝试跳转强制触发
            if not token:
                debug_log("[Auth] 尚未捕获令牌，尝试强制唤醒...", "yellow")
                try:
                    page.goto(config.TRIGGER_URL, wait_until="domcontentloaded", timeout=30000)
                    for _ in range(15):
                        if token: break
                        time.sleep(1)
                except: pass
                    
            if token:
                debug_log("[Auth] 凭证获取成功！", "green")
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in context.cookies()])
                browser.close()
                return token, cookie_str
            else:
                debug_log("[Auth] 凭证获取失败，请手动确认网页是否需要验证码", "red")
                browser.close()
                return None, None
                
        except Exception as e:
            debug_log(f"[Auth] 流程异常: {e}", "red")
            if 'browser' in locals(): browser.close()
            return None, None

if __name__ == "__main__":
    t, c = get_token()
    print("TOKEN:", t)
