# Volume 備份與還原

本專案的 Elasticsearch 資料儲存在 Docker volume `esdata01`。

## 備份
建議使用 Docker container 讀取 volume 並建立 tar 包。

```bash
docker run --rm \
  -v esdata01:/data \
  -v ${PWD}:/backup \
  alpine sh -c "cd /data && tar czf /backup/esdata01-backup.tgz ."
```

備份檔會存放在當前目錄 `esdata01-backup.tgz`。

## 還原
還原前請先停止 Elasticsearch：

```bash
docker-compose stop es01
```

執行還原：

```bash
docker run --rm \
  -v esdata01:/data \
  -v ${PWD}:/backup \
  alpine sh -c "cd /data && tar xzf /backup/esdata01-backup.tgz"
```

完成後重新啟動 Elasticsearch：

```bash
docker-compose up -d es01
```

## 注意事項
- 若要建立新的備份 volume，可改用不同 volume 名稱。
- Windows 使用者可在 WSL 或 Git Bash 下執行上述命令。
- 這個備份只包含 Elasticsearch 資料，不包含 Nginx `.htpasswd` 或 `.env`。

## 使用腳本備份/還原
本專案也提供可執行腳本：

```bash
./scripts/backup.sh esdata01-backup.tgz
./scripts/restore.sh esdata01-backup.tgz
```

如果腳本無法執行，請先給予執行權限：

```bash
chmod +x scripts/backup.sh scripts/restore.sh
```
