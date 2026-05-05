import base64
import os
import random
import time

import pandas as pd
import requests

import auth
import config
import utils
from logger import debug_log

CURRENT_TOKEN = None
CURRENT_COOKIE = None
AUTH_FAILURE_COUNT = 0
LAST_AUTH_TS = 0.0


def reset_auth_state():
    global CURRENT_TOKEN, CURRENT_COOKIE
    CURRENT_TOKEN = None
    CURRENT_COOKIE = None


def clear_auth_failures():
    global AUTH_FAILURE_COUNT
    AUTH_FAILURE_COUNT = 0


def ensure_auth():
    global CURRENT_TOKEN, CURRENT_COOKIE, AUTH_FAILURE_COUNT, LAST_AUTH_TS

    if CURRENT_TOKEN:
        return

    now = time.time()
    cooldown = getattr(config, "AUTH_RETRY_COOLDOWN_SECONDS", 45)
    if AUTH_FAILURE_COUNT and now - LAST_AUTH_TS < cooldown:
        wait_seconds = max(1, int(cooldown - (now - LAST_AUTH_TS)))
        raise Exception(f"recent auth failure, cooldown {wait_seconds}s")

    debug_log("凭证为空或已失效，正在尝试自动登录...", "yellow")
    CURRENT_TOKEN, CURRENT_COOKIE = auth.get_token()
    LAST_AUTH_TS = time.time()

    if not CURRENT_TOKEN:
        AUTH_FAILURE_COUNT += 1
        raise Exception("unable to obtain valid credential")

    clear_auth_failures()


def safe_search(keyword, field, limit=None, proxy_url=None):
    global CURRENT_TOKEN, CURRENT_COOKIE

    while True:
        try:
            ensure_auth()
            break
        except Exception as auth_err:
            if "cooldown" in str(auth_err).lower():
                # 智能等待：如果处于冷却期，每 5 秒探测一次，直到解除
                debug_log(f"⏳ 认证处于冷却保护中，扫描暂停等待中... ({auth_err})", "yellow")
                time.sleep(5)
                if getattr(config, "TASK_STATUS", {}).get('stop_signal'): return []
                continue
            else:
                debug_log(f"❌ 认证引擎致命异常: {auth_err}", "red")
                return []

    if limit is None:
        limit = config.LIMIT

    q_b64 = base64.b64encode(keyword.encode("utf-8")).decode()
    params = {"language": "zh", "field": field, "q": q_b64, "limit": limit}

    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    max_attempts = getattr(config, "REQUEST_RETRY_ATTEMPTS", 4)
    auth_retry_statuses = set(getattr(config, "AUTH_RETRY_STATUS_CODES", [401, 403]))
    backoff_statuses = set(getattr(config, "BACKOFF_STATUS_CODES", [429, 521, 502, 503, 504]))

    for attempt in range(max_attempts):
        headers = {
            "User-Agent": config.UA,
            "Cube-Authorization": CURRENT_TOKEN,
            "Cookie": CURRENT_COOKIE,
            "Origin": "https://www.zoomeye.org",
            "Referer": "https://www.zoomeye.org/searchResult",
        }

        try:
            res = requests.get(
                config.AGGS_URL,
                headers=headers,
                params=params,
                verify=False,
                timeout=10,
                proxies=proxies,
            )

            if res.status_code == 200:
                clear_auth_failures()
                data = res.json()
                return data.get(field, [])

            if res.status_code in auth_retry_statuses:
                debug_log(f"认证被拒绝 (HTTP {res.status_code})，刷新凭证后重试...", "orange")
                reset_auth_state()
                ensure_auth()
                continue

            if res.status_code in backoff_statuses:
                delay = min(2 * (attempt + 1), getattr(config, "MAX_BACKOFF_SECONDS", 12))
                debug_log(f"请求被拦截 (HTTP {res.status_code})，{delay}s 后重试，不触发重新登录...", "orange")
                time.sleep(delay)
                continue

            debug_log(f"API 错误: {res.status_code}", "red")
            return []

        except Exception as exc:
            delay = min(2 * (attempt + 1), getattr(config, "MAX_BACKOFF_SECONDS", 12))
            debug_log(f"网络请求异常: {exc}，{delay}s 后重试...", "red")
            time.sleep(delay)

    return []


