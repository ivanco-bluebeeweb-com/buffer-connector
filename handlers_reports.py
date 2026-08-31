"""Value-add reports for Buffer Connector -- channel overview, same
"aggregate raw records into one glance" shape as every other connector's
handlers_reports.py this session.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import buffer_client as bf
from app import chat
from handlers_connection import resolve_or_error
from handlers_entities import _CHANNELS_QUERY
from schemas import (
    AuditBufferAccountParams, BufferAccountReport,
)


@chat.function(
    "audit_buffer_account",
    "Build one aggregated channel overview for the connected Buffer account: total connected channels "
    "broken down by social service (Instagram, X, LinkedIn, etc.).",
    action_type="read", chain_callable=True, data_model=BufferAccountReport,
)
async def audit_buffer_account(ctx, params: AuditBufferAccountParams) -> ActionResult:
    """Scan channels and summarize by service."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        data = await bf.graphql(ctx, conn, _CHANNELS_QUERY, action="list channels for audit")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    orgs = ((data.get("account") or {}).get("organizations")) or []
    channels: list[dict] = []
    for org in orgs:
        channels.extend(org.get("channels", []) or [])
    by_service: dict = {}
    for c in channels:
        svc = c.get("service", "unknown")
        by_service[svc] = by_service.get(svc, 0) + 1
    return ActionResult.success(BufferAccountReport(
        total_channels=len(channels),
        channels_by_service=by_service,
    ), summary="Buffer account audit ready.")
