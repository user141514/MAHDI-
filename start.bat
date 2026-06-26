@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set HOST=127.0.0.1
set PORT=8010
set URL=http://%HOST%:%PORT%
set DATA_FILE=backend\data\mahid.db

title MAHDI Local Test Server

echo ============================================================
echo   MAHDI 五类人才测评 - 本地手动测试
echo ============================================================
echo.
echo 项目目录: %cd%
echo 访问地址: %URL%
echo 数据文件: %DATA_FILE%
echo 讲师账号: teacher
echo 讲师密码: meitai123456
echo.
echo 测试建议:
echo   1. 先注册一个学员账号
echo   2. 完成一次测评并提交结果
echo   3. 退出后用讲师账号登录
echo   4. 进入讲师数据看板查看学员结果
echo.
echo 按 Ctrl+C 可以停止服务。
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo [错误] 没有检测到 Python。请先安装 Python，或确认 python 已加入 PATH。
  pause
  exit /b 1
)

if not exist "backend\data" mkdir "backend\data"

echo [1/4] 检查依赖...
python -c "import fastapi, uvicorn, pydantic" >nul 2>&1
if errorlevel 1 (
  echo [依赖缺失] 正在安装 requirements.txt ...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
  )
) else (
  echo [OK] 依赖已存在。
)

echo.
echo [2/4] 初始化本地 SQLite 和默认讲师账号...
python -c "from backend.storage import init_db; from backend.auth_local import ensure_teacher; init_db(); ensure_teacher(); print('database ready')"
if errorlevel 1 (
  echo [错误] 数据库初始化失败。
  pause
  exit /b 1
)

echo.
echo [3/4] 打开浏览器...
start "" "%URL%"

echo.
echo [4/4] 启动后端服务...
echo.
python -m uvicorn backend.app:app --host %HOST% --port %PORT% --reload

echo.
echo 服务已停止。
pause
endlocal
