# 02 消除 extract_body/extract_english_summary 重复

## 遇到的问题

`extract_body()` 和 `extract_english_summary()` 有 ~270 行重复代码，做了完全相同的事：

1. 复制草稿到临时文件
2. 用 lxml 解析 document.xml
3. 定位起始/结束索引
4. 保存范围内的 sectPr 页边距
5. 删除范围外的元素
6. 应用页边距到最终 sectPr
7. 保存到输出路径
8. 清理临时文件

只有第 3 步（定位逻辑）不同。此外定位逻辑和文件操作混在同一个 try 块里，无法单独测试。

## 重构方法

### 提取通用函数

```python
def _extract_fragment_by_range_finder(
    draft_path, output_path, temp_prefix,
    locate_range: Callable[[list], Optional[Tuple[int, int]]],
    clear_indents: bool = False,
) -> Path:
```

`locate_range` 是回调，由调用方提供定位逻辑。`clear_indents` 处理唯一的额外差异。

### 提取定位函数

```python
def _find_body_range(elements, start_marker, end_marker) -> Tuple[int, int]:
def _find_english_summary_range(elements, start_marker, end_marker) -> Optional[Tuple[int, int]]:
```

纯函数：输入元素列表和标记文本，输出索引范围。不碰文件系统，可独立测试。

## 变更

| 文件 | 变更 |
|------|------|
| `splitter.py` | 新增 `_extract_fragment_by_range_finder()`、`_find_body_range()`、`_find_english_summary_range()`；简化 `extract_body()` 和 `extract_english_summary()` |
| `test_splitter.py` | 新增 `TestExtractFragmentByRangeFinder` |

## 原则

- 两个函数只有"定位范围"不同时，把变化的部分提取为回调，不变的部分合并。
- 定位逻辑（纯计算）和文件操作（IO）是两个独立关注点，必须分离。
