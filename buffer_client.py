"""Thin GraphQL client for Buffer API + Bearer API-key auth.

Same "fail()-dict + ClientFail exception" shape as every other connector
this session's *_client.py, adapted for Buffer's single-endpoint GraphQL
transport. Confirmed against developers.buffer.com, 2026-08-29:

- Single endpoint: POST https://api.buffer.com
- Auth header: Authorization: Bearer {access_token}
- Body: {"query": "...", "variables": {...}}
- Errors come back as a top-level `errors` array in the JSON response,
  not (only) via HTTP status codes.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

BF_NOT_CONNECTED = "BUFFER_NOT_CONNECTED"
BF_UNAUTHORIZED = "BUFFER_UNAUTHORIZED"
BF_FORBIDDEN = "BUFFER_FORBIDDEN"
BF_NOT_FOUND = "BUFFER_NOT_FOUND"
BF_RATE_LIMITED = "BUFFER_RATE_LIMITED"
BF_BACKEND_ERROR = "BUFFER_BACKEND_ERROR"
BF_VALIDATION_FAILED = "BUFFER_VALIDATION_FAILED"
BF_GRAPHQL_ERROR = "BUFFER_GRAPHQL_ERROR"
BF_RESPONSE_UNEXPECTED = "BUFFER_RESPONSE_UNEXPECTED"

_MESSAGES = {
    BF_NOT_CONNECTED: "No Buffer account connected. Connect one first.",
    BF_UNAUTHORIZED: "Buffer rejected the API key as invalid or expired.",
    BF_FORBIDDEN: "Buffer denied access to this resource.",
    BF_NOT_FOUND: "That Buffer record was not found.",
    BF_RATE_LIMITED: "Buffer rate-limited this request. Try again shortly.",
    BF_BACKEND_ERROR: "Buffer returned an error.",
    BF_VALIDATION_FAILED: "Buffer rejected the request as invalid.",
    BF_GRAPHQL_ERROR: "Buffer's GraphQL API returned an error.",
    BF_RESPONSE_UNEXPECTED: "Buffer returned an unexpected response shape.",
}


def fail(code: str, detail: str = "") -> dict:
    msg = _MESSAGES.get(code, "Buffer request failed.")
    if detail:
        msg = f"{msg} ({detail})"
    return {"code": code, "message": msg}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        super().__init__(payload.get("message", "Buffer request failed."))
        self.payload = payload


def _base_url() -> str:
    return "https://api.buffer.com"


async def graphql(ctx, conn: dict, query: str, variables: dict | None = None, action: str = "call Buffer") -> dict:
    """Run a GraphQL query/mutation against Buffer's single endpoint."""
    token = conn.get("access_token", "")
    if not token:
        raise ClientFail(fail(BF_NOT_CONNECTED))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {"query": query}
    if variables:
        body["variables"] = variables
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_base_url(), headers=headers, json=body)
    except httpx.RequestError as exc:
        raise ClientFail(fail(BF_BACKEND_ERROR, f"network error while trying to {action}: {exc}")) from exc

    if resp.status_code == 401:
        raise ClientFail(fail(BF_UNAUTHORIZED, action))
    if resp.status_code == 403:
        raise ClientFail(fail(BF_FORBIDDEN, action))
    if resp.status_code == 429:
        raise ClientFail(fail(BF_RATE_LIMITED, action))
    if resp.status_code >= 500:
        raise ClientFail(fail(BF_BACKEND_ERROR, f"HTTP {resp.status_code} while trying to {action}"))

    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise ClientFail(fail(BF_RESPONSE_UNEXPECTED, f"non-JSON response while trying to {action}")) from exc

    if not isinstance(data, dict):
        raise ClientFail(fail(BF_RESPONSE_UNEXPECTED, f"unexpected response shape while trying to {action}"))

    if data.get("errors"):
        errs = data["errors"]
        first = errs[0] if isinstance(errs, list) and errs else {}
        msg = first.get("message", "unknown GraphQL error") if isinstance(first, dict) else str(first)
        if "not found" in msg.lower():
            raise ClientFail(fail(BF_NOT_FOUND, f"{action}: {msg}"))
        if resp.status_code == 200 and "unauthorized" in msg.lower():
            raise ClientFail(fail(BF_UNAUTHORIZED, f"{action}: {msg}"))
        raise ClientFail(fail(BF_GRAPHQL_ERROR, f"{action}: {msg}"))

    return data.get("data", {}) or {}
