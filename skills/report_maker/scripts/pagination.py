"""pagination.py - 文档分页优化模块。

使用 LibreOffice UNO API 实现以下分页优化：
1. 段落分页处理（3行规则）
2. 标题孤行处理
3. 图表和 caption 保持同页

依赖：
- LibreOffice（带 UNO Python 支持）
- uno 库（通常随 LibreOffice 安装）
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import subprocess
import time
import os
import tempfile
import shutil


# ============================================================================
# LibreOffice UNO 连接管理
# ============================================================================

class LibreOfficeConnection:
    """LibreOffice UNO 连接管理器。

    管理 LibreOffice 进程的启动、连接和关闭。
    使用 socket 方式连接到 LibreOffice 实例。
    """

    DEFAULT_PORT = 2002
    DEFAULT_HOST = "localhost"

    def __init__(self, port: int = DEFAULT_PORT, host: str = DEFAULT_HOST):
        self.port = port
        self.host = host
        self.process = None
        self.desktop = None
        self.local_context = None
        self._uno_available = None

    def _check_uno_available(self) -> bool:
        """检查 uno 库是否可用。"""
        if self._uno_available is not None:
            return self._uno_available

        try:
            import uno
            from com.sun.star.beans import PropertyValue
            self._uno_available = True
        except ImportError:
            self._uno_available = False
            print("警告: uno 库不可用。请确保：")
            print("  1. 已安装 LibreOffice")
            print("  2. 使用 LibreOffice 的 Python 环境，或")
            print("  3. 已安装 python3-uno 包（Linux）")

        return self._uno_available

    def _find_libreoffice(self) -> Optional[str]:
        """查找 LibreOffice 可执行文件。"""
        import platform

        system = platform.system()

        if system == "Windows":
            possible_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                r"C:\Program Files\LibreOffice 7\program\soffice.exe",
                r"C:\Program Files\LibreOffice 24\program\soffice.exe",
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path

            for cmd in ['soffice', 'libreoffice']:
                found = shutil.which(cmd)
                if found:
                    return found
        else:
            # Linux/Mac
            possible_commands = ['libreoffice', 'libreoffice7.5', 'libreoffice7.6',
                               'libreoffice24.2', 'soffice']
            for cmd in possible_commands:
                found = shutil.which(cmd)
                if found:
                    return found

        return None

    def start_libreoffice(self, timeout: int = 30) -> bool:
        """启动 LibreOffice 监听模式。

        Args:
            timeout: 等待启动的超时时间（秒）

        Returns:
            是否启动成功
        """
        libreoffice_cmd = self._find_libreoffice()
        if not libreoffice_cmd:
            print("错误: 找不到 LibreOffice")
            return False

        # 构建监听参数
        accept_arg = f'socket,host={self.host},port={self.port};urp;StarOffice.ServiceManager'

        # 使用临时用户配置，避免与其他实例冲突
        user_profile = tempfile.mkdtemp(prefix="lo_pagination_")

        cmd = [
            libreoffice_cmd,
            '--headless',
            '--invisible',
            '--nologo',
            '--nofirststartwizard',
            f'--accept={accept_arg}',
            f'-env:UserInstallation=file://{user_profile.replace(os.sep, "/")}'
        ]

        try:
            print(f"启动 LibreOffice 监听模式 (端口 {self.port})...")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 等待 LibreOffice 启动
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._try_connect():
                    print("LibreOffice 连接成功")
                    return True
                time.sleep(1)

            print(f"LibreOffice 启动超时（{timeout}秒）")
            self.stop_libreoffice()
            return False

        except Exception as e:
            print(f"启动 LibreOffice 失败: {e}")
            return False

    def _try_connect(self) -> bool:
        """尝试连接到 LibreOffice 实例。"""
        if not self._check_uno_available():
            return False

        try:
            import uno
            from com.sun.star.connection import NoConnectException

            local_context = uno.getComponentContext()
            resolver = local_context.ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", local_context
            )

            connect_string = f"uno:socket,host={self.host},port={self.port};urp;StarOffice.ComponentContext"
            ctx = resolver.resolve(connect_string)
            smgr = ctx.ServiceManager
            self.desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            self.local_context = ctx

            return self.desktop is not None

        except Exception:
            return False

    def connect(self) -> bool:
        """连接到已运行的 LibreOffice 实例。"""
        return self._try_connect()

    def stop_libreoffice(self):
        """停止 LibreOffice 进程。"""
        if self.desktop:
            try:
                self.desktop.terminate()
            except Exception:
                pass
            self.desktop = None

        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def open_document(self, file_path: str) -> Any:
        """打开文档。

        Args:
            file_path: 文档路径

        Returns:
            文档对象，失败返回 None
        """
        if not self.desktop:
            print("错误: 未连接到 LibreOffice")
            return None

        try:
            import uno
            from com.sun.star.beans import PropertyValue

            # 转换为 file:// URL
            abs_path = Path(file_path).resolve()
            file_url = f"file:///{str(abs_path).replace(os.sep, '/')}"

            # 打开文档属性
            props = (
                PropertyValue("Hidden", 0, True, 0),
            )

            doc = self.desktop.loadComponentFromURL(file_url, "_blank", 0, props)
            return doc

        except Exception as e:
            print(f"打开文档失败: {e}")
            return None

    def save_document(self, doc: Any, output_path: str) -> bool:
        """保存文档。

        Args:
            doc: 文档对象
            output_path: 输出路径

        Returns:
            是否保存成功
        """
        try:
            import uno
            from com.sun.star.beans import PropertyValue

            abs_path = Path(output_path).resolve()
            file_url = f"file:///{str(abs_path).replace(os.sep, '/')}"

            # 保存属性
            props = (
                PropertyValue("FilterName", 0, "MS Word 2007 XML", 0),
                PropertyValue("Overwrite", 0, True, 0),
            )

            doc.storeToURL(file_url, props)
            return True

        except Exception as e:
            print(f"保存文档失败: {e}")
            return False

    def close_document(self, doc: Any):
        """关闭文档。"""
        if doc:
            try:
                doc.close(True)
            except Exception:
                pass

    def __enter__(self):
        """上下文管理器入口。"""
        if not self.connect():
            if not self.start_libreoffice():
                raise RuntimeError("无法连接或启动 LibreOffice")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出。"""
        self.stop_libreoffice()
        return False


