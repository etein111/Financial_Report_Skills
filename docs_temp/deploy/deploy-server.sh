#!/bin/bash
#=============================================================================
# NeoSkills 服务器部署脚本
# 用于在 Linux 服务器上部署 FileBrowser + 配置用户隔离
#=============================================================================

set -e

# 配置变量
DATA_BASE_DIR="/data"
FILEBROWSER_PORT=8081
FILEBROWSER_DATA_DIR="/data/filebrowser"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

#-----------------------------------------------------------------------------
# 1. 创建目录结构
#-----------------------------------------------------------------------------
log_info "创建目录结构..."
mkdir -p ${DATA_BASE_DIR}/filebrowser
mkdir -p ${DATA_BASE_DIR}/input        # 全局输入目录（可选）
mkdir -p ${DATA_BASE_DIR}/output       # 全局输出目录（可选）

#-----------------------------------------------------------------------------
# 2. 检查 Docker
#-----------------------------------------------------------------------------
log_info "检查 Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi
docker --version

#-----------------------------------------------------------------------------
# 3. 停止并删除旧的 FileBrowser 容器（如果存在）
#-----------------------------------------------------------------------------
log_info "清理旧容器..."
docker stop filebrowser 2>/dev/null || true
docker rm filebrowser 2>/dev/null || true

#-----------------------------------------------------------------------------
# 4. 启动 FileBrowser
#-----------------------------------------------------------------------------
log_info "启动 FileBrowser..."

# 创建 FileBrowser 配置目录
mkdir -p ${FILEBROWSER_DATA_DIR}

# 运行 FileBrowser
docker run -d \
    --name filebrowser \
    --restart=unless-stopped \
    -p ${FILEBROWSER_PORT}:80 \
    -v /:/data \
    -v ${FILEBROWSER_DATA_DIR}/filebrowser.db:/database.db \
    -e PUID=1000 \
    -e PGID=1000 \
    filebrowser/filebrowser:latest

#-----------------------------------------------------------------------------
# 5. 等待 FileBrowser 启动
#-----------------------------------------------------------------------------
log_info "等待 FileBrowser 启动..."
sleep 3

# 检查容器状态
if docker ps | grep -q filebrowser; then
    log_info "FileBrowser 启动成功！"
else
    log_error "FileBrowser 启动失败，请检查日志"
    docker logs filebrowser
    exit 1
fi

#-----------------------------------------------------------------------------
# 6. 获取服务器 IP
#-----------------------------------------------------------------------------
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

#-----------------------------------------------------------------------------
# 7. 输出信息
#-----------------------------------------------------------------------------
echo ""
echo "============================================================================="
echo "                      部署完成！                      "
echo "============================================================================="
echo ""
echo "访问地址："
echo "  FileBrowser: http://${SERVER_IP}:${FILEBROWSER_PORT} (文件上传/下载)"
echo ""
echo "默认管理员账号："
echo "  用户名: admin"
echo "  密码: admin"
echo "  （首次登录后请修改密码）"
echo ""
echo "============================================================================="
echo ""
echo "后续步骤："
echo "  1. 登录 FileBrowser 修改管理员密码"
echo "  2. 创建业务人员账号（建议与 OpenCode 用户名一致）"
echo "  3. 为每个用户创建独立的 input/output 目录"
echo "  4. 在 OpenCode 中配置用户工作目录"
echo ""
echo "创建用户目录命令："
echo "  ./init-user-dirs.sh <username>"
echo ""
