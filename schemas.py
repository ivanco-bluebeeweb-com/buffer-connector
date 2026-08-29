"""Pydantic param/result models for Buffer Connector.

Same "explicit ConnectionScoped mixin + one params + one result class per
@chat.function" shape as every other connector this session's schemas.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectionScoped(BaseModel):
    connection_id: str = Field("", description="Which saved Buffer account to use. Omit if only one is connected.")


# ── Connection lifecycle ────────────────────────────────────────────────

class ConnectBufferParams(BaseModel):
    label: str = Field("", description="A friendly name for this account, e.g. 'Marketing team'.")
    access_token: str = Field(description="Your Buffer API key (Buffer Settings > API).")


class ConnectBufferResult(BaseModel):
    connection_id: str = ""
    label: str = ""
    organization_id: str = ""


class DisconnectBufferParams(BaseModel):
    connection_id: str = Field(description="The connection id to disconnect, from list_connections.")


class DeleteResult(BaseModel):
    deleted: bool = False
    id: str = ""


class BufferConnection(BaseModel):
    id: str = ""
    label: str = ""
    organization_id: str = ""


class ConnectionList(BaseModel):
    connections: list[BufferConnection] = Field(default_factory=list)


class ListConnectionsParams(BaseModel):
    pass


# ── Channels ─────────────────────────────────────────────────────────────

class ListChannelsParams(ConnectionScoped):
    pass


class Channel(BaseModel):
    id: str = ""
    name: str = ""
    service: str = ""
    avatar: str = ""


class ChannelList(BaseModel):
    channels: list[Channel] = Field(default_factory=list)


# ── Posts (Updates) ──────────────────────────────────────────────────────

class ListPostsParams(ConnectionScoped):
    channel_id: str = Field(description="The channel id to list posts for, from list_channels.")
    status: str = Field("", description="Optionally filter by status: 'sent', 'due' (queued/scheduled), or leave empty for all.")


class Post(BaseModel):
    id: str = ""
    text: str = ""
    status: str = ""
    scheduled_at: str = ""
    channel_id: str = ""


class PostList(BaseModel):
    posts: list[Post] = Field(default_factory=list)


class CreatePostParams(ConnectionScoped):
    channel_id: str = Field(description="The channel id to post to, from list_channels.")
    text: str = Field(description="The post text/caption.")
    scheduled_at: str = Field("", description="ISO 8601 timestamp to schedule the post at. Omit to add it to the next available queue slot.")


class PostCreateResult(BaseModel):
    id: str = ""
    status: str = ""


class DeletePostParams(ConnectionScoped):
    post_id: str = Field(description="The post id to delete, from list_posts.")


# ── Ideas ────────────────────────────────────────────────────────────────

class CreateIdeaParams(ConnectionScoped):
    text: str = Field(description="The idea's text content -- a draft thought to turn into a post later.")


class IdeaCreateResult(BaseModel):
    id: str = ""


# ── Account / Organization ───────────────────────────────────────────────

class GetAccountInfoParams(ConnectionScoped):
    pass


class AccountInfo(BaseModel):
    organization_id: str = ""
    organization_name: str = ""


# ── Reports ──────────────────────────────────────────────────────────────

class AuditBufferAccountParams(ConnectionScoped):
    pass


class BufferAccountReport(BaseModel):
    total_channels: int = 0
    channels_by_service: dict[str, int] = Field(default_factory=dict)
