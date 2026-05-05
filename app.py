import os
import time
import traceback

import pandas as pd
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

import config
import logger
import scanner
import utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neweye_super_secret'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

socketio = SocketIO(app, async_mode='threading', max_http_buffer_size=100 * 1024 * 1024)

logger.init_logger(socketio)

TASK_STATUS = {'running': False, 'stop_signal': False, 'paused': False}

IMPORT_TYPE_MAP = {
    'device': 'device',
    'product': 'product',
    'title': 'title',
    '设备': 'device',
    '组件': 'product',
    '标题': 'title',
    'app': 'product',
    'dev': 'device',
}

IMPORT_COL_ALIASES = {
    'keyword': ['搜索关键词', 'keyword', '关键词', 'kw', 'target'],
    'type': ['数据类型', 'type', '类型', 'mode'],
    'name': ['资产名称', 'name', '名称', 'asset'],
    'count': ['资产数量', 'count', '数量', 'cnt'],
}

IMPORT_COL_FALLBACKS = {
    'keyword': 1,
    'type': 2,
    'name': 3,
    'count': 4,
}


def _build_empty_import_data():
    return {'__GLOBAL__': {'device': [], 'product': [], 'title': []}}


def _read_import_dataframe(path, filename):
    if filename.lower().endswith('.csv'):
        last_error = None
        for encoding in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                return pd.read_csv(path, encoding=encoding)
            except Exception as exc:
                last_error = exc
        raise last_error
    return pd.read_excel(path)


def _resolve_import_columns(df):
    actual_cols = {}
    normalized_cols = [(col, str(col).strip().lower()) for col in df.columns]

    for key, aliases in IMPORT_COL_ALIASES.items():
        for alias in aliases:
            lowered = alias.lower()
            for col, normalized in normalized_cols:
                if normalized == lowered:
                    actual_cols[key] = col
                    break
            if key in actual_cols:
                break

    for key, fallback_idx in IMPORT_COL_FALLBACKS.items():
        if key not in actual_cols and len(df.columns) > fallback_idx:
            actual_cols[key] = df.columns[fallback_idx]

    return actual_cols


def _extract_row_value(row, col_name, fallback_idx, default=''):
    if col_name is not None:
        value = row.get(col_name, default)
    elif len(row) > fallback_idx:
        value = row.iloc[fallback_idx]
    else:
        value = default

    if pd.isna(value):
        return default
    return value


def _parse_import_count(value):
    if pd.isna(value):
        return 1
    if isinstance(value, str) and not value.strip():
        return 1
    try:
        parsed = int(float(value))
    except Exception:
        return 1
    return parsed if parsed > 0 else 1


