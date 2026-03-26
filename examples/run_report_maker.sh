#!/bin/bash
# 示例：使用 report_maker 处理报告
# 此脚本演示如何验证 report_maker 环境和运行测试

set -e

echo "==================================="
echo "  report_maker 环境验证和测试脚本"
echo "==================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 已安装"
        return 0
    else
        echo -e "${RED}✗${NC} $1 未安装"
        return 1
    fi
}

# 检查 Python 模块
check_python_module() {
    if $PYTHON -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python 模块 $1"
        return 0
    else
        echo -e "${RED}✗${NC} Python 模块 $1 未安装"
        return 1
    fi
}

# 步骤 1: 检查环境
echo "步骤 1: 检查环境"
echo "-------------------"

# 优先使用 python3
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}错误: 未找到 Python${NC}"
    echo "请安装 Python 3.8 或更高版本"
    exit 1
fi

echo -e "${GREEN}✓${NC} 使用 Python: $PYTHON"
$PYTHON --version

check_command uv || {
    echo -e "${YELLOW}警告: uv 未安装，推荐使用 uv 管理依赖${NC}"
    echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh"
}

echo ""

# 步骤 2: 检查依赖
echo "步骤 2: 检查 Python 依赖"
echo "---------------------"

MISSING_DEPS=0
check_python_module docx || MISSING_DEPS=1
check_python_module docxtpl || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}缺少依赖，正在尝试安装...${NC}"
    if command -v uv &> /dev/null; then
        uv pip install python-docx docxtpl
    else
        pip install python-docx docxtpl
    fi

    # 重新检查
    echo ""
    echo "重新检查依赖..."
    check_python_module docx || { echo -e "${RED}依赖安装失败${NC}"; exit 1; }
    check_python_module docxtpl || { echo -e "${RED}依赖安装失败${NC}"; exit 1; }
fi

echo ""

# 步骤 3: 检查 skill 文件
echo "步骤 3: 检查 skill 文件"
echo "--------------------"

SKILL_FILES=(
    "skills/report_maker/SKILL.md"
    "skills/report_maker/scripts/common.py"
    "skills/report_maker/scripts/extractor.py"
    "skills/report_maker/scripts/splitter.py"
    "skills/report_maker/scripts/renderer.py"
)

for file in "${SKILL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file 未找到"
        exit 1
    fi
done

echo ""

# 步骤 4: 检查模板文件
echo "步骤 4: 检查模板文件"
echo "------------------"

TEMPLATE_FILES=(
    "templates/router.yaml"
    "templates/company/schema.yaml"
    "templates/company/template.docx"
)

for file in "${TEMPLATE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${YELLOW}⚠${NC} $file 未找到（可选）"
    fi
done

echo ""

# 步骤 5: 检查样本文件
echo "步骤 5: 检查样本文件（可选）"
echo "-------------------------"

SAMPLE_FILE="samples/西锐飞机首次覆盖报告（中文）提交版.docx"
if [ -f "$SAMPLE_FILE" ]; then
    echo -e "${GREEN}✓${NC} $SAMPLE_FILE"
    HAS_SAMPLE=1
else
    echo -e "${YELLOW}⚠${NC} 样本文件不存在（跳过集成测试）"
    HAS_SAMPLE=0
fi

echo ""

# 步骤 6: 运行单元测试
echo "步骤 6: 运行单元测试"
echo "-------------------"

if command -v pytest &> /dev/null; then
    echo "运行 pytest..."
    if pytest skills/report_maker/tests/ -v --tb=short; then
        echo -e "${GREEN}✓${NC} 所有测试通过"
    else
        echo -e "${RED}✗${NC} 测试失败"
        exit 1
    fi
else
    echo -e "${YELLOW}警告: pytest 未安装，跳过测试${NC}"
    echo "安装命令: pip install pytest"
fi

echo ""

# 步骤 7: 检查 LibreOffice（可选）
echo "步骤 7: 检查 LibreOffice（可选）"
echo "-----------------------------"

LIBREOFFICE_FOUND=0
for cmd in libreoffice soffice; do
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓${NC} LibreOffice 已安装"
        LIBREOFFICE_FOUND=1
        break
    fi
done

if [ $LIBREOFFICE_FOUND -eq 0 ]; then
    echo -e "${YELLOW}⚠${NC} LibreOffice 未安装"
    echo "PDF 转换功能将不可用"
    echo "安装指南: https://www.libreoffice.org/download/download/"
fi

echo ""

# 步骤 8: 创建测试报告目录
echo "步骤 8: 准备测试环境"
echo "-------------------"

mkdir -p reports
echo -e "${GREEN}✓${NC} 创建 reports/ 目录"

echo ""

# 总结
echo "==================================="
echo "  验证完成！"
echo "==================================="
echo ""
echo "report_maker 环境已就绪，可以开始使用。"
echo ""
echo "使用示例："
echo "  1. 在 Claude Code 中上传草稿报告"
echo "  2. 说：'我上传了公司报告草稿，报告类型是 company，帮我处理'"
echo "  3. 等待系统提取要素"
echo "  4. 确认要素后生成标准报告"
echo ""
echo "输出目录：reports/"
echo ""

if [ $HAS_SAMPLE -eq 1 ]; then
    echo "提示: 检测到样本文件，可以运行集成测试"
    echo "运行: $PYTHON examples/test_integration.py"
    echo ""
fi

echo "==================================="
