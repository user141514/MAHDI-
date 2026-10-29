# MAHDI 服务器部署验收

日期：2026-10-27，时区 Asia/Shanghai。用户在本次对话明确授权本地构建打包并部署指定目录、8901端口，要求不影响其他项目。

## 发布

- 访问地址：<http://8.138.102.225:8901>
- 服务器目录：`/opt/MT-wuleirencaizhinengti`
- Compose 项目 / 容器：`mahdi` / `mahdi-app-1`
- 平台 / 镜像：`linux/amd64` / `mahdi:release-20261027-210358`
- 最终镜像 ID：`sha256:5149dcb8def908fe208f55fba9e262fe6b139778b76a80b40414602bfeae5c32`
- 本地发布包目录：`.ops/releases/release-20261027-210358`
- 镜像压缩包：436309125 bytes；包内 `SHA256SUMS` 在服务器全部验证通过，导入后的镜像 ID 与本地验收镜像一致。
- 数据挂载：宿主机 `data/` → 容器 `/app/backend/data/`。未上传本地数据库。

## 证据

| 项目 | 实际结果 |
|---|---|
| 自动化回归 | `mahdi` Conda环境：69 passed，3 subtests passed；2条既有FastAPI启动事件弃用提醒 |
| 模拟评分诊断 | 100条分布样本、30组双版对照通过；仅证明模拟输入，不代表真实人群有效性 |
| 独立只读复核 | 认证和隔离配置已复核；首次部署脚本的命名空间、符号链接及校验清单保护补齐并复审通过 |
| 最终 Linux 镜像 API | 注册、登录、12题精简版、继承后补32题、44题完整版、讲师结果和统计全部通过 |
| 最终 Linux 镜像 PDF | 实际Chromium生成；精简版336354 bytes，完整版834970 bytes；浏览器真实下载PDF通过 |
| 浏览器流程 | 真实注册→精简版报告→PDF下载→完整版升级；无页面异常或控制台错误 |
| 移动端 | 390px宽度无横向溢出，完整报告流程通过 |
| 容器约束与持久化 | UID 65534；根目录只读；3个合成账号的密码均为哈希；4条合成结果在本地容器重启后保持一致 |
| 服务器启动 | `docker compose up --no-build --pull never --wait` 通过，容器healthy；服务器没有构建或下载应用依赖 |
| 公网访问 | 直接绕过代理访问首页HTTP200，公开配置12/44题；真实浏览器公网登录并显示两个版本入口 |
| 生产认证 | 新讲师配置密码登录通过，旧默认密码被拒绝；邮件未配置返回503，不返回调试重置链接；服务器账号均为哈希 |
| 线上数据 | 创建独立学员测试账号 `teststudent`，登录通过；验收时线上结果为0条，没有上传本地合成测评结果 |
| 其他项目 | 从最初盘点到部署后，两次比较原有25个容器的ID、启动时间与重启次数，均未变化；部署后总计26个运行容器 |
| 公共服务 | 未修改Nginx路由，未重启Docker/Nginx/firewalld；仅为public zone新增TCP8901的runtime和permanent规则 |

真实凭据不写入本记录。生产讲师密码仅保存在服务器权限受限的 `.env`，学员测试密码通过对话交付。

## 可复验位置

- 本地 `.ops/image-api-smoke.json`、`image-browser-smoke.json`、`image-persistence-smoke.json`
- 本地 `.ops/public-browser-verification.json`、`server-isolation-verification.json`
- 本地 `.ops/releases/release-20261027-210358/RELEASE.json` 与 `SHA256SUMS`
- 服务器 `.ops/deployment-record.json` 与 `.ops/containers-before.json`

更新前检查、SQLite一致性备份、更新、验证和回滚步骤见 [部署说明](../DEPLOYMENT.md)。

边界：最终镜像的完整测评与真实PDF在本地Linux容器中验证；线上验证首页、配置、认证和实际浏览器登录，未向线上提交合成测评结果。HTTPS与域名配置不在本次指定8901端口部署范围内。
