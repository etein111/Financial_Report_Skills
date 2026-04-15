"""context.py - 上下文准备模块

提供 render_report 所需的上下文准备函数：
- enrich_company_names_with_yfinance: 使用 yfinance 补全公司名称
- prepare_context_with_analysts: 准备渲染上下文（分析师字段等）
"""

from typing import Dict, Any
from pathlib import Path

# 尝试导入 yfinance
try:
    import yfinance as yf
    CHARTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: yfinance not available: {e}")
    CHARTS_AVAILABLE = False
    yf = None


def enrich_company_names_with_yfinance(elements: Dict[str, Any]) -> Dict[str, Any]:
    """使用 yfinance 补全公司中英文名称。

    逻辑：
    - 如果 company_en 已存在且不为空，跳过
    - 如果 company_en 不存在或为空，但 ticker 存在，用 yfinance 查询补充
    - 如果 company_cn 已存在且不为空，跳过
    - 如果 company_cn 不存在或为空，但 ticker 存在，尝试用 yfinance 查询补充

    Args:
        elements: 原始要素字典

    Returns:
        补全后的要素字典
    """
    elements = elements.copy()

    ticker = elements.get('ticker', '').strip() if elements.get('ticker') else ''

    if not ticker:
        return elements

    # 如果 company_en 为空，尝试用 yfinance 补全
    if not elements.get('company_en'):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            company_en = info.get('longName') or info.get('shortName', '')
            if company_en:
                elements['company_en'] = company_en
                print(f"  [yfinance] 补全 company_en: {company_en}")
        except Exception as e:
            print(f"  [yfinance] 查询 company_en 失败: {e}")

    # 如果 company_cn 为空，尝试用 yfinance 补全
    if not elements.get('company_cn'):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            company_cn = info.get('longName') or info.get('shortName', '')
            # yfinance 通常不返回中文名，这里仅作为备用
            if company_cn:
                elements['company_cn'] = company_cn
                print(f"  [yfinance] 补全 company_cn: {company_cn}")
        except Exception:
            pass

    return elements


def clean_value(value: Any) -> str:
    """清理字段值为字符串，处理 None 和列表。

    Args:
        value: 原始值

    Returns:
        清理后的字符串，空返回空字符串
    """
    if value is None:
        return ''
    if isinstance(value, list):
        return ', '.join(str(v) for v in value)
    return str(value)


def prepare_context_with_analysts(elements: Dict[str, Any]) -> Dict[str, Any]:
    """准备渲染上下文，将 a1~a8 字段展开为独立变量。

    将 elements 中的 a1_email、a1_name 等字段展开为独立的上下文变量，
    方便模板中直接引用 {{ a1_email }}、{{ a2_name }} 等。

    同时处理 rating、target_price 等字段的格式化。

    Args:
        elements: 要素字典

    Returns:
        渲染上下文字典
    """
    context = {}

    # 复制所有非 aN_* 的字段
    for key, value in elements.items():
        if not key.startswith('a') or not key[1:].split('_')[0].isdigit():
            context[key] = value

    # 展开 a1~a8 字段
    for i in range(1, 9):
        prefix = f'a{i}'
        for suffix in ['_name', '_email', '_certification']:
            key = f'{prefix}{suffix}'
            if key in elements:
                context[key] = elements[key]
            # rating 字段（如果有）
        rating_key = f'a{i}_rating'
        if rating_key in elements:
            context[rating_key] = elements[rating_key]

    # 格式化 rating 和 target_price
    if 'rating' in context:
        context['rating'] = clean_value(context['rating'])
    if 'target_price' in context:
        tp = context['target_price']
        if tp:
            try:
                context['target_price'] = float(tp)
            except (ValueError, TypeError):
                pass

    # 处理 analyst_abbr 字段（用于显示）
    if 'analysts' in elements:
        analysts = elements['analysts']
        if isinstance(analysts, list) and analysts:
            context['analyst_display'] = ' / '.join(
                a.get('name', '') for a in analysts if a.get('name')
            )
        context['analysts'] = analysts

    return context
