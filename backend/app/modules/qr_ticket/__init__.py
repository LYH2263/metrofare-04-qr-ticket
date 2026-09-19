"""qr_ticket 乘车码模块：签发 / 按编码核验 / 作废，落库于 qr_tickets 表。

码上冻结起点、终点、途经站序列、站数、应付票价与状态；核验按冻结值返回。
"""

from app.modules.qr_ticket.repository import ensure_schema
from app.modules.qr_ticket.service import TicketError, get, issue, list_tickets, verify, void

__all__ = ["ensure_schema", "issue", "verify", "void", "get", "list_tickets", "TicketError"]
