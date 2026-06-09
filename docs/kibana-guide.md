# Kibana 操作指南

本文檔記錄在 Kibana UI 上的各項操作與設置步驟。

## Alert Rule - CPU > 80% 告警

### STEP 1 確認 Metricbeat 有收 CPU 資料

進入：

Kibana → Analytics → Discover

Data View：

metricbeat-*

搜尋：

system.cpu.total.norm.pct

如果有：

0.1, 0.5, 0.8

代表 CPU Metrics 正常。

### STEP 2 建立 Connector

進入：

Kibana → Stack Management → Connectors

點：

Create connector

選擇：

Server log

輸入：

Connector name: "CPU usage is above 80%"

點：

Save

### STEP 3 建立 Rule

進入：

Kibana → Stack Management → Rules

點：

Create Rule

### STEP 4 選擇 Rule Type

選：

Index threshold

### STEP 5 Rule 基本設定

**Name：**

High CPU Usage > 80%

**Index：**

metricbeat-*

**Time field：**

@timestamp

**WHEN：**

avg()

**Field：**

system.cpu.total.norm.pct

**OVER：**

all documents

**Threshold：**

is above 0.8

**FOR THE LAST：**

5 minutes

**Check every：**

1 minute

### STEP 6 新增 Rule 的 Actions

在 Rule 設置頁面點：

Add action

選擇剛剛建立的 Connector：

"CPU usage is above 80%"

點：

Save

或

Create rule

### STEP 7 驗證 Rule 建立成功

進入：

Stack Management → Rules

確認：

High CPU Usage > 80%

已被新增且 Status 為 Enabled。

---

## CPU 壓力測試與 Alert 驗證

### STEP 8 安裝 stress 工具

Linux：

```bash
sudo apt install stress -y
```

### STEP 9 查看 CPU 核心數

```bash
nproc
```

### STEP 10 開始 CPU 壓力測試

使用全部 CPU 核心，持續 5 分鐘以上（避免時間不足導致 CPU 未超過 80%）：

```bash
stress --cpu $(nproc) --timeout 600
```

說明：

- `--cpu $(nproc)` 使用所有 CPU 核心
- `--timeout 600` 持續 600 秒（10 分鐘）
- 可根據需要調整 timeout

### STEP 11 查看 Kibana Metrics

進入：

Kibana → Observability → Infrastructure

Metric：

CPU Usage

應看到 CPU 飆高（接近 100%）。

### STEP 12 查看 Alert 是否觸發

進入：

Kibana → Stack Management → Alerts

應看到：

Status：

Active

表示 Alert 已觸發。

### STEP 13 查看 Rule Execution

進入：

Kibana → Stack Management → Rules → 點選 "High CPU Usage > 80%"

會看到：

rule executed: 1

代表條件成立（CPU > 80%）。

### STEP 14 停止 CPU 壓力

可等待 timeout 自動結束，或手動：

```bash
pkill stress
```

### STEP 15 驗證 Alert Recover

等待約 1 ~ 5 分鐘（Rule 判斷時間窗口為最近 5 分鐘）。

進入：

Kibana → Stack Management → Alerts

應看到：

Status：

Recovered

代表 CPU 已恢復正常，Alert 已解除。

---

## Alert 狀態說明

| 狀態 | 說明 |
|------|------|
| Active | CPU > 80%，條件符合 |
| Recovered | CPU <= 80%，條件解除 |
| rule executed: 1 | 當前執行時符合條件 |
| rule executed: 0 | 當前執行時不符合條件 |

---

## Alert Rule - Memory > 80% 告警

### STEP 1 確認 Metricbeat 有收到 Memory 資料

Discover 搜尋：

system.memory.used.pct

### STEP 2 建立 Memory Rule

進入：

Kibana → Stack Management → Rules → Create Rule

Rule Type：

Index threshold

#### Rule 設定

Name：

High Memory Usage > 80%

Index：

metricbeat-*

Condition：

WHEN average()
OF system.memory.used.pct
OVER all documents
IS ABOVE 0.8
FOR THE LAST 5 minutes

Schedule：

Check every 1 minute

### STEP 3 查看目前 Memory

```bash
free -h
```
來決定需要

### STEP 4 Memory 壓力測試

