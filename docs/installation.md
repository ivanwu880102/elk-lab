# 安裝與啟動

## 先決條件
- Docker 與 Docker Compose 已安裝
- `.env` 已建立並包含 `ELASTIC_PASSWORD`
- `kibana.lab.local` 已解析到本機或 VM
- `nginx/`、`kibana/`、`filebeat/`、`metricbeat/` 已配置對應設定檔

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

3. 產生自簽 TLS 憑證 (lab用)

   在 `nginx/certs` 建立自簽憑證：

   ```bash
   mkdir -p nginx/certs
   cd nginx/certs
   openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout kibana.key \
     -out kibana.crt \
   ```

   將 `kibana.crt`、`kibana.key` 放在 `nginx/certs/`，並確保 `docker-compose.yml` 已掛載該目錄。

3. 啟動 Elasticsearch

   ```bash
   docker-compose up -d es01
   ```

4. 產生 Kibana Service Token

   ```bash
   docker exec -it es01 \
     /usr/share/elasticsearch/bin/elasticsearch-service-tokens \
     create elastic/kibana kibana-token
   ```

5. 將 token 寫入 `.env`

   ```env
   KIBANA_SERVICE_TOKEN=AAEAAWVsYXN0aWM...
   ```

6. 啟動完整 Stack

   ```bash
   docker-compose up -d kibana nginx filebeat metricbeat alert-worker
   ```

   或者直接啟動全部服務：

   ```bash
   docker-compose up -d
   ```

## 主要設定檔
- `kibana/kibana.yml`：Kibana 連線 Elasticsearch、service token、加密金鑰配置。
- `nginx/default.conf`：HTTP -> HTTPS 轉向、TLS、Basic Auth、反向代理至 Kibana。
- `filebeat/filebeat.yml`：Filebeat log collection 設定。
- `metricbeat/metricbeat.yml`：Metricbeat system metrics 設定。

## Kibana Observability 注意
- `metricbeat` 已啟用 `filesystem` metricset，Kibana Observability → Infrastructure 可用 `system.filesystem.used.bytes` 檢視磁碟使用量。

## 取得 Kibana encryption keys
如果你尚未有 `kibana/kibana.yml` 或還沒設定加密金鑰，請直接在 Kibana container 裡使用官方工具產生：

```bash
docker exec -it kibana bash
bin/kibana-encryption-keys generate
```

會看到輸出：

```text
xpack.encryptedSavedObjects.encryptionKey: "xxxxx"
xpack.reporting.encryptionKey: "xxxxx"
xpack.security.encryptionKey: "xxxxx"
```

把這三組 key 直接寫入 `kibana/kibana.yml`，並重啟 Kibana。

## 實驗室注意事項
- `nginx/.htpasswd` 需在啟動前建立，且不應加入版本控制。
- `filebeat` / `metricbeat` 目前以 `elastic` 密碼直接輸出到 Elasticsearch，僅適用實驗室測試。
- 若 `esdata01` volume 已存在，`ELASTIC_PASSWORD` 不會覆蓋舊密碼。
- 若 `https://kibana.lab.local` 無法存取，請先檢查 hosts 解析與 SSL 憑證。

## 檢查
```bash
docker-compose ps
docker logs --tail=20 -f es01
docker logs --tail=20 -f kibana
docker logs --tail=20 -f nginx-kibana
docker logs --tail=20 -f filebeat
docker logs --tail=20 -f metricbeat
```

提示：如果你在 container 內修改檔案（或更新了 `kibana/kibana.yml` 等），請參考 `docs/dockerscript.md` 的「在容器內修改後重建 / 排除故障」一節，使用 `docker-compose up -d --build <container_name>` 或在必要時先 `docker rm -f <container_name>` 再重建。

