# MAHDI 本地构建与服务器部署

目标服务器 `8.138.102.225`，目录 `/opt/MT-wuleirencaizhinengti`，Compose 项目名 `mahdi`，公开端口 `8901`，容器端口 `8010`。其他项目、Nginx、Docker daemon 和全局防火墙均不重启。

## 本地准备与构建

在 Windows PowerShell 的项目根目录执行。后端验证使用现有 Conda `mahdi` 环境。

```powershell
docker desktop status
# 仅在 Docker Desktop 未运行时执行：
docker desktop start
docker info --format '{{.OSType}}/{{.Architecture}}'
& 'D:\anaconda\envs\mahdi\python.exe' -B -m pytest tests -q -p no:cacheprovider
$releaseTag = 'release-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
docker build --platform linux/amd64 --tag "mahdi:$releaseTag" .
```

如官方 PyPI 下载超时，可在单次构建中增加 `--build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple`；不修改全局 pip 或 Docker 配置。本次网络检查中清华镜像对 Docker 的出口返回403，因此没有采用该镜像。

如 Debian 索引下载超时，可增加 `--build-arg DEBIAN_MIRROR=https://mirrors.aliyun.com`。此参数只改变镜像内部 Debian 软件源，软件包仍通过 Debian 签名与摘要验证。

镜像通过白名单复制 Python 源码、JSON 题库、依赖清单和 HTML；不包含 `.env`、私钥、账号数据库、测试报告或本地环境。Chromium、其 Linux 依赖和中文字体在本地构建时安装。容器以 `65534:65534` 运行。

先用独立数据目录、独立端口验证最终镜像的注册、登录、两版测评与升级、讲师统计、真实 PDF、找回问题及重置链接保护，再导出镜像。发布包必须包含镜像压缩包、`compose.yaml`、`.env.example`、本说明、`RELEASE.json` 与 `SHA256SUMS`，不包含真实 `.env` 或本地数据库。

## 服务器首次部署

服务器使用 Bash，执行位置为 `/opt/MT-wuleirencaizhinengti`。上传已验证的发布包，并先核验 SHA256；不要在服务器执行 `docker build` 或下载应用依赖。

```bash
cd /opt/MT-wuleirencaizhinengti
sha256sum -c SHA256SUMS
docker load -i mahdi-linux-amd64-image.tar.gz
install -d -m 700 .ops
install -d -m 750 -o 65534 -g 65534 data
```

生成权限为 `600` 的 `.env`：设置本次 `MAHDI_IMAGE_TAG`、`MAHDI_ENV=production`、独立随机的 `MAHDI_TEACHER_PASSWORD`（至少16位）以及 `MAHDI_PUBLIC_BASE_URL=http://8.138.102.225:8901`。不要打印、提交或分享 `.env`；镜像内不包含真实密码。首次启动自动创建讲师账号 `teacher`；已有讲师密码不会随 `.env` 自动更改。

```bash
docker compose -p mahdi config --quiet
docker compose -p mahdi up -d --no-build --pull never --wait --wait-timeout 180
docker compose -p mahdi ps
curl --noproxy '*' -fsS http://127.0.0.1:8901/api/assessment/config >/dev/null
```

如果主机防火墙还未允许8901，只添加该端口：

```bash
firewall-cmd --zone=public --add-port=8901/tcp
firewall-cmd --permanent --zone=public --add-port=8901/tcp
```

不执行防火墙整体 reload。阿里云安全组也需允许 TCP 8901；以外网实际访问为验收依据。

## 数据与账号

数据库位于宿主机 `data/mahid.db`，绑定到 `/app/backend/data/mahid.db`。重建容器保留该目录。新密码使用带随机盐的 PBKDF2-SHA256 存储；旧本地账号首次成功登录时自动转换，无需改表。重置密码会使该账号旧会话失效。生产环境缺少邮件配置时关闭邮件重置申请，不返回测试重置链接。

默认不上传本地数据库，服务器独立创建账号；迁移真实用户数据须另外安排一致性备份与验证。

## 更新前检查与备份

先记录当前版本和现有其他项目容器状态。备份 `.env`、Compose 和SQLite；备份只保存在本项目 `.ops` 下，不上传分享。

```bash
cd /opt/MT-wuleirencaizhinengti
docker compose -p mahdi ps
backup_dir=".ops/backup-$(date +%Y%m%d-%H%M%S)"
install -d -m 700 "$backup_dir"
cp .env compose.yaml RELEASE.json "$backup_dir/"
docker compose -p mahdi images -q app > "$backup_dir/image.id"
docker compose -p mahdi exec -T app python -c 'import sqlite3; s=sqlite3.connect("/app/backend/data/mahid.db"); d=sqlite3.connect("/tmp/mahid-backup.db"); s.backup(d); d.close(); s.close()'
docker compose -p mahdi cp app:/tmp/mahid-backup.db "$backup_dir/mahid.db"
chmod 600 "$backup_dir"/*
```

上传新镜像包到单独的 `.ops/incoming-<release>` 目录，核验后 `docker load`，将 `.env` 的 `MAHDI_IMAGE_TAG` 改为已加载的版本。保留旧镜像；只启动 `mahdi` 项目。

```bash
docker compose -p mahdi config --quiet
docker compose -p mahdi up -d --no-build --pull never --wait --wait-timeout 180
docker compose -p mahdi ps
curl --noproxy '*' -fsS http://127.0.0.1:8901/ >/dev/null
curl --noproxy '*' -fsS http://127.0.0.1:8901/api/assessment/config >/dev/null
```

随后从外网验证登录、报告和 PDF，并对比其他容器的 ID、启动时间和重启次数。

## 回滚

首次上线失败时只停止 MAHDI：

```bash
cd /opt/MT-wuleirencaizhinengti
docker compose -p mahdi stop app
```

保留数据库和日志。若本次新增了8901防火墙规则且决定撤销上线，分别删除该端口的 runtime 和 permanent 规则；不改变其他规则。

更新回滚时，从明确选定的备份恢复 `.env` 和 `compose.yaml`，然后执行相同的 `up -d --no-build --pull never --wait` 恢复旧镜像。本次密码格式兼容迁移没有表结构变更，不自动恢复数据库；如确需恢复数据库，先停止 app、另存当前库，再恢复选定备份并设置 `65534:65534` 所有者，避免覆盖更新后新增数据。

禁止 `docker system prune`、`docker compose down -v`、重启全局Docker/Nginx、防火墙整体 reload，以及操作其他项目目录。
