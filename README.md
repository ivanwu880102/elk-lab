# ELK Lab Docker Compose

這個專案透過 Docker Compose 建置單機 ELK Stack，並使用 Nginx 作為 Kibana 的反向代理。

本專案包含：HTTPS/TLS、Elasticsearch Security、Kibana Service Token、Filebeat、Metricbeat。

配置檔案位置：
- `nginx/default.conf`
- `nginx/certs/kibana.crt`, `nginx/certs/kibana.key`
- `kibana/kibana.yml`
- `filebeat/filebeat.yml`
- `metricbeat/metricbeat.yml`

## 先決條件
- Docker 與 Docker Compose 已安裝
- `.env` 已建立，且包含 `ELASTIC_PASSWORD`
- `kibana.lab.local` 已解析至本機或 VM

## 快速啟動
1. 建立 `.env`

   ```env
   ELASTIC_PASSWORD=YourElasticPassword123!
   KIBANA_SERVICE_TOKEN=
   ```

2. 建立 Nginx Basic Auth

   ```bash
   sudo apt install apache2-utils -y
   htpasswd -c nginx/.htpasswd admin
   ```

3. 產生自簽 TLS 憑證

   若你希望使用自簽憑證 (適用於實驗室)，可在 `nginx/certs` 目錄執行：

   ```bash
   mkdir -p nginx/certs
   cd nginx/certs
   openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout kibana.key \
     -out kibana.crt \
   ```

   將產生的 `kibana.crt` 與 `kibana.key` 掛載到 `nginx/certs/`。

3. 啟動 Elasticsearch

   ```bash
   docker-compose up -d es01
   ```

4. 建立 Kibana Service Token

   ```bash
   docker exec -it es01 \
     /usr/share/elasticsearch/bin/elasticsearch-service-tokens \
     create elastic/kibana kibana-token
   ```

5. 將 token 寫入 `.env`

   ```env
   KIBANA_SERVICE_TOKEN=AAEAAWVsYXN0aWM...
   ```

6. 啟動整個 stack

   ```bash
   docker-compose up -d kibana nginx filebeat metricbeat
   ```

   或者：

   ```bash
   docker-compose up -d
   ```

## 開啟 Kibana

```text
https://kibana.lab.local
```

## 注意事項
- `esdata01` volume 若已存在，`ELASTIC_PASSWORD` 不會覆蓋舊密碼。
1. 更改密碼
```bash
docker exec -it es01 \
/usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
```

2. 測試新密碼
```bash
docker exec -it es01 \
curl -u elastic:'新密碼' http://localhost:9200
```

- `.env` 與 `nginx/.htpasswd` 不應加入版本控制。
- 若 `kibana.lab.local` 無法存取，請先確認 hosts 設定。

## 文件總覽
- `docs/installation.md` — 安裝與初始化（建立 `.env`、產生 TLS 憑證、啟動 services 的快速步驟）。
- `docs/troubleshooting.md` — 常見問題與排查（Kibana encryption key、認證錯誤、重建容器指引）。
- `docs/backup.md` — 備份與還原（Elasticsearch 資料卷備份與還原流程）。
- `docs/architecture.md` — 系統架構總覽（服務關係、nginx 反向代理、Beats 與資料流程）。
- `docs/dockerscript.md` — 常用 Docker 指令集（重建、清除、快速部署腳本）。
- `docs/kibana-guide.md` — Kibana UI 操作指南（建立 Rules、Alerts、Dashboard 的步驟與範例）。
- `docs/alert-worker.md` — Alert-worker（Discord）設定與測試指南（Webhook 設定、部署與測試）。

詳細步驟與範例請參閱各文件。