def run_scan_task(
    filepath,
    selected_modes,
    output_format,
    delay_range,
    custom_filename,
    proxy_url,
    task_status,
    socketio,
    api_limit=20,
):
    min_sleep, max_sleep = delay_range
    proxy_status = proxy_url if proxy_url else "Direct"
    debug_log(f"NewEye 引擎启动 | 延时: {min_sleep}-{max_sleep}s | Route: {proxy_status}", "green")

    try:
        raw_names = utils.read_input_file(filepath)
        debug_log(f"目标装载完成: 队列数 {len(raw_names)}", "cyan")
    except Exception as exc:
        debug_log(f"任务载入异常: {exc}", "red")
        task_status["running"] = False
        socketio.emit("status", {"running": False, "paused": False})
        return

    all_results = []
    total_steps = len(raw_names)

    for idx, raw_name in enumerate(raw_names):
        if task_status["stop_signal"]:
            break

        if task_status["paused"]:
            debug_log("任务已暂停...", "yellow")
            while task_status["paused"]:
                if task_status["stop_signal"]:
                    break
                time.sleep(1)
            if task_status["stop_signal"]:
                break
            debug_log("恢复探测", "green")

        search_kw = utils.data_format(raw_name)
        if len(search_kw) < 2:
            search_kw = raw_name.strip()

        debug_log(f"[{idx + 1}/{total_steps}] 解析目标: {raw_name} -> 核心词: {search_kw}", "blue")

        for mode in selected_modes:
            if task_status["stop_signal"]:
                break

            debug_log(f"↳ 提取 [{mode.upper()}] ...", "gray")
            items = safe_search(search_kw, mode, limit=api_limit, proxy_url=proxy_url)

            if items:
                noise_free_items = [item for item in items if item.get("name") and not utils.is_noise(item["name"])]

                if config.MATCH_RULES:
                    filtered_items = [item for item in noise_free_items if utils.match_rule(item["name"])]
                else:
                    filtered_items = noise_free_items

                debug_log(
                    f"✅ [{mode}] API {len(items)} 条 | 去噪余 {len(noise_free_items)} 条 | 命中白名单 {len(filtered_items)} 条",
                    "green",
                )

                for item in noise_free_items:
                    is_filtered = utils.match_rule(item.get("name")) if config.MATCH_RULES else True
                    all_results.append(
                        {
                            "原始目标": raw_name,
                            "搜索关键词": search_kw,
                            "数据类型": mode,
                            "资产名称": item.get("name"),
                            "资产数量": item.get("count"),
                            "is_filtered": is_filtered,
                        }
                    )

                    if is_filtered:
                        socketio.emit(
                            "new_data",
                            {
                                "type": mode,
                                "keyword": search_kw,
                                "name": item.get("name"),
                                "count": item.get("count"),
                                "target": raw_name,
                            },
                        )
            else:
                debug_log("⚠️ 未找到有效数据", "gray")

            sleep_time = random.uniform(min_sleep, max_sleep)
            time.sleep(sleep_time)

        socketio.emit("progress", {"val": int(((idx + 1) / total_steps) * 98)})

    if all_results:
        debug_log("开始落盘处理...", "yellow")
        try:
            df_raw = pd.DataFrame(all_results)
            df_filtered = df_raw[df_raw["is_filtered"] == True].drop(columns=["is_filtered"])
            df_raw = df_raw.drop(columns=["is_filtered"])

            df_raw = df_raw.sort_values(by=["原始目标", "数据类型", "资产数量"], ascending=[True, True, False])
            if not df_filtered.empty:
                df_filtered = df_filtered.sort_values(by=["原始目标", "数据类型", "资产数量"], ascending=[True, True, False])

            if custom_filename and custom_filename.strip():
                base_name = custom_filename.strip()
            else:
                base_name = f"scan_{int(time.time())}"

            path_raw = os.path.join(config.RESULT_DIR_RAW, f"{base_name}_RAW.{output_format}")
            path_filtered = os.path.join(config.RESULT_DIR_FILTERED, f"{base_name}_FILTERED.{output_format}")

            if output_format == "xlsx":
                df_raw.to_excel(path_raw, index=False)
                df_filtered.to_excel(path_filtered, index=False)
            else:
                df_raw.to_csv(path_raw, index=False, encoding="utf-8-sig")
                df_filtered.to_csv(path_filtered, index=False, encoding="utf-8-sig")

            debug_log(f"扫描完成，优质白名单数据已生成: {path_filtered}", "green")
        except Exception as exc:
            debug_log(f"持久化异常: {exc}", "red")

    socketio.emit("progress", {"val": 100})
    task_status["running"] = False
    task_status["paused"] = False
    socketio.emit("status", {"running": False, "paused": False})
    debug_log("探测矩阵关闭", "green")