def _build_import_payload(df):
    actual_cols = _resolve_import_columns(df)
    payload = _build_empty_import_data()
    buckets = payload['__GLOBAL__']
    index_maps = {bucket_name: {} for bucket_name in buckets}

    success_count = 0
    row_type_counts = {bucket_name: 0 for bucket_name in buckets}
    count_sums = {bucket_name: 0 for bucket_name in buckets}

    for _, row in df.iterrows():
        keyword = str(_extract_row_value(row, actual_cols.get('keyword'), 1, '')).strip()
        raw_type = str(_extract_row_value(row, actual_cols.get('type'), 2, 'title')).strip()
        name = str(_extract_row_value(row, actual_cols.get('name'), 3, '')).strip()
        count = _parse_import_count(_extract_row_value(row, actual_cols.get('count'), 4, 1))

        if not name and not keyword:
            continue

        normalized_type = IMPORT_TYPE_MAP.get(raw_type.lower(), IMPORT_TYPE_MAP.get(raw_type, 'title'))
        row_type_counts[normalized_type] += 1
        count_sums[normalized_type] += count

        item_key = (keyword, name)
        bucket = buckets[normalized_type]
        existing_idx = index_maps[normalized_type].get(item_key)
        if existing_idx is None:
            index_maps[normalized_type][item_key] = len(bucket)
            bucket.append({'keyword': keyword, 'name': name, 'count': count})
        else:
            bucket[existing_idx]['count'] += count

        success_count += 1

    for items in buckets.values():
        items.sort(key=lambda item: (-item['count'], item['keyword'], item['name']))

    unique_type_counts = {bucket_name: len(items) for bucket_name, items in buckets.items()}
    return payload, success_count, row_type_counts, unique_type_counts, count_sums


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start():
    if TASK_STATUS['running']:
        return jsonify({'status': 'error', 'msg': '引擎繁忙'})

    file = request.files.get('file')
    companies_text = request.form.get('companies_text', '').strip()
    modes = request.form.getlist('modes[]')
    out_fmt = request.form.get('format', 'xlsx')
    min_sleep = request.form.get('min_sleep', 5, type=int)
    max_sleep = request.form.get('max_sleep', 20, type=int)
    api_limit = request.form.get('api_limit', 20, type=int)
    custom_filename = request.form.get('custom_filename', '').strip()
    proxy_url = request.form.get('proxy_url', '').strip()

    if not modes:
        return jsonify({'status': 'error', 'msg': '无捕获维度(Title/App/Dev)'})
    if min_sleep < 0:
        min_sleep = 0
    if max_sleep < min_sleep:
        max_sleep = min_sleep

    filepath = None
    if companies_text:
        filepath = os.path.join(config.UPLOAD_DIR, f"direct_{int(time.time())}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(companies_text)
    elif file:
        filepath = os.path.join(config.UPLOAD_DIR, secure_filename(file.filename) or f"in_{int(time.time())}")
        file.save(filepath)
    else:
        return jsonify({'status': 'error', 'msg': '请上传文件或输入公司名称'})

    TASK_STATUS['running'] = True
    TASK_STATUS['paused'] = False
    TASK_STATUS['stop_signal'] = False

    socketio.emit('status', {'running': True, 'paused': False})
    socketio.start_background_task(
        target=scanner.run_scan_task,
        filepath=filepath,
        selected_modes=modes,
        output_format=out_fmt,
        delay_range=(min_sleep, max_sleep),
        custom_filename=custom_filename,
        proxy_url=proxy_url,
        task_status=TASK_STATUS,
        socketio=socketio,
        api_limit=api_limit
    )
    return jsonify({'status': 'ok'})


@app.route('/pause', methods=['POST'])
def pause():
    if not TASK_STATUS['running']:
        return jsonify({'status': 'error', 'msg': '引擎未运行'})
    TASK_STATUS['paused'] = True
    socketio.emit('status', {'running': True, 'paused': True})
    return jsonify({'status': 'ok'})


@app.route('/resume', methods=['POST'])
def resume():
    if not TASK_STATUS['running']:
        return jsonify({'status': 'error', 'msg': '引擎未运行'})
    TASK_STATUS['paused'] = False
    socketio.emit('status', {'running': True, 'paused': False})
    return jsonify({'status': 'ok'})


@app.route('/stop', methods=['POST'])
def stop():
    if TASK_STATUS['running']:
        TASK_STATUS['stop_signal'] = True
        TASK_STATUS['paused'] = False
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'})


@app.route('/get_config', methods=['GET'])
def get_config():
    return jsonify({
        'noise_words': config.NOISE_WORDS,
        'match_rules': config.MATCH_RULES
    })


@app.route('/save_config', methods=['POST'])
def save_config():
    try:
        data = request.get_json()
        noise_words = data.get('noise_words', [])
        match_rules = data.get('match_rules', [])

        config.NOISE_WORDS = noise_words
        config.MATCH_RULES = match_rules

        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        noise_str = 'NOISE_WORDS = [\n' + ',\n'.join(f'    {repr(w)}' for w in noise_words) + '\n]'
        content = re.sub(r'NOISE_WORDS\s*=\s*\[.*?\]', noise_str, content, flags=re.DOTALL)

        rules_str = 'MATCH_RULES = [\n' + ',\n'.join(f'    {repr(r)}' for r in match_rules) + '\n]'
        content = re.sub(r'MATCH_RULES\s*=\s*\[.*?\]', rules_str, content, flags=re.DOTALL)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({'status': 'ok', 'msg': '配置已保存'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500


@app.route('/import_data', methods=['POST'])
def import_data():
    file = request.files.get('file')
    if not file:
        return jsonify({'status': 'error', 'msg': '未选择文件'}), 400

    tmp_path = None
    try:
        fname = secure_filename(file.filename) or f"import_{int(time.time())}"
        tmp_path = os.path.join(config.UPLOAD_DIR, fname)
        file.save(tmp_path)

        df = _read_import_dataframe(tmp_path, fname)
        data, success_count, row_type_counts, unique_type_counts, count_sums = _build_import_payload(df)

        socketio.emit('log', {
            'time': time.strftime("%H:%M:%S"),
            'msg': f'📊 离线数据导入完成，成功注入 {success_count} 条记录',
            'color': '#30d158'
        })
        return jsonify({
            'status': 'ok',
            'msg': f'导入成功: {success_count} 条',
            'data': data,
            'stats': {
                'rows': success_count,
                'row_type_counts': row_type_counts,
                'unique_type_counts': unique_type_counts,
                'count_sums': count_sums,
            },
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({'status': 'error', 'msg': f'解析失败: {str(e)}'}), 500
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


if __name__ == '__main__':
    logger.debug_log("NewEye Web System Initialized", "blue")
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
