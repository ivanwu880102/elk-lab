# Alert Worker (Discord) — 設定與測試指南

本文檔描述如何把 Elasticsearch 告警透過一個輕量的 `alert-worker` container 傳到 Discord（Webhook）。

重要：Webhook URL 等同通知密鑰，請勿公開或提交至版本控制。

## 概要
流程：

Discord Webhook → alert-worker (Python) → Elasticsearch 查詢 → 判斷門檻 → 發送 Discord

目標：當 Filebeat / Metricbeat 送入 Elasticsearch 的資料符合條件（例如登入失敗、CPU/Mem/Disk 達門檻），`alert-worker` 會呼叫 Discord Webhook 傳送訊息。

---

## 前提
- 已有本專案的 Docker Compose stack（包含 `es01`, `kibana`, `filebeat`, `metricbeat`, `nginx`）
- 你已在 Discord 建立好 Webhook 並取得 URL
- 你已在主機上準備好 `alert-worker` 目錄與所需檔案

---

## 1. 建立 Discord Webhook（操作摘要）
1. 打開 Discord → 目標 Server → 要接收告警的頻道 → 編輯頻道 → Integrations → Webhooks → Create Webhook。
2. 複製 Webhook URL（格式類似 `https://discord.com/api/webhooks/xxxx/yyyy`）。

測試 Webhook：
```bash
curl -H "Content-Type: application/json" \
  -X POST \
  -d '{"content":"Discord webhook test from ELK lab"}' \
  "<你的Discord Webhook URL>"
```
如果有訊息出現在頻道，Webhook 正常。

---

## 2. 建立 `alert-worker` 目錄與檔案
在專案根目錄下：

```bash
cd ~/docker-lab/elk
mkdir -p alert-worker
cd alert-worker
```

### 2.1 `alert_worker.py`
- 建立 `alert_worker.py`，並修改以下參數：
  - `ES_PASS = "你的Elastic密碼"`
  - `DISCORD_WEBHOOK = "你的Discord Webhook URL"`

### 2.2 `Dockerfile`
建立 `Dockerfile`，範例內容：

```
FROM python:3.12-slim
WORKDIR /app
RUN pip install requests
COPY alert_worker.py /app/alert_worker.py
CMD ["python", "alert_worker.py"]
```

---

## 3. 在 `docker-compose.yml` 中加入服務
在 `services:` 同層新增：

```yaml
  alert-worker:
    build: ./alert-worker
    container_name: alert-worker
    depends_on:
      - es01
    networks:
      - elastic
    restart: unless-stopped
```

注意：`alert-worker` 與 `es01`、`kibana`、`filebeat`、`metricbeat` 同層。

---

## 4. 啟動與檢查
建立並啟動 `alert-worker`：

```bash
cd ~/docker-lab/elk
docker compose up -d --build alert-worker
```

確認 container 啟動：

```bash
docker ps
```

查看 log：

```bash
docker logs -f alert-worker
```

預期 log 範例：
```
[INFO] Elasticsearch count response status: 200
[INFO] Elasticsearch metric response status: 200
[INFO] Auth failure count: 0
[INFO] CPU usage: 3.25%
[INFO] Memory usage: 42.10%
[INFO] Disk usage /dev/sda2: 55.30%
```

---

## 5. 告警來源與欄位（摘要）
- 登入失敗（Auth failure）
  - Index: `filebeat-*`
  - Query: `message: "pam_authenticate failed"`
  - 門檻：5 分鐘內 >= 5 次
- CPU
  - Index: `metricbeat-*`
  - Field: `system.cpu.total.norm.pct`
  - 門檻：> 0.8 (80%)
- Memory
  - Index: `metricbeat-*`
  - Field: `system.memory.used.pct`
  - 門檻：> 0.8 (80%)
- Disk (指定磁碟 `/dev/sda2`)
  - Index: `metricbeat-*`
  - Field: `system.filesystem.used.pct`
  - 門檻：> 0.95 (95%)

---

## 6. 測試場景
### 6.1 測試登入失敗告警
```bash
ssh fakeuser@localhost
# 故意輸入錯誤密碼 5 次以上
# 檢查 auth log
tail -f /var/log/auth.log
```

### 6.2 測試 CPU 告警
```bash
sudo apt install -y stress
stress --cpu $(nproc) --timeout 600
```

### 6.3 測試 Memory 告警
```bash
stress --vm 2 --vm-bytes 2G --timeout 600
```

### 6.4 測試 Disk 告警
```bash
df -h
dd if=/dev/zero of=/tmp/bigfile bs=1G count=90
# 檢查 df -h
rm -f /tmp/bigfile
```

---

## 7. 部署/開發工作流程
每次修改 `alert_worker.py` 後，重建並觀察 log：

```bash
cd ~/docker-lab/elk
docker compose up -d --build alert-worker
docker logs -f alert-worker
```

若 container 無法啟動或行為異常，可先強制移除再重建：

```bash
docker rm -f alert-worker
docker compose up -d --build alert-worker
```

---

## 8. 安全性注意事項
- 將 `DISCORD_WEBHOOK` 與 `ES_PASS` 保存在本機環境或 `.env`，不要將含密資訊的檔案加入版本控制。
- Webhook URL 請視為機密憑證。

---