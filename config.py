import os

# ==================== 1. 账号配置 ====================
USERNAME = os.environ.get("ZOOMEYE_USERNAME", "").strip()
PASSWORD = os.environ.get("ZOOMEYE_PASSWORD", "").strip()

# ==================== 2. 接口配置 ====================
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
LOGIN_URL = "https://www.zoomeye.org/login"
TRIGGER_URL = "https://www.zoomeye.org/searchResult?q=port%3A80"
AGGS_URL = "https://www.zoomeye.org/api/analysis/aggs"
AUTH_HEADLESS = False
AUTH_RETRY_COOLDOWN_SECONDS = 25
REQUEST_RETRY_ATTEMPTS = 5
AUTH_RETRY_STATUS_CODES = [401, 403, 521]
BACKOFF_STATUS_CODES = [429, 502, 503, 504]
MAX_BACKOFF_SECONDS = 12

# ==================== 3. 扫描参数 ====================
MIN_DELAY = 3   # 最小随机延时（秒）
MAX_DELAY = 8   # 最大随机延时（秒）
LIMIT = 20    # 单次聚合最大返回数量

# ==================== 4. 目录配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR_RAW = os.path.join(BASE_DIR, "results", "raw")
RESULT_DIR_FILTERED = os.path.join(BASE_DIR, "results", "filtered")
UPLOAD_DIR = os.path.join(BASE_DIR, "results", "uploads")

for d in [RESULT_DIR_RAW, RESULT_DIR_FILTERED, UPLOAD_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# ==================== 5. 高级过滤规则 (MATCH_RULES) ====================
# 白名单规则。语法支持：单个词匹配、或(||)、与(&&)、非黑名单(!)
MATCH_RULES = [

]



# ==================== 6. 噪音过滤词汇 (NOISE_WORDS) ====================
# 从 geminieye 完美继承的庞大黑名单字典
NOISE_WORDS = [
    '导航网',
    '上网主页',
    '网址导航',
    '上网就上',
    '网站导航',
    '114啦',
    '2233dh',
    'my1399',
    '网址大全',
    '新葡京',
    '娱乐城',
    '娱乐平台',
    '寡乐城',
    '博彩',
    '赌局',
    '赌场',
    '九游会J9',
    'J9官网',
    '百家乐',
    '棋牌娱乐',
    '返券网',
    '优惠券',
    '领取网',
    '领券',
    '折扣',
    '促销',
    '成人网',
    '成人小说',
    '妻子',
    '逼',
    '官方网站-登录入口',
    '官方网站',
    '全球首选',
    '首选平台',
    '第一体育',
    '博天堂',
    '威尼斯人',
    '开奖网',
    '彩票',
    'APP下载',
    '电信',
    '联通',
    '移动',
    '宽带',
    'ISP',
    'CDN',
    'DNS',
    '解析',
    'Domain',
    '出售',
    '购买',
    'Parking',
    '广告',
    '单机',
    '301',
    '电路板',
    '下载',
    '免费',
    '播放',
    '浏览器',
    '游戏',
    '手游',
    '302',
    '网址',
    '小说',
    '欧洲',
    '官网',
    '协会',
    '电机',
    '团队',
    '502',
    '党',
    '工程',
    '省钱',
    '购物',
    '直播',
    '微信',
    '咨询',
    '培训',
    '人才',
    '有限公司',
    '阿里云',
    '澳门',
    '体育',
    '热门',
    '客服',
    '404',
    '403',
    '机构',
    '银行',
    '导航',
    '赛',
    '腾讯',
    '人民',
    '中华',
    '北京',
    '上海',
    '天津',
    '重庆',
    '南京',
    '无锡',
    '徐州',
    '常州',
    '苏州',
    '南通',
    '杭州',
    '宁波',
    '温州',
    '嘉兴',
    '金华',
    '合肥',
    '福州',
    '厦门',
    '泉州',
    '南昌',
    '济南',
    '青岛',
    '烟台',
    '潍坊',
    '临沂',
    '广州',
    '深圳',
    '珠海',
    '佛山',
    '东莞',
    '中山',
    '惠州',
    '南宁',
    '海口',
    '三亚',
    '武汉',
    '长沙',
    '郑州',
    '洛阳',
    '石家庄',
    '唐山',
    '太原',
    '呼和浩特',
    '包头',
    '西安',
    '兰州',
    '西宁',
    '银川',
    '乌鲁木齐',
    '延安',
    '成都',
    '绵阳',
    '贵阳',
    '昆明',
    '拉萨',
    '沈阳',
    '大连',
    '长春',
    '哈尔滨',
    '黑龙江',
    '吉林',
    '辽宁',
    '内蒙古',
    '河北',
    '河南',
    '山东',
    '山西',
    '江苏',
    '安徽',
    '陕西',
    '宁夏',
    '甘肃',
    '青海',
    '湖北',
    '湖南',
    '浙江',
    '江西',
    '福建',
    '贵州',
    '四川',
    '云南',
    '广东',
    '广西',
    '海南',
    '新疆',
    '西藏',
    '中国'
]
