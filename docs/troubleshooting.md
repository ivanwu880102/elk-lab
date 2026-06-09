# 常見問題排查

## 1. Kibana container 一直 restart

### 可能原因
- `KIBANA_SERVICE_TOKEN` 未設定或值錯誤
- Elasticsearch 尚未啟動完成
- Kibana 無法透過 token 連線 Elasticsearch

### 排查步驟
```bash
docker-compose ps
docker logs --tail=50 kibana
```

### 解決方式
1. 確認 `es01` 已啟動且健康。
2. 確認 `.env` 中 `KIBANA_SERVICE_TOKEN` 是否正確。
3. 重新產生 token 並重啟 Kibana：

```bash
docker exec -it es01 \
  /usr/share/elasticsearch/bin/elasticsearch-service-tokens \
  create elastic/kibana kibana-token
```

## 2. Kibana 需要 encryption key

### 錯誤
Unable to create actions client because the Encrypted Saved Objects plugin is missing encryption key

### 原因
Kibana `kibana.yml` 未設定必要的 `xpack` encryption keys。

### 解法
在 `kibana/kibana.yml` 加入：

```yaml
xpack.encryptedSavedObjects.encryptionKey: "<your-key>"
xpack.reporting.encryptionKey: "<your-key>"
xpack.security.encryptionKey: "<your-key>"
```

### 範例（常見情境）

錯誤範例：在 Kibana UI（Management > Stack Management > Rules）新增 rule 時會看到：

```json
{
  "name": "Error",
  "body": {
    "message": "Unable to create actions client because the Encrypted Saved Objects plugin is missing encryption key. Please set xpack.encryptedSavedObjects.encryptionKey in the kibana.yml or use the bin/kibana-encryption-keys command.",
    "status_code": 500
  },
  "message": "Internal Server Error"
}
```

原因：Kibana 尚未有加密金鑰配置，因此 Rules 相關的 action client 無法建立。

解決方法：先在 Kibana container 裡執行 `bin/kibana-encryption-keys generate` 產生金鑰，然後再將輸出的三組金鑰寫入 `kibana/kibana.yml`。

具體修復步驟：

### 直接在 Kibana container 產生金鑰
1. 確保 Kibana container 已啟動：

```bash
docker-compose up -d kibana
```

2. 進入 Kibana container：

```bash
docker exec -it kibana bash
```

3. 產生金鑰：

```bash
bin/kibana-encryption-keys generate
```

4. 依序將輸出的三個 key 複製到 `kibana/kibana.yml`：

```yaml
xpack.encryptedSavedObjects.encryptionKey: "xxxxx"
xpack.reporting.encryptionKey: "xxxxx"
xpack.security.encryptionKey: "xxxxx"
```

5. 產出金鑰寫入 `kibana.yml`（示例）：

```bash
mkdir -p kibana
cat > kibana/kibana.yml <<'EOF'
server.host: "0.0.0.0"
server.publicBaseUrl: "https://kibana.lab.local"

elasticsearch.hosts: ["http://es01:9200"]
elasticsearch.serviceAccountToken: "${KIBANA_SERVICE_TOKEN}"

xpack.encryptedSavedObjects.encryptionKey: "4075fb35bb1a01cce7e88a1df3dde10b"
xpack.reporting.encryptionKey: "b5084ca7f196ef0d438db08a973ba194"
xpack.security.encryptionKey: "fb39f0ae34b5fbe91af7bf918117dce2"
EOF
```

6. 在 `docker-compose.yml` 的 `kibana` 服務掛載該檔案（示例）：

```yaml
kibana:
  image: docker.elastic.co/kibana/kibana:8.17.3
  container_name: kibana
  environment:
    - KIBANA_SERVICE_TOKEN=${KIBANA_SERVICE_TOKEN}
  volumes:
    - ./kibana/kibana.yml:/usr/share/kibana/config/kibana.yml:ro
  depends_on:
    - es01
  networks:
    - elastic
  restart: unless-stopped
```

7. 重新建立/啟動 Kibana（只重建 Kibana 即可）：

```bash
docker-compose up -d --force-recreate --no-deps kibana
# 或
docker-compose up -d kibana nginx
```

8. 驗證：在 Kibana UI 再次建立 rule，錯誤應已消失。


## 3. Nginx 顯示 502 Bad Gateway

### 可能原因
- Kibana container 未啟動
- Nginx 無法連到 `kibana:5601`
- Docker network 或 container DNS 有問題

### 排查步驟
```bash
docker-compose ps
docker logs --tail=50 nginx-kibana
```

### 解決方式
1. 確認 `kibana` container 已啟動。
2. 確認 `nginx/default.conf` 的 `proxy_pass http://kibana:5601;` 正確。
3. 重新啟動服務：

```bash
docker-compose restart kibana nginx
```

## 4. Docker Compose environment 格式錯誤

### 錯誤
contains invalid type, it should be a string

### 原因
`docker-compose.yml` 中混用 `- KEY=VALUE` 與 `key: value`。

### 解法
統一 environment 格式：

```yaml
environment:
  - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
  - KIBANA_SERVICE_TOKEN=${KIBANA_SERVICE_TOKEN}
```

或改用外部設定檔 `kibana/kibana.yml`。

## 5. Metricbeat / Filebeat Dashboard 沒資料

### 可能原因
- Beat 尚未完成 setup
- Beats 無法連線 Elasticsearch

### 排查步驟
```bash
docker-compose ps
docker logs --tail=50 filebeat
docker logs --tail=50 metricbeat
```

### 解法
```bash
docker exec -it filebeat bash
filebeat setup

docker exec -it metricbeat bash
metricbeat setup
```

## 6. `kibana.lab.local` 無法解析

### 可能原因
- hosts 未設定
- DNS 解析錯誤

### 排查步驟
```bash
ping kibana.lab.local
```

### 解決方式
1. 編輯 hosts 檔案。
2. 確認 IP 為 Docker 主機或 VM 的實際地址。

## 7. Elasticsearch 連線失敗

### 排查步驟
```bash
docker logs --tail=50 es01
```

### 建議
檢查 Elasticsearch 是否啟動完成，並讀取 cluster health：

```bash
docker exec -it es01 curl -u elastic:'你的密碼' \
  http://localhost:9200/_cluster/health?pretty
```