import os
import re
import pandas as pd
import config

def data_format(data):
    """
    目标清洗函数：剥离地域前缀和泛词后缀，提纯出核心企业名称（完全继承自 geminieye）
    """
    if not isinstance(data, str): data = str(data)
    
    # 剥离括号内容
    data = re.sub(r'[\(（].*?[\)）]', '', data)
    
    # 剥离法律后缀
    legal_suffixes = ['有限责任公司', '股份有限公司', '集团有限公司', '有限公司', '集团', '股份', '分公司', '支公司', '办事处', '委员会', '厂', '矿']
    for word in legal_suffixes: 
        data = data.replace(word, '')
        
    # 剥离企业泛词
    generic_phrases = ['计算机系统', '信息技术', '网络技术', '电子技术', '通信技术', '数据技术', '系统集成', '网络科技', '信息产业', '应用软件', '实业', '发展', '投资', '控股', '管理', '服务']
    for word in generic_phrases: 
        data = data.replace(word, '')
        
    data = data.replace('省', '').replace('市', '').replace('自治区', '')
    
    # 剥离地域前缀
    geo_prefixes = ["北京", "上海", "天津", "重庆", "南京", "无锡", "徐州", "常州", "苏州", "南通", "杭州", "宁波", "温州", "嘉兴", "金华", "合肥", "福州", "厦门", "泉州", "南昌", "济南", "青岛", "烟台", "潍坊", "临沂", "广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "南宁", "海口", "三亚", "武汉", "长沙", "郑州", "洛阳", "石家庄", "唐山", "太原", "呼和浩特", "包头", "西安", "兰州", "西宁", "银川", "乌鲁木齐", "延安", "成都", "绵阳", "贵阳", "昆明", "拉萨", "沈阳", "大连", "长春", "哈尔滨", "黑龙江", "吉林", "辽宁", "内蒙古", "河北", "河南", "山东", "山西", "江苏", "安徽", "陕西", "宁夏", "甘肃", "青海", "湖北", "湖南", "浙江", "江西", "福建", "贵州", "四川", "云南", "广东", "广西", "海南", "新疆", "西藏", "中国"]
    geo_prefixes.sort(key=len, reverse=True)
    
    for geo in geo_prefixes:
        if data.startswith(geo):
            if len(data) - len(geo) >= 2:
                data = data[len(geo):]
                break
                
    # 剥离短尾泛词
    short_noise_words = ['软件', '技术', '科技', '网络', '通信', '电子', '数码', '智能', '信息', '系统']
    for _ in range(2):
        for word in short_noise_words:
            if data.endswith(word):
                if len(data) - len(word) > 2: 
                    data = data[:-len(word)]
                    
    return data.strip()

def is_noise(name):
    """
    噪音检测函数 (黑名单)
    """
    if not name: return True
    text = str(name).lower()
    return any(noise in text for noise in config.NOISE_WORDS)

def match_rule(name):
    """
    高级规则匹配函数 (白名单 MATCH_RULES)
    """
    if not config.MATCH_RULES: 
        return True # 如果没配置白名单，默认全放行
        
    s = str(name).lower()
    for rule in config.MATCH_RULES:
        r = rule.lower()
        if r.startswith('!'):
            if r[2:-1] in s: return False
        elif '||' in r:
            if any(k.strip() in s for k in r.split('||')): return True
        elif '&&' in r:
            if all(k.strip() in s for k in r.split('&&')): return True
        elif r in s: 
            return True
            
    return False



def read_input_file(filepath):
    """
    通用文件读取器：支持自动解析 TXT, CSV, EXCEL 提取目标名称
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"找不到文件: {filepath}")
        
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.csv':
            try: 
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            except: 
                df = pd.read_csv(filepath, encoding='gbk')
            return df.iloc[:, 0].dropna().astype(str).unique().tolist()
            
        elif ext in ['.xlsx', '.xls']: 
            df = pd.read_excel(filepath)
            return df.iloc[:, 0].dropna().astype(str).unique().tolist()
            
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f if line.strip()]
            return list(set(lines))
            
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    except Exception as e:
        raise Exception(f"读取文件失败: {e}")
