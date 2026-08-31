"""Connection lifecycle: connect (verify via GetOrganizations query), list,
disconnect.

Same "secrets-store list of dicts" shape as every other BYOK connector
this session's handlers_connection.py.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import buffer_client as bf
from app import chat
from schemas import (
    ConnectBufferParams, ConnectBufferResult,
    DisconnectBufferParams, DeleteResult,
    BufferConnection, ConnectionList, ListConnectionsParams,
)

_CONNECTIONS_SECRET = "buffer_connections"

_ORGS_QUERY = """
query GetOrganizations {
  account {
    organizations {
      id
      name
    }
  }
}
"""


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_CONNECTIONS_SECRET)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_CONNECTIONS_SECRET, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        return next((c for c in connections if c.get("id") == connection_id), None)
    return connections[0]


async def resolve_or_error(ctx, connection_id: str = ""):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error(
            "No Buffer account found. Connect one with connect_buffer first.",
            code=bf.BF_NOT_CONNECTED,
        )
    return conn, None


@chat.function(
    "connect_buffer",
    "Connect your own Buffer account by saving its API key, after checking it actually works.",
    action_type="write", chain_callable=True, effects=["create:connection"], data_model=ConnectBufferResult, event="buffer-connector.connect_buffer",
)
async def connect_buffer(ctx, params: ConnectBufferParams) -> ActionResult:
    """Verify the supplied API key against Buffer's v1 API, then store it."""
    fake_conn = {"access_token": params.access_token}
    try:
        data = await bf.graphql(ctx, fake_conn, _ORGS_QUERY, action="verify Buffer API key")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])

    orgs = ((data.get("account") or {}).get("organizations")) or []
    org_id = orgs[0].get("id", "") if orgs else ""

    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    connections.append({
        "id": conn_id,
        "label": params.label or "Buffer account",
        "access_token": params.access_token,
        "organization_id": org_id,
    })
    await _save_connections(ctx, connections)
    return ActionResult.success(ConnectBufferResult(
        connection_id=conn_id, label=params.label or "Buffer account", organization_id=org_id,
    ), summary="Buffer connected.")


@chat.function(
    "disconnect_buffer",
    "Disconnect a Buffer account: deletes the saved API key. Nothing in Buffer itself is changed.",
    action_type="write", chain_callable=True, effects=["delete:connection"], data_model=DeleteResult, event="buffer-connector.disconnect_buffer",
)
async def disconnect_buffer(ctx, params: DisconnectBufferParams) -> ActionResult:
    """Remove one saved connection's API key; Buffer data is untouched."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code=bf.BF_NOT_CONNECTED)
    await _save_connections(ctx, remaining)
    return ActionResult.success(DeleteResult(deleted=True, id=params.connection_id), summary="Buffer disconnected.")


@chat.function(
    "list_connections",
    "List the connected Buffer accounts.",
    action_type="read", chain_callable=True, data_model=ConnectionList,
)
async def list_connections(ctx, params: ListConnectionsParams) -> ActionResult:
    """Return safe connection metadata only -- never the stored API key."""
    connections = await _load_connections(ctx)
    return ActionResult.success(ConnectionList(connections=[
        BufferConnection(id=c.get("id", ""), label=c.get("label", ""), organization_id=c.get("organization_id", ""))
        for c in connections
    ]), summary="Connections listed.")
