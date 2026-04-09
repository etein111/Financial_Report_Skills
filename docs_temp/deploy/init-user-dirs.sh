#!/bin/bash
#=============================================================================
# 用户目录初始化脚本
# 为每个业务人员创建独立的 input/output 目录
#=============================================================================

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "Usage: $0 <username>"
    echo ""
    echo "Example:"
    echo "  $0 test    # 创建 alice 用户的目录"
    echo "  $0 yang      # 创建 bob 用户的目录"
    exit 1
fi

# 配置
DATA_BASE_DIR="/data"

# 创建用户目录
echo "Creating directories for user: $USERNAME"

mkdir -p ${DATA_BASE_DIR}/${USERNAME}/input
mkdir -p ${DATA_BASE_DIR}/${USERNAME}/output

# 设置权限（需要根据实际情况调整）
chmod 755 ${DATA_BASE_DIR}/${USERNAME}
chmod 755 ${DATA_BASE_DIR}/${USERNAME}/input
chmod 755 ${DATA_BASE_DIR}/${USERNAME}/output

echo ""
echo "Done! Created:"
echo "  /data/${USERNAME}/input/   - 上传文件目录"
echo "  /data/${USERNAME}/output/  - 输出文件目录"
echo ""
echo "在 FileBrowser 中："
echo "  1. 创建用户 '$USERNAME'"
echo "  2. 设置该用户只能访问 /data/${USERNAME} 目录"
