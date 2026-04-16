#!/bin/bash
# iQuant 监控系统启动脚本
# 用法: ./start_monitoring.sh [full|core|stop]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  iQuant 监控系统启动脚本${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

case "${1:-full}" in
    full)
        echo -e "${YELLOW}启动完整监控栈（包括 Prometheus + Grafana + Flower）...${NC}"
        docker-compose --profile monitoring up -d
        echo ""
        echo -e "${GREEN}✓ 所有服务已启动！${NC}"
        echo ""
        echo -e "访问以下面板："
        echo -e "  ${YELLOW}FastAPI API:${NC}      http://localhost:8000"
        echo -e "  ${YELLOW}API 文档:${NC}         http://localhost:8000/api/docs"
        echo -e "  ${YELLOW}Prometheus:${NC}       http://localhost:9090"
        echo -e "  ${YELLOW}Grafana:${NC}          http://localhost:3000 (admin/admin)"
        echo -e "  ${YELLOW}Flower:${NC}           http://localhost:5555"
        echo ""
        ;;

    core)
        echo -e "${YELLOW}启动核心服务（不含监控组件）...${NC}"
        docker-compose up -d
        echo ""
        echo -e "${GREEN}✓ 核心服务已启动！${NC}"
        echo ""
        echo -e "访问以下面板："
        echo -e "  ${YELLOW}FastAPI API:${NC}      http://localhost:8000"
        echo -e "  ${YELLOW}API 文档:${NC}         http://localhost:8000/api/docs"
        echo ""
        ;;

    stop)
        echo -e "${YELLOW}停止所有服务...${NC}"
        docker-compose --profile monitoring down
        echo ""
        echo -e "${GREEN}✓ 所有服务已停止！${NC}"
        echo ""
        ;;

    status)
        echo -e "${YELLOW}查看服务状态...${NC}"
        docker-compose --profile monitoring ps
        echo ""
        ;;

    logs)
        echo -e "${YELLOW}查看日志（Ctrl+C 退出）...${NC}"
        docker-compose --profile monitoring logs -f
        ;;

    *)
        echo -e "${RED}用法: $0 {full|core|stop|status|logs}${NC}"
        echo ""
        echo "选项说明："
        echo "  full   - 启动完整监控栈（默认）"
        echo "  core   - 仅启动核心服务"
        echo "  stop   - 停止所有服务"
        echo "  status - 查看服务状态"
        echo "  logs   - 查看所有日志"
        exit 1
        ;;
esac