```bash
stress --vm 2 --vm-bytes 2G --timeout 600
```

說明：

- 2G可以根據free -h的結果調整，若可用memory是5G那2*2G大概就80%
- `--timeout 600` 持續 600 秒（10 分鐘）
- 可根據需要調整 timeout

### STEP 5 驗證 Memory Alert

進入：

Kibana → Observability → Infrastructure

Metric：

Memory Usage

應看到 Memory 飆高。

### STEP 6 查看 Memory Alert

進入：

Kibana → Stack Management → Alerts

應看到：

Status：

Active

### STEP 7 停止 Memory 測試

等待 timeout。

或：

```bash
pkill stress
```

### STEP 8 驗證 Memory Recover

等待：

1 ~ 5 分鐘

應看到：

Recovered = 1

---

## Alert Rule - Disk > 80% 告警

### STEP 1 確認目前 Disk 使用率

```bash
df -h
```

### STEP 2 確認 Metricbeat 有收到 Disk 資料

Discover 搜尋：
system.filesystem.device_name : "/dev/sda2"

### STEP 3 建立 Disk Rule

進入：

Kibana → Stack Management → Rules → Create Rule

Rule Type：

Index threshold

#### Rule 設定

Name：

High Disk Usage > 80%

Index：

metricbeat-*

Condition：

WHEN average()
OF system.filesystem.used.pct
OVER all documents
IS ABOVE 0.8
FOR THE LAST 5 minutes

Filter：

system.filesystem.device_name : "/dev/sda2"

Schedule：

Check every 1 minute

### STEP 4 Disk 壓力測試

方法 1：

```bash
fallocate -l 90G /tmp/bigfile
```

#### 如果 fallocate 不可用

```bash
dd if=/dev/zero of=/tmp/bigfile bs=1G count=90
```

### STEP 5 驗證 Disk Usage

```bash
df -h
```

應看到：

/dev/sda2 使用率升高。

### STEP 6 驗證 Disk Alert

進入：

Kibana → Observability → Infrastructure

Metric：

Disk Usage

應看到 Disk Usage 飆高。

### STEP 7 查看 Disk Alert

進入：

Kibana → Stack Management → Alerts

應看到：

Status：

Active

### STEP 8 清除測試檔案

```bash
rm -f /tmp/bigfile
```

### STEP 9 驗證 Disk Recover

等待：

1 ~ 5 分鐘

應看到：

Recovered = 1

---

## pam_authenticate failed Alert 練習

### STEP 1 確認 Filebeat 有收到 pam_authenticate failed Log

進入：

Kibana → Analytics → Discover

Data View：

filebeat-*

搜尋：

message : "pam_authenticate failed"

### STEP 2 建立 pam_authenticate failed Rule

進入：

Kibana → Stack Management → Rules → Create Rule

Rule Type：

Index threshold

#### Rule 設定

Name：

pam_authenticate failed Alert

Index：

filebeat-*

Condition：

WHEN count()
OVER all documents
IS ABOVE 5
FOR THE LAST 5 minutes

Filter：

message : "pam_authenticate failed"

Schedule：

Check every 1 minute

### STEP 3 測試 pam_authenticate failed

鎖定 Linux 畫面。

故意輸入錯誤密碼。

重複數次。

### STEP 4 驗證 Filebeat 是否收到

Discover 搜尋：

message : "pam_authenticate failed"

應看到：

pam_unix

pam_authenticate failed

### STEP 5 查看 pam_authenticate failed Alert

進入：

Kibana → Stack Management → Alerts

應看到：

Status：

Active

### STEP 6 停止測試

停止輸入錯誤密碼。

### STEP 7 驗證 Recover

等待：

1 ~ 5 分鐘

應看到：

Recovered = 1

---

## Rule 執行邏輯

Rule 每分鐘執行一次：

schedule interval = 1m

---

## Alert 狀態

Threshold 超過
→ Active

恢復正常
→ Recovered

---

## rule executed: 1

代表：

目前符合條件。

---

## rule executed: 0

代表：

目前不符合條件。

---


## 後續擴展

此文檔可用於記錄更多 Kibana 操作，例如：

- Dashboard 自訂與佈局
- Visualization 建立
- Saved Searches
- 其他 Alert Rules（Memory、Disk 等）
- Log 搜尋與過濾
