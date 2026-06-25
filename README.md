# MAHDI 五类人才评测

MAHDI 五类人才模型测评工具，包含单页测评前端和轻量本地后端。

## 当前能力

- 学员注册 / 登录界面
- 学员完成 44 题 MAHDI 测评
- 测评结果写入本地 SQLite 文件
- 讲师端查看全部学员测评结果
- 讲师端导出 CSV
- 学员可通过注册时设置的找回问题重置密码

## 启动

双击：

```bat
start.bat
```

或手动运行：

```bash
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010 --reload
```

打开：

```text
http://localhost:8010
```

## 默认讲师账号

```text
teacher
meitai123456
```

## 数据存储

本项目使用轻量本地 SQLite：

```text
backend/data/mahid.db
```

该文件已被 `.gitignore` 忽略，不会提交到 Git。

## 邮件重置配置

后端已接入邮件重置申请接口：

```text
/api/account/mail/start
```

可选环境变量：

```text
MAHDI_MAIL_HOST
MAHDI_MAIL_PORT
MAHDI_MAIL_USER
MAHDI_MAIL_KEY
MAHDI_MAIL_FROM
MAHDI_MAIL_FROM_NAME
MAHDI_MAIL_TLS
MAHDI_MAIL_SSL
MAHDI_PUBLIC_BASE_URL
```

未配置邮件服务时，后端会返回本地测试链接，便于开发调试。

## 说明

当前版本目标是短期内满足本地/局域网部署：学员提交测评后，讲师账号可以查看学员数据。后续如需公网多人长期使用，可再迁移到 PostgreSQL 或云数据库。
