"""Channels, Posts (Updates), Ideas, Account for Buffer Connector.

Confirmed against developers.buffer.com GraphQL schema conventions,
2026-08-29: channels query, posts query (filterable by channelId/status),
createPost mutation, deletePost mutation, createIdea mutation, account
query.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import buffer_client as bf
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListChannelsParams, ChannelList, Channel,
    ListPostsParams, PostList, Post,
    CreatePostParams, PostCreateResult,
    DeletePostParams, DeleteResult,
    CreateIdeaParams, IdeaCreateResult,
    GetAccountInfoParams, AccountInfo,
)

_CHANNELS_QUERY = """
query GetChannels {
  account {
    organizations {
      channels {
        id
        name
        service
        avatar
      }
    }
  }
}
"""

_POSTS_QUERY = """
query GetPosts($channelId: ID!, $status: PostStatus) {
  posts(channelId: $channelId, status: $status) {
    id
    text
    status
    scheduledAt
    channelId
  }
}
"""

_CREATE_POST_MUTATION = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    id
    status
  }
}
"""

_DELETE_POST_MUTATION = """
mutation DeletePost($id: ID!) {
  deletePost(id: $id) {
    success
  }
}
"""

_CREATE_IDEA_MUTATION = """
mutation CreateIdea($input: CreateIdeaInput!) {
  createIdea(input: $input) {
    id
  }
}
"""

_ACCOUNT_QUERY = """
query GetAccount {
  account {
    organizations {
      id
      name
    }
  }
}
"""


def _channel_entity(c: dict) -> Channel:
    return Channel(id=c.get("id", ""), name=c.get("name", ""), service=c.get("service", ""), avatar=c.get("avatar", ""))


def _post_entity(p: dict) -> Post:
    return Post(
        id=p.get("id", ""), text=p.get("text", ""), status=p.get("status", ""),
        scheduled_at=p.get("scheduledAt", ""), channel_id=p.get("channelId", ""),
    )


@chat.function(
    "list_channels",
    "List connected social channels (e.g. Instagram, X, LinkedIn, Facebook pages) on the connected Buffer account.",
    action_type="read", chain_callable=True, data_model=ChannelList,
)
async def list_channels(ctx, params: ListChannelsParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        data = await bf.graphql(ctx, conn, _CHANNELS_QUERY, action="list channels")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    orgs = ((data.get("account") or {}).get("organizations")) or []
    channels: list[dict] = []
    for org in orgs:
        channels.extend(org.get("channels", []) or [])
    return ActionResult.ok(ChannelList(channels=[_channel_entity(c) for c in channels]))


@chat.function(
    "list_posts",
    "List posts (updates) for one channel, optionally filtered by status ('sent' or 'due'/queued).",
    action_type="read", chain_callable=True, data_model=PostList,
)
async def list_posts(ctx, params: ListPostsParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    variables: dict = {"channelId": params.channel_id}
    if params.status:
        variables["status"] = params.status.upper()
    try:
        data = await bf.graphql(ctx, conn, _POSTS_QUERY, variables=variables, action="list posts")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    posts = data.get("posts", []) or []
    return ActionResult.ok(PostList(posts=[_post_entity(p) for p in posts]))


@chat.function(
    "create_post",
    "Create (schedule) a new post on a Buffer channel, optionally at a specific time or the next queue slot.",
    action_type="write", chain_callable=True, effects=["create:post"], data_model=PostCreateResult,
)
async def create_post(ctx, params: CreatePostParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    input_obj: dict = {"channelId": params.channel_id, "text": params.text}
    if params.scheduled_at:
        input_obj["scheduledAt"] = params.scheduled_at
    try:
        data = await bf.graphql(ctx, conn, _CREATE_POST_MUTATION, variables={"input": input_obj}, action="create post")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    result = data.get("createPost", {}) or {}
    return ActionResult.ok(PostCreateResult(id=result.get("id", ""), status=result.get("status", "")))


@chat.function(
    "delete_post",
    "Permanently delete a scheduled or sent Buffer post. Cannot be undone.",
    action_type="write", chain_callable=True, effects=["delete:post"], data_model=DeleteResult,
)
async def delete_post(ctx, params: DeletePostParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        await bf.graphql(ctx, conn, _DELETE_POST_MUTATION, variables={"id": params.post_id}, action="delete post")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    return ActionResult.ok(DeleteResult(deleted=True, id=params.post_id))


@chat.function(
    "create_idea",
    "Create a new post idea (a draft thought to turn into a post later) in the connected Buffer account.",
    action_type="write", chain_callable=True, effects=["create:idea"], data_model=IdeaCreateResult,
)
async def create_idea(ctx, params: CreateIdeaParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        data = await bf.graphql(ctx, conn, _CREATE_IDEA_MUTATION, variables={"input": {"text": params.text}}, action="create idea")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    result = data.get("createIdea", {}) or {}
    return ActionResult.ok(IdeaCreateResult(id=result.get("id", "")))


@chat.function(
    "get_account_info",
    "Read the connected Buffer account's own organization profile.",
    action_type="read", chain_callable=True, data_model=AccountInfo,
)
async def get_account_info(ctx, params: GetAccountInfoParams) -> ActionResult:
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if err:
        return err
    try:
        data = await bf.graphql(ctx, conn, _ACCOUNT_QUERY, action="get account info")
    except bf.ClientFail as exc:
        return ActionResult.error(exc.payload["message"], code=exc.payload["code"])
    orgs = ((data.get("account") or {}).get("organizations")) or []
    org = orgs[0] if orgs else {}
    return ActionResult.ok(AccountInfo(organization_id=org.get("id", ""), organization_name=org.get("name", "")))
