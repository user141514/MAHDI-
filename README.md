# MAHDI 五类人才评测

MAHDI 五类人才模型测评工具，包含单页测评前端和轻量本地后端。

## 当前能力

- 学员注册 / 登录界面
- 单入口选择精简版（默认12题，可配10–20题）或完整版（44题）
- 服务端统一评分，标准化得分、倾向强度、近分复合型结论与算法版本可追溯
- 精简版四块报告，可继承答案升级完整版，仅补未答题目
- 测评结果写入本地 SQLite 文件
- 管理员端查看全部学员测评结果
- 管理员端导出 CSV
- 管理员端查看双版本选择与完成比例；学员导出当前已保存报告PDF
- 完整版雷达以已保存主类型的 E/K/I/L/P 五维得分展示，标题为“主类型名称五维倾向得分”；复合型使用中性参考标题，页面与PDF一致
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

## 默认管理员账号

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

## 1019配置与验收

`backend/assessment_config.json` 控制 `lite_question_count` 和 `algorithm_version`（默认 `standard_v3`，保留 `standard_v2` / `legacy_v1` 回放）。v3 在五类标准分转为展示分前减去共同偏移，避免五类同时逼近上限后舍入并列。新选择读取新配置；进行中和历史结果保留自己的配置快照。题库与五类定义统一存放在 `backend/assessment_bank.json`。旧的客户端计分提交接口 `/api/results` 已停用，历史结果仍可读取和导出。

```bash
python -m pytest tests -q
python scripts/validate_assessment.py --synthetic
```

新算法采用理论选项分布的 z-score/CDF 映射，不宣称真实人群常模。模拟样本、浏览器验收、接口与回滚说明见 [1019验收记录](docs/acceptance/2026-10-26-mahid.md)。

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

当前版本目标是短期内满足本地/局域网部署：学员提交测评后，管理员账号可以查看学员数据。后续如需公网多人长期使用，可再迁移到 PostgreSQL 或云数据库。
