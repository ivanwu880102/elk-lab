# 匯入 time 模組，用來 sleep、計算 cooldown 時間
import time

# 匯入 requests，用來呼叫 Elasticsearch API 與 Discord Webhook
import requests

# 匯入時間相關模組，用來產生查詢 Elasticsearch 的時間區間
from datetime import datetime, timedelta, timezone


# Elasticsearch 服務位置
# 因為 alert-worker 跟 es01 在同一個 Docker network，所以可以直接用 es01:9200
ES_URL = "http://es01:9200"

# Elasticsearch 登入帳號
ES_USER = "elastic"

# Elasticsearch 密碼
# 正式環境建議改用 .env，不要直接寫在程式裡
ES_PASS = "你的Elastic密碼"

# Discord Webhook URL
# 正式環境建議改用 .env，不要直接寫在程式裡
DISCORD_WEBHOOK = "你的Discord Webhook URL"


# 每幾秒檢查一次 Elasticsearch
CHECK_INTERVAL = 30

# 查詢最近幾分鐘內的資料
TIME_WINDOW_MINUTES = 5

# 同一種告警冷卻時間，單位是秒
# 300 秒 = 5 分鐘，避免一直洗 Discord 訊息
ALERT_COOLDOWN = 300


# 登入失敗門檻
# 5 分鐘內登入失敗 >= 5 次就告警
AUTH_FAILURE_THRESHOLD = 5

# CPU 使用率門檻
# 0.80 = 80%
CPU_THRESHOLD = 0.80

# Memory 使用率門檻
# 0.80 = 80%
MEMORY_THRESHOLD = 0.80

# Disk 使用率門檻
# 0.95 = 95%
DISK_THRESHOLD = 0.95


# 指定要監控哪一顆磁碟
# 這個名稱要跟 Metricbeat 進 Elasticsearch 的 system.filesystem.device_name 一致
DISK_DEVICE_NAME = "/dev/sda2"


# 記錄各種告警上一次發送時間
# 用來做 cooldown 控制
last_alert_time = {
    "auth": 0,
    "cpu": 0,
    "memory": 0,
    "disk": 0
}


# 發送 Discord 訊息的函式
def send_discord(message):

    # 使用 HTTP POST 發送 JSON 到 Discord Webhook
    r = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=10
    )

    # 印出 Discord 回應狀態碼，方便確認是否成功
    print(f"[INFO] Discord response status: {r.status_code}", flush=True)


# 判斷某一種告警是否可以發送
def can_send_alert(alert_name):

    # 取得目前 Unix timestamp
    current_time = time.time()

    # 如果目前時間 - 上次發送時間 >= cooldown 秒數，就允許發送
    if current_time - last_alert_time[alert_name] >= ALERT_COOLDOWN:

        # 更新該告警的最後發送時間
        last_alert_time[alert_name] = current_time

        # 回傳 True，代表可以發送
        return True

    # 如果還在 cooldown 期間，就印出 suppressed 訊息
    print(f"[INFO] {alert_name} alert suppressed by cooldown.", flush=True)

    # 回傳 False，代表不要發送
    return False


# 查詢 Elasticsearch 文件數量的函式
# 適合用在登入失敗次數這種 count 類型查詢
def es_count(index, query):

    # 呼叫 Elasticsearch _count API
    r = requests.post(
        f"{ES_URL}/{index}/_count",
        auth=(ES_USER, ES_PASS),
        json=query,
        timeout=10
    )

    # 印出 Elasticsearch 回應狀態
    print(f"[INFO] Elasticsearch count response status: {r.status_code}", flush=True)

    # 從 JSON 回應中取出 count
    # 如果沒有 count，就回傳 0
    return r.json().get("count", 0)


# 查詢某個 metric 欄位最大值的函式
# 適合用在 CPU、Memory、Disk 這類百分比數值
def es_max_metric(index, field, extra_filter=None):

    # 取得目前 UTC 時間
    now = datetime.now(timezone.utc)

    # 計算查詢起始時間
    # 例如 TIME_WINDOW_MINUTES = 5，就查最近 5 分鐘
    start = now - timedelta(minutes=TIME_WINDOW_MINUTES)

    # 建立 Elasticsearch filter 條件
    filters = [
        {
            # 限制 @timestamp 在指定時間區間內
            "range": {
                "@timestamp": {
                    "gte": start.isoformat(),
                    "lte": now.isoformat()
                }
            }
        },
        {
            # 確認該欄位存在
            "exists": {
                "field": field
            }
        }
    ]

    # 如果有額外 filter，就加入 filters
    # 例如 Disk 要指定 /dev/sda2
    if extra_filter:
        filters.append(extra_filter)

    # 建立 Elasticsearch aggregation 查詢
    query = {
        # size = 0 代表不用回傳原始 documents，只要 aggregation 結果
        "size": 0,

        # bool filter 查詢
        "query": {
            "bool": {
                "filter": filters
            }
        },

        # aggregation：取該欄位最大值
        "aggs": {
            "max_value": {
                "max": {
                    "field": field
                }
            }
        }
    }

    # 呼叫 Elasticsearch _search API
    r = requests.post(
        f"{ES_URL}/{index}/_search",
        auth=(ES_USER, ES_PASS),
        json=query,
        timeout=10
    )

    # 印出 Elasticsearch 回應狀態
    print(f"[INFO] Elasticsearch metric response status: {r.status_code}", flush=True)

    # 將回應轉成 JSON
    data = r.json()

    # 取出 aggregation max_value 的 value
    value = data.get("aggregations", {}).get("max_value", {}).get("value")

    # 如果沒有值，回傳 0
    if value is None:
        return 0

    # 回傳最大值
    return value


