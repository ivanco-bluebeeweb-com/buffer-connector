"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK, same reasoning as every other connector this session -- the
user's own Buffer account (channels, posts/updates, ideas) is managed via
their own API key.

WHY A STATIC API KEY, CONFIRMED against developers.buffer.com/guides/
getting-started.html and .../authentication.html, 2026-08-29: Buffer's
current API is GraphQL-only (its legacy REST v1 API was fully retired).
Auth is a single long-lived API key generated in the user's own Buffer
account (Settings > API), sent as `Authorization: Bearer {api_key}` on
every POST to the single GraphQL endpoint https://api.buffer.com. This
matches the same "paste your own long-lived token" pattern as every other
static-token connector this session -- no client_id/secret/refresh cycle.

WHY THIS CLIENT IS GRAPHQL, NOT REST (different from every sibling
connector's *_client.py this session): Buffer has exactly one HTTP
endpoint; every operation is a named GraphQL query or mutation in the
POST body, and errors come back as a top-level `errors` array in the JSON
response rather than as HTTP status codes alone.

WHY EACH CONNECTION STORES access_token only, SAME SHAPE AS EVERY OTHER
STATIC-TOKEN CONNECTOR THIS SESSION.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "buffer-connector",
    version="0.1.0",
    display_name="Buffer",
    icon="icon.svg",
    capabilities=["buffer:read", "buffer:write"],
    description=(
        "Connect your own Buffer account (API key) to manage social "
        "channels, scheduled posts, and post ideas via Buffer's GraphQL API."
    ),
)

chat = ChatExtension(ext)
