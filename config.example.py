import os

# ZoomEye account
USERNAME = os.environ.get("ZOOMEYE_USERNAME", "").strip()
PASSWORD = os.environ.get("ZOOMEYE_PASSWORD", "").strip()

# HTTP / auth settings
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

# Scan settings
MIN_DELAY = 3
MAX_DELAY = 8
LIMIT = 20

# Match / filter settings
MATCH_RULES = []
NOISE_WORDS = []
