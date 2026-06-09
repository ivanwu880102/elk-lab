# 常用 Docker 指令

## 啟動服務
```bash
docker-compose up -d es01
docker-compose up -d kibana nginx filebeat metricbeat
docker-compose up -d
```

## 停止服務
```bash
docker-compose stop
docker-compose down
```

## 重新建立 Kibana
```bash
docker-compose up -d --force-recreate kibana
```

## 檢查狀態
```bash
docker-compose ps
docker ps
docker volume ls
```

## 查看日誌
```bash
docker logs --tail=50 es01
docker logs --tail=50 kibana
docker logs --tail=50 nginx-kibana
docker logs --tail=50 filebeat
docker logs --tail=50 metricbeat
```

## Filebeat / Metricbeat 加入DashBoard
```bash
docker exec -it filebeat bash
filebeat setup

docker exec -it metricbeat bash
metricbeat setup
```

## Elasticsearch 相關
```bash
docker exec -it es01 \
  /usr/share/elasticsearch/bin/elasticsearch-service-tokens \
  create elastic/kibana kibana-token
docker exec -it es01 \
  curl -u elastic:'你的密碼' http://localhost:9200
```

## Volume
```bash
docker volume inspect esdata01
```

## 在容器內修改後重建 / 排除故障

如果你在容器內修改了設定（例如手動編輯檔案或產生金鑰），需要重建或重啟該容器：

```bash
# 重新建構並啟動單一 container（會使用 Dockerfile 或 image 的設定）
docker-compose up -d --build container_name

# 若 container 狀態異常，可先移除後重建
docker rm -f container_name
docker-compose up -d --build container_name
```

替換 `container_name` 為 `kibana`、`es01`、`nginx-kibana` 等服務名稱。

注意：若是修改映射到 container 的本機檔案（如 `kibana/kibana.yml`），通常只需重啟對應 container 即可；若改變 image 或 Dockerfile，請使用 `--build`。