import time
import requests
from datetime import datetime, timedelta, timezone


ES_URL = "http://es01:9200"
ES_USER = "elastic"
ES_PASS = "你的Elastic密碼"
DISCORD_WEBHOOK = "你的Discord Webhook URL"

CHECK_INTERVAL = 30
TIME_WINDOW_MINUTES = 5
ALERT_COOLDOWN = 300

AUTH_FAILURE_THRESHOLD = 5
CPU_THRESHOLD = 0.80
MEMORY_THRESHOLD = 0.80
DISK_THRESHOLD = 0.95

DISK_DEVICE_NAME = "/dev/sda2"

last_alert_time = {
    "auth": 0,
    "cpu": 0,
    "memory": 0,
    "disk": 0
}


def send_discord(message):
    r = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=10
    )

    print(f"[INFO] Discord response status: {r.status_code}", flush=True)


def can_send_alert(alert_name):
    current_time = time.time()

    if current_time - last_alert_time[alert_name] >= ALERT_COOLDOWN:
        last_alert_time[alert_name] = current_time
        return True

    print(f"[INFO] {alert_name} alert suppressed by cooldown.", flush=True)
    return False


def es_count(index, query):
    r = requests.post(
        f"{ES_URL}/{index}/_count",
        auth=(ES_USER, ES_PASS),
        json=query,
        timeout=10
    )

    print(f"[INFO] Elasticsearch count response status: {r.status_code}", flush=True)
    return r.json().get("count", 0)


def es_max_metric(index, field, extra_filter=None):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=TIME_WINDOW_MINUTES)

    filters = [
        {
            "range": {
                "@timestamp": {
                    "gte": start.isoformat(),
                    "lte": now.isoformat()
                }
            }
        },
        {
            "exists": {
                "field": field
            }
        }
    ]

    if extra_filter:
        filters.append(extra_filter)

    query = {
        "size": 0,
        "query": {
            "bool": {
                "filter": filters
            }
        },
        "aggs": {
            "max_value": {
                "max": {
                    "field": field
                }
            }
        }
    }

    r = requests.post(
        f"{ES_URL}/{index}/_search",
        auth=(ES_USER, ES_PASS),
        json=query,
        timeout=10
    )

    print(f"[INFO] Elasticsearch metric response status: {r.status_code}", flush=True)

    data = r.json()
    value = data.get("aggregations", {}).get("max_value", {}).get("value")

    if value is None:
        return 0

    return value


def count_auth_failure():
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=TIME_WINDOW_MINUTES)

    query = {
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": start.isoformat(),
                                "lte": now.isoformat()
                            }
                        }
                    },
                    {
                        "match_phrase": {
                            "message": "pam_authenticate failed"
                        }
                    }
                ]
            }
        }
    }

    return es_count("filebeat-*", query)


while True:
    try:
        auth_count = count_auth_failure()
        cpu_usage = es_max_metric("metricbeat-*", "system.cpu.total.norm.pct")
        memory_usage = es_max_metric("metricbeat-*", "system.memory.used.pct")
        disk_usage = es_max_metric(
            "metricbeat-*",
            "system.filesystem.used.pct",
            {
                "term": {
                    "system.filesystem.device_name": DISK_DEVICE_NAME
                }
            }
        )

        print(f"[INFO] Auth failure count: {auth_count}", flush=True)
        print(f"[INFO] CPU usage: {cpu_usage * 100:.2f}%", flush=True)
        print(f"[INFO] Memory usage: {memory_usage * 100:.2f}%", flush=True)
        print(f"[INFO] Disk usage {DISK_DEVICE_NAME}: {disk_usage * 100:.2f}%", flush=True)

        if auth_count >= AUTH_FAILURE_THRESHOLD:
            if can_send_alert("auth"):
                send_discord(
                    f"Authentication Failure Alert\n"
                    f"Failed login count in last {TIME_WINDOW_MINUTES} minutes: {auth_count}"
                )

        if cpu_usage > CPU_THRESHOLD:
            if can_send_alert("cpu"):
                send_discord(
                    f"High CPU Usage Alert\n"
                    f"Highest CPU usage in last {TIME_WINDOW_MINUTES} minutes: {cpu_usage * 100:.2f}%"
                )

        if memory_usage > MEMORY_THRESHOLD:
            if can_send_alert("memory"):
                send_discord(
                    f"High Memory Usage Alert\n"
                    f"Highest memory usage in last {TIME_WINDOW_MINUTES} minutes: {memory_usage * 100:.2f}%"
                )

        if disk_usage > DISK_THRESHOLD:
            if can_send_alert("disk"):
                send_discord(
                    f"High Disk Usage Alert\n"
                    f"Disk device: {DISK_DEVICE_NAME}\n"
                    f"Highest disk usage in last {TIME_WINDOW_MINUTES} minutes: {disk_usage * 100:.2f}%"
                )

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        time.sleep(CHECK_INTERVAL)
