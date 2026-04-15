@echo off
REM iQuant 监控系统启动脚本 (Windows)
REM 用法: start_monitoring.bat [full|core|stop]

echo =====================================
echo   iQuant 监控系统启动脚本
echo =====================================
echo.

if "%1"=="" goto full
if "%1"=="full" goto full
if "%1"=="core" goto core
if "%1"=="flask" goto flask
if "%1"=="stop" goto stop
if "%1"=="status" goto status
if "%1"=="logs" goto logs

goto usage

:full
echo 启动完整监控栈（包括 Prometheus + Grafana + Flower）...
docker-compose --profile monitoring up -d
echo.
echo ✓ 所有服务已启动！
echo.
echo 访问以下面板：
echo   FastAPI API:      http://localhost:8000
echo   API 文档:         http://localhost:8000/api/docs
echo   Prometheus:       http://localhost:9090
echo   Grafana:          http://localhost:3000 (admin/admin)
echo   Flower:           http://localhost:5555
echo.
goto end

:core
echo 启动核心服务（不含监控组件）...
docker-compose up -d
echo.
echo ✓ 核心服务已启动！
echo.
echo 访问以下面板：
echo   FastAPI API:      http://localhost:8000
echo   API 文档:         http://localhost:8000/api/docs
echo.
goto end

:flask
echo 启动 Flask 应用（模板渲染）...
docker-compose --profile flask up -d
echo.
echo ✓ Flask 应用已启动！
echo.
echo 访问以下面板：
echo   Flask App:        http://localhost:5000
echo.
goto end

:stop
echo 停止所有服务...
docker-compose --profile monitoring down
echo.
echo ✓ 所有服务已停止！
echo.
goto end

:status
echo 查看服务状态...
docker-compose --profile monitoring ps
echo.
goto end

:logs
echo 查看日志（Ctrl+C 退出）...
docker-compose --profile monitoring logs -f
goto end

:usage
echo 用法: %0 {full^|core^|flask^|stop^|status^|logs}
echo.
echo 选项说明：
echo   full   - 启动完整监控栈（默认）
echo   core   - 仅启动核心服务
echo   flask  - 启动 Flask 应用
echo   stop   - 停止所有服务
echo   status - 查看服务状态
echo   logs   - 查看所有日志
exit /b 1

:end
