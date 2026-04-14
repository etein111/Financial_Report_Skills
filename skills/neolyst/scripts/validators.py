"""
validators.py — Neolyst 报告提交前校验。

校验逻辑的单一事实源在 DB 侧（validate_report RPC）。
Python 层只封装 RPC 调用，返回标准化结果。
"""

from supabase import Client

from . import rpc


def validate_report(client: Client, report_id: str) -> None:
    """
    调用 validate_report RPC，校验报告是否满足提交条件。

    校验不通过时 RPC 抛出 ValueError；通过时无返回值。
    """
    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})
