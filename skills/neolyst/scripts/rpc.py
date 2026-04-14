"""
rpc.py — Supabase RPC 调用封装。

统一 RPC 调用的异常处理和结果提取，消除各模块的重复 try/except 模式。
"""

from typing import Any

from supabase import Client


def call_rpc(client: Client, fn_name: str, params: dict | None = None) -> Any:
    """调用 Supabase RPC，统一异常转换为 ValueError。"""
    try:
        return client.rpc(fn_name, params or {}).execute()
    except Exception as e:
        raise ValueError(str(e)) from e


def single_row(resp, message: str = "RPC 未返回数据") -> dict:
    """从 RPC 响应中提取唯一一行，空数据时抛 ValueError。"""
    if not resp.data:
        raise ValueError(message)
    return resp.data[0]