# ============================================================================
# 分页信息获取
# ============================================================================

class ParagraphInfo:
    """段落信息类。"""

    def __init__(self):
        self.index: int = 0           # 段落索引
        self.text: str = ""           # 段落文本
        self.start_page: int = 0      # 起始页码
        self.end_page: int = 0        # 结束页码
        self.line_count: int = 0      # 总行数
        self.lines_on_start_page: int = 0  # 在起始页的行数
        self.lines_on_end_page: int = 0    # 在结束页的行数
        self.is_heading: bool = False      # 是否是标题
        self.heading_level: int = 0        # 标题级别 (1-9)
        self.has_image: bool = False       # 是否包含图片
        self.has_table: bool = False       # 是否是表格
        self.style_name: str = ""          # 样式名称
        self.paragraph_obj: Any = None     # 原始段落对象

    @property
    def spans_pages(self) -> bool:
        """段落是否跨页。"""
        return self.start_page != self.end_page

    def __repr__(self):
        return (f"ParagraphInfo(idx={self.index}, pages={self.start_page}-{self.end_page}, "
                f"lines={self.line_count}, heading={self.is_heading}, text={self.text[:30]}...)")


def get_paragraph_info(doc: Any) -> List[ParagraphInfo]:
    """获取文档中所有段落的信息。

    Args:
        doc: LibreOffice 文档对象

    Returns:
        段落信息列表
    """
    paragraphs = []

    try:
        import uno

        text = doc.getText()
        cursor = text.createTextCursor()
        cursor.gotoStart(False)

        enum = text.createEnumeration()
        idx = 0

        while enum.hasMoreElements():
            para = enum.nextElement()

            # 跳过表格等非段落元素
            if not para.supportsService("com.sun.star.text.Paragraph"):
                continue

            info = ParagraphInfo()
            info.index = idx
            info.paragraph_obj = para

            # 获取文本
            try:
                info.text = para.getString()
            except Exception:
                info.text = ""

            # 获取样式名称
            try:
                info.style_name = para.getPropertyValue("ParaStyleName")
            except Exception:
                info.style_name = ""

            # 判断是否是标题
            if info.style_name:
                style_lower = info.style_name.lower()
                if "heading" in style_lower or "标题" in info.style_name:
                    info.is_heading = True
                    # 尝试提取标题级别
                    for i in range(1, 10):
                        if str(i) in info.style_name:
                            info.heading_level = i
                            break

            # 获取段落的页码信息
            try:
                # 创建一个 ViewCursor 来获取页码
                controller = doc.getCurrentController()
                view_cursor = controller.getViewCursor()

                # 移动到段落开始
                view_cursor.gotoRange(para.getAnchor().getStart(), False)
                info.start_page = view_cursor.getPage()

                # 移动到段落结束
                view_cursor.gotoRange(para.getAnchor().getEnd(), False)
                info.end_page = view_cursor.getPage()

            except Exception as e:
                # 如果无法获取页码，使用默认值
                info.start_page = 1
                info.end_page = 1

            # 检查是否包含图片
            try:
                content_enum = para.createContentEnumeration("com.sun.star.text.TextContent")
                while content_enum.hasMoreElements():
                    content = content_enum.nextElement()
                    if content.supportsService("com.sun.star.text.TextGraphicObject"):
                        info.has_image = True
                        break
            except Exception:
                pass

            # 估算行数（基于字符数和页面宽度）
            # 这是一个近似值，实际行数取决于字体大小、页面宽度等
            try:
                char_count = len(info.text)
                # 假设每行约 40-50 个中文字符或 80-100 个英文字符
                avg_chars_per_line = 45
                info.line_count = max(1, (char_count + avg_chars_per_line - 1) // avg_chars_per_line)

                if info.spans_pages:
                    # 粗略估算每页的行数
                    info.lines_on_start_page = info.line_count // 2
                    info.lines_on_end_page = info.line_count - info.lines_on_start_page
            except Exception:
                info.line_count = 1
                info.lines_on_start_page = 1
                info.lines_on_end_page = 0

            paragraphs.append(info)
            idx += 1

    except Exception as e:
        print(f"获取段落信息失败: {e}")
        import traceback
        traceback.print_exc()

    return paragraphs


def get_paragraph_line_info_precise(doc: Any, para_info: ParagraphInfo) -> Tuple[int, int]:
    """精确获取段落在每页的行数。

    使用 ViewCursor 逐行遍历来获取精确的行数。

    Args:
        doc: 文档对象
        para_info: 段落信息

    Returns:
        (起始页行数, 结束页行数)
    """
    try:
        controller = doc.getCurrentController()
        view_cursor = controller.getViewCursor()
        para = para_info.paragraph_obj

        # 移动到段落开始
        view_cursor.gotoRange(para.getAnchor().getStart(), False)
        start_page = view_cursor.getPage()

        lines_on_start_page = 0
        lines_on_end_page = 0
        current_page = start_page

        # 逐行移动，计算每页的行数
        while True:
            page_before = view_cursor.getPage()

            # 尝试移动到下一行
            if not view_cursor.goDown(1, False):
                # 无法继续向下，可能已到段落末尾
                break

            page_after = view_cursor.getPage()

            # 检查是否还在当前段落内
            # 通过比较位置来判断
            cursor_pos = view_cursor.getStart()
            para_end = para.getAnchor().getEnd()

            # 如果已经超出段落范围，停止
            if cursor_pos.compareRegionEnds(para_end) > 0:
                break

            if page_after == start_page:
                lines_on_start_page += 1
            else:
                lines_on_end_page += 1

        # 至少有一行
        lines_on_start_page = max(1, lines_on_start_page)

        return lines_on_start_page, lines_on_end_page

    except Exception as e:
        print(f"获取精确行数失败: {e}")
        # 返回估算值
        return para_info.lines_on_start_page, para_info.lines_on_end_page


# ============================================================================
# 分页优化实现
# ============================================================================

def insert_page_break_before(doc: Any, para: Any) -> bool:
    """在段落前插入分页符。

    Args:
        doc: 文档对象
        para: 段落对象

    Returns:
        是否成功
    """
    try:
        import uno
        from com.sun.star.style.BreakType import PAGE_BEFORE

        para.setPropertyValue("BreakType", PAGE_BEFORE)
        return True

    except Exception as e:
        print(f"插入分页符失败: {e}")
        return False


def set_keep_with_next(doc: Any, para: Any, keep: bool = True) -> bool:
    """设置段落与下一段保持同页。

    Args:
        doc: 文档对象
        para: 段落对象
        keep: 是否保持同页

    Returns:
        是否成功
    """
    try:
        para.setPropertyValue("ParaKeepTogether", keep)
        return True
    except Exception as e:
        print(f"设置 KeepWithNext 失败: {e}")
        return False


def set_keep_lines_together(doc: Any, para: Any, keep: bool = True) -> bool:
    """设置段落各行保持同页。

    Args:
        doc: 文档对象
        para: 段落对象
        keep: 是否保持同页

    Returns:
        是否成功
    """
    try:
        para.setPropertyValue("ParaSplit", not keep)  # ParaSplit=False 表示不分割
        return True
    except Exception as e:
        print(f"设置 KeepLinesTogether 失败: {e}")
        return False


def optimize_paragraph_pagination(doc: Any, paragraphs: List[ParagraphInfo],
                                   min_lines: int = 3) -> int:
    """优化段落分页（3行规则）。

    规则：
    1. 如果段落跨页，前页部分 < min_lines 行，则整段移到下一页
    2. 如果段落跨页，前页部分 >= min_lines 行，但后页部分 < min_lines 行，则整段移到下一页
    3. 如果前后页部分都 >= min_lines 行，则不改动

    Args:
        doc: 文档对象
        paragraphs: 段落信息列表
        min_lines: 最小行数阈值（默认3）

    Returns:
        修改的段落数量
    """
    modified_count = 0

    for info in paragraphs:
        if not info.spans_pages:
            continue

        # 获取精确的行数信息
        lines_start, lines_end = get_paragraph_line_info_precise(doc, info)

        need_page_break = False

        if lines_start < min_lines:
            # 规则1：前页部分小于3行
            need_page_break = True
            print(f"  段落 {info.index}: 前页 {lines_start} 行 < {min_lines}，添加分页符")
        elif lines_end < min_lines:
            # 规则2：后页部分小于3行
            need_page_break = True
            print(f"  段落 {info.index}: 后页 {lines_end} 行 < {min_lines}，添加分页符")

        if need_page_break:
            if insert_page_break_before(doc, info.paragraph_obj):
                modified_count += 1

    return modified_count


def optimize_heading_pagination(doc: Any, paragraphs: List[ParagraphInfo]) -> int:
    """优化标题分页（避免标题孤行）。

    如果标题单独在页尾（后面的段落在下一页），则将标题移到下一页。

    Args:
        doc: 文档对象
        paragraphs: 段落信息列表

    Returns:
        修改的段落数量
    """
    modified_count = 0

    for i, info in enumerate(paragraphs):
        if not info.is_heading:
            continue

        # 检查下一个段落是否在不同页
        if i + 1 < len(paragraphs):
            next_info = paragraphs[i + 1]

            if info.end_page < next_info.start_page:
                # 标题和下一段落不在同一页
                # 方案1：设置标题与下一段保持同页
                if set_keep_with_next(doc, info.paragraph_obj, True):
                    modified_count += 1
                    print(f"  标题 {info.index} '{info.text[:20]}...': 设置与下一段保持同页")

    return modified_count


def optimize_figure_pagination(doc: Any, paragraphs: List[ParagraphInfo]) -> int:
    """优化图表分页（图片和 caption 保持同页）。

    检测图片段落和相邻的 caption 段落，确保它们在同一页。

    Args:
        doc: 文档对象
        paragraphs: 段落信息列表

    Returns:
        修改的段落数量
    """
    modified_count = 0

    # 查找图片段落
    for i, info in enumerate(paragraphs):
        if not info.has_image:
            continue

        # 设置图片段落不分页
        if set_keep_lines_together(doc, info.paragraph_obj, True):
            print(f"  图片段落 {info.index}: 设置不分页")

        # 检查相邻段落是否是 caption
        # caption 通常紧跟在图片后面，包含 "图"、"Figure"、"表"、"Table" 等关键词
        caption_keywords = ['图', 'Figure', 'Fig.', '表', 'Table', 'Tab.',
                          '来源', 'Source', '数据来源', '资料来源', '注：', '注:']

        # 检查图片后面的段落
        if i + 1 < len(paragraphs):
            next_info = paragraphs[i + 1]
            text_lower = next_info.text.strip()

            is_caption = False
            for keyword in caption_keywords:
                if text_lower.startswith(keyword) or keyword in text_lower[:20]:
                    is_caption = True
                    break

            if is_caption:
                # 设置图片与 caption 保持同页
                if set_keep_with_next(doc, info.paragraph_obj, True):
                    modified_count += 1
                    print(f"  图片 {info.index} 和 caption {next_info.index}: 设置保持同页")

        # 也检查图片前面的段落（caption 可能在图片上方）
        if i > 0:
            prev_info = paragraphs[i - 1]
            text_lower = prev_info.text.strip()

            is_caption = False
            for keyword in caption_keywords:
                if text_lower.startswith(keyword) or keyword in text_lower[:20]:
                    is_caption = True
                    break

            if is_caption:
                # 设置 caption 与图片保持同页
                if set_keep_with_next(doc, prev_info.paragraph_obj, True):
                    modified_count += 1
                    print(f"  caption {prev_info.index} 和图片 {info.index}: 设置保持同页")

    return modified_count


# ============================================================================
# 主函数
# ============================================================================

def optimize_pagination(
    input_path: str,
    output_path: str,
    optimize_paragraphs: bool = True,
    optimize_headings: bool = True,
    optimize_figures: bool = True,
    min_lines: int = 3
) -> Dict[str, Any]:
    """优化文档分页。

    Args:
        input_path: 输入文档路径
        output_path: 输出文档路径
        optimize_paragraphs: 是否优化段落分页（3行规则）
        optimize_headings: 是否优化标题分页
        optimize_figures: 是否优化图表分页
        min_lines: 段落分页的最小行数阈值

    Returns:
        优化结果字典，包含：
        - success: 是否成功
        - paragraphs_modified: 修改的段落数
        - headings_modified: 修改的标题数
        - figures_modified: 修改的图表数
        - error: 错误信息（如果有）
    """
    result = {
        "success": False,
        "paragraphs_modified": 0,
        "headings_modified": 0,
        "figures_modified": 0,
        "error": None
    }

    print(f"开始优化分页: {input_path}")
    print(f"  段落优化: {optimize_paragraphs}")
    print(f"  标题优化: {optimize_headings}")
    print(f"  图表优化: {optimize_figures}")
    print(f"  最小行数: {min_lines}")

    try:
        with LibreOfficeConnection() as conn:
            # 打开文档
            doc = conn.open_document(input_path)
            if not doc:
                result["error"] = "无法打开文档"
                return result

            try:
                # 获取段落信息
                print("正在分析文档结构...")
                paragraphs = get_paragraph_info(doc)
                print(f"  共找到 {len(paragraphs)} 个段落")

                # 统计
                headings = [p for p in paragraphs if p.is_heading]
                images = [p for p in paragraphs if p.has_image]
                spanning = [p for p in paragraphs if p.spans_pages]

                print(f"  标题数: {len(headings)}")
                print(f"  含图段落: {len(images)}")
                print(f"  跨页段落: {len(spanning)}")

                # 执行优化
                if optimize_paragraphs:
                    print("\n优化段落分页...")
                    result["paragraphs_modified"] = optimize_paragraph_pagination(
                        doc, paragraphs, min_lines
                    )

                if optimize_headings:
                    print("\n优化标题分页...")
                    result["headings_modified"] = optimize_heading_pagination(doc, paragraphs)

                if optimize_figures:
                    print("\n优化图表分页...")
                    result["figures_modified"] = optimize_figure_pagination(doc, paragraphs)

                # 保存文档
                print(f"\n保存文档: {output_path}")
                if conn.save_document(doc, output_path):
                    result["success"] = True
                else:
                    result["error"] = "保存文档失败"

            finally:
                conn.close_document(doc)

        total_modified = (result["paragraphs_modified"] +
                         result["headings_modified"] +
                         result["figures_modified"])
        print(f"\n优化完成，共修改 {total_modified} 处")

    except Exception as e:
        result["error"] = str(e)
        print(f"优化失败: {e}")
        import traceback
        traceback.print_exc()

    return result


def optimize_pagination_simple(input_path: str, output_path: str = None) -> bool:
    """简化版分页优化接口。

    执行所有优化，使用默认参数。

    Args:
        input_path: 输入文档路径
        output_path: 输出文档路径（默认覆盖原文件）

    Returns:
        是否成功
    """
    if output_path is None:
        output_path = input_path

    result = optimize_pagination(
        input_path=input_path,
        output_path=output_path,
        optimize_paragraphs=True,
        optimize_headings=True,
        optimize_figures=True,
        min_lines=3
    )

    return result["success"]


# ============================================================================
# 备用方案：纯 XML 属性设置（不需要 UNO）
# ============================================================================

def optimize_pagination_xml(input_path: str, output_path: str = None) -> Dict[str, Any]:
    """使用纯 XML 方式优化分页（备用方案）。

    当 LibreOffice UNO 不可用时，使用此方法。
    通过设置 Word XML 段落属性来控制分页：
    - keepLines: 段落各行保持同页
    - keepNext: 与下一段保持同页
    - widowControl: 寡妇/孤儿控制

    注意：此方法不能精确计算行数，只能设置段落属性。
    实际分页效果在 Word 打开时才会生效。

    Args:
        input_path: 输入文档路径
        output_path: 输出路径（默认覆盖原文件）

    Returns:
        优化结果
    """
    from lxml import etree
    import zipfile

    if output_path is None:
        output_path = input_path

    result = {
        "success": False,
        "headings_modified": 0,
        "figures_modified": 0,
        "error": None
    }

    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    try:
        # 读取文档
        with zipfile.ZipFile(input_path, 'r') as z:
            files = {name: z.read(name) for name in z.namelist()}

        if 'word/document.xml' not in files:
            result["error"] = "无效的 docx 文件"
            return result

        doc_tree = etree.fromstring(files['word/document.xml'])
        body = doc_tree.find(f'{W}body')

        if body is None:
            result["error"] = "文档结构错误"
            return result

        # 标题样式名称模式
        heading_styles = ['Heading', 'heading', '标题', 'Title']

        # 图表/caption 关键词
        caption_keywords = ['图', 'Figure', 'Fig', '表', 'Table', 'Tab',
                          '来源', 'Source', '数据来源', '注：', '注:']

        all_paragraphs = list(body.findall(f'.//{W}p'))

        for i, para in enumerate(all_paragraphs):
            # 获取段落属性
            pPr = para.find(f'{W}pPr')
            if pPr is None:
                pPr = etree.SubElement(para, f'{W}pPr')
                para.insert(0, pPr)

            # 获取段落样式
            pStyle = pPr.find(f'{W}pStyle')
            style_name = pStyle.get(f'{W}val', '') if pStyle is not None else ''

            # 获取段落文本
            text = ''.join(t.text or '' for t in para.iter(f'{W}t'))

            # 检查是否是标题
            is_heading = any(h in style_name for h in heading_styles)

            # 检查是否包含图片
            has_image = para.find(f'.//{W}drawing') is not None or \
                       para.find('.//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline') is not None

            # 检查是否是 caption
            is_caption = any(text.strip().startswith(kw) or kw in text[:30]
                           for kw in caption_keywords)

            # 设置标题与下一段保持同页
            if is_heading and i + 1 < len(all_paragraphs):
                keepNext = pPr.find(f'{W}keepNext')
                if keepNext is None:
                    keepNext = etree.SubElement(pPr, f'{W}keepNext')
                result["headings_modified"] += 1

            # 设置图片段落属性
            if has_image:
                # 设置不分页
                keepLines = pPr.find(f'{W}keepLines')
                if keepLines is None:
                    keepLines = etree.SubElement(pPr, f'{W}keepLines')

                # 与下一段（可能是caption）保持同页
                if i + 1 < len(all_paragraphs):
                    keepNext = pPr.find(f'{W}keepNext')
                    if keepNext is None:
                        keepNext = etree.SubElement(pPr, f'{W}keepNext')

                result["figures_modified"] += 1

            # 设置 caption 与上一段保持同页
            if is_caption and i > 0:
                # 检查上一段是否有图片
                prev_para = all_paragraphs[i - 1]
                prev_has_image = prev_para.find(f'.//{W}drawing') is not None

                if prev_has_image:
                    # 给上一段设置 keepNext
                    prev_pPr = prev_para.find(f'{W}pPr')
                    if prev_pPr is None:
                        prev_pPr = etree.SubElement(prev_para, f'{W}pPr')
                        prev_para.insert(0, prev_pPr)

                    keepNext = prev_pPr.find(f'{W}keepNext')
                    if keepNext is None:
                        keepNext = etree.SubElement(prev_pPr, f'{W}keepNext')

        # 保存修改
        files['word/document.xml'] = etree.tostring(
            doc_tree, xml_declaration=True, encoding='UTF-8', standalone=True
        )

        # 如果输入输出相同，先删除原文件
        if input_path == output_path:
            os.remove(input_path)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in files.items():
                z.writestr(name, content)

        result["success"] = True
        print(f"XML 优化完成: 标题 {result['headings_modified']} 处, 图表 {result['figures_modified']} 处")

    except Exception as e:
        result["error"] = str(e)
        print(f"XML 优化失败: {e}")
        import traceback
        traceback.print_exc()

    return result


# ============================================================================
# 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Word 文档分页优化工具")
    parser.add_argument("input", help="输入文档路径")
    parser.add_argument("-o", "--output", help="输出文档路径（默认覆盖原文件）")
    parser.add_argument("--no-paragraphs", action="store_true", help="不优化段落分页")
    parser.add_argument("--no-headings", action="store_true", help="不优化标题分页")
    parser.add_argument("--no-figures", action="store_true", help="不优化图表分页")
    parser.add_argument("--min-lines", type=int, default=3, help="最小行数阈值（默认3）")
    parser.add_argument("--xml-only", action="store_true", help="只使用 XML 方式（不启动 LibreOffice）")

    args = parser.parse_args()

    if args.xml_only:
        result = optimize_pagination_xml(args.input, args.output)
    else:
        result = optimize_pagination(
            input_path=args.input,
            output_path=args.output or args.input,
            optimize_paragraphs=not args.no_paragraphs,
            optimize_headings=not args.no_headings,
            optimize_figures=not args.no_figures,
            min_lines=args.min_lines
        )

    if result["success"]:
        print("优化成功!")
    else:
        print(f"优化失败: {result.get('error', '未知错误')}")
        exit(1)
