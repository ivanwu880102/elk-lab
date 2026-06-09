# 架構與網路說明

## 服務拓撲

```text
[Browser] -> [Nginx HTTPS] -> [Kibana] -> [Elasticsearch]
[Filebeat] ----> [Elasticsearch]
[Metricbeat] ---> [Elasticsearch]
```

## 連線流程
1. 使用者透過瀏覽器連到 `https://kibana.lab.local`
2. Nginx 先做 HTTP -> HTTPS 轉向，並進行 Basic Auth
3. 驗證通過後，Nginx 將請求轉發給內部 `kibana` container
4. Kibana 透過 `kibana/kibana.yml` 中的 `elasticsearch.serviceAccountToken` 與 Elasticsearch 建立安全連線
5. Filebeat / Metricbeat 透過內部 network 直接將資料送到 Elasticsearch

## 主要元件
- `nginx`
  - 監聽 host port 80、443
  - 80 轉向到 443
  - 使用自簽 SSL 憑證進行 TLS
  - `auth_basic` 做第一層認證
  - 反向代理至 `kibana:5601`

- `kibana`
  - 透過 `kibana/kibana.yml` 讀取 `server.publicBaseUrl`, `elasticsearch.hosts`, `elasticsearch.serviceAccountToken`
  - 支援 `xpack.encryptedSavedObjects.encryptionKey`, `xpack.reporting.encryptionKey`, `xpack.security.encryptionKey`

- `es01`
  - Elasticsearch 單節點模式
  - `xpack.security.enabled=true`
  - 資料寫入 volume `esdata01`

- `filebeat`
  - 讀取 host 日誌
  - 透過 `output.elasticsearch` 發送資料到 Elasticsearch
  - `setup.kibana` 用於註冊 Kibana Dashboard

- `metricbeat`
  - 收集系統 metrics
  - 透過 `output.elasticsearch` 發送資料到 Elasticsearch
  - `setup.kibana` 用於註冊 Metricbeat Dashboard
  - 包含 `filesystem` 與 `fsstat` 指標，Kibana Observability → Infrastructure 可查看 `system.filesystem.used.bytes` 來監控磁碟使用量

## Docker network
- 使用 `elastic` 自定義 network
- 所有 service 均加入同一 network
- 外部只暴露 Nginx 的 80/443 port

## 重要安全設計
- Kibana 不直接對外開放 5601
- Nginx 提供 HTTPS + Basic Auth
- Kibana 與 Elasticsearch 之間使用 service token 連線
- Kibana `encryptionKey` 相關設定保護 Saved Objects 與 Reporting