# 計算登入失敗次數的函式
def count_auth_failure():

    # 取得目前 UTC 時間
    now = datetime.now(timezone.utc)

    # 計算查詢起始時間
    start = now - timedelta(minutes=TIME_WINDOW_MINUTES)

    # 建立 Elasticsearch 查詢
    query = {
        "query": {
            "bool": {
                "filter": [
                    {
                        # 查詢最近 TIME_WINDOW_MINUTES 分鐘內的資料
                        "range": {
                            "@timestamp": {
                                "gte": start.isoformat(),
                                "lte": now.isoformat()
                            }
                        }
                    },
                    {
                        # 查詢 message 內包含 pam_authenticate failed 的 log
                        "match_phrase": {
                            "message": "pam_authenticate failed"
                        }
                    }
                ]
            }
        }
    }

    # 呼叫 es_count，查 filebeat-* 裡符合條件的 log 筆數
    return es_count("filebeat-*", query)


# 主程式，無限迴圈執行
while True:

    try:
        # 查詢最近 5 分鐘登入失敗次數
        auth_count = count_auth_failure()

        # 查詢最近 5 分鐘 CPU 最大使用率
        cpu_usage = es_max_metric("metricbeat-*", "system.cpu.total.norm.pct")

        # 查詢最近 5 分鐘 Memory 最大使用率
        memory_usage = es_max_metric("metricbeat-*", "system.memory.used.pct")

        # 查詢最近 5 分鐘指定磁碟最大使用率
        disk_usage = es_max_metric(
            "metricbeat-*",
            "system.filesystem.used.pct",
            {
                # 只查指定 device_name 的磁碟
                "term": {
                    "system.filesystem.device_name": DISK_DEVICE_NAME
                }
            }
        )

        # 印出登入失敗次數
        print(f"[INFO] Auth failure count: {auth_count}", flush=True)

        # 印出 CPU 使用率
        print(f"[INFO] CPU usage: {cpu_usage * 100:.2f}%", flush=True)

        # 印出 Memory 使用率
        print(f"[INFO] Memory usage: {memory_usage * 100:.2f}%", flush=True)

        # 印出 Disk 使用率
        print(f"[INFO] Disk usage {DISK_DEVICE_NAME}: {disk_usage * 100:.2f}%", flush=True)


        # 如果登入失敗次數達到門檻
        if auth_count >= AUTH_FAILURE_THRESHOLD:

            # 判斷是否通過 cooldown
            if can_send_alert("auth"):

                # 發送 Discord 告警
                send_discord(
                    f"Authentication Failure Alert\n"
                    f"Failed login count in last {TIME_WINDOW_MINUTES} minutes: {auth_count}"
                )


        # 如果 CPU 使用率大於門檻
        if cpu_usage > CPU_THRESHOLD:

            # 判斷是否通過 cooldown
            if can_send_alert("cpu"):

                # 發送 Discord 告警
                send_discord(
                    f"High CPU Usage Alert\n"
                    f"Highest CPU usage in last {TIME_WINDOW_MINUTES} minutes: {cpu_usage * 100:.2f}%"
                )


        # 如果 Memory 使用率大於門檻
        if memory_usage > MEMORY_THRESHOLD:

            # 判斷是否通過 cooldown
            if can_send_alert("memory"):

                # 發送 Discord 告警
                send_discord(
                    f"High Memory Usage Alert\n"
                    f"Highest memory usage in last {TIME_WINDOW_MINUTES} minutes: {memory_usage * 100:.2f}%"
                )


        # 如果 Disk 使用率大於門檻
        if disk_usage > DISK_THRESHOLD:

            # 判斷是否通過 cooldown
            if can_send_alert("disk"):

                # 發送 Discord 告警
                send_discord(
                    f"High Disk Usage Alert\n"
                    f"Disk device: {DISK_DEVICE_NAME}\n"
                    f"Highest disk usage in last {TIME_WINDOW_MINUTES} minutes: {disk_usage * 100:.2f}%"
                )

        # 等待 CHECK_INTERVAL 秒後再檢查一次
        time.sleep(CHECK_INTERVAL)

    # 如果程式發生錯誤，不讓 container 直接停止
    except Exception as e:

        # 印出錯誤訊息
        print(f"[ERROR] {e}", flush=True)

        # 發生錯誤後等待 CHECK_INTERVAL 秒再重試
        time.sleep(CHECK_INTERVAL)