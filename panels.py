"""Panel UI -- connections list/connect form + the one required "App
settings" entry point. Uses slot="left" (SDK valid slots are
['bottom','center','chat-sidebar','left','overlay','right']) and the
ui.Button("Connect Buffer Channels (OAuth 2.0)", variant="primary", size="sm", icon="login"),
ui.Divider(),
ui.Text("Or connect via API Access Token", variant="caption"),
corrected Form/Input kwargs (ui.Form(submit_label=...),
ui.Text(variant="label") for each Input). NOTE: ui.Stack has no `style`
kwarg (caught during Sprout Social Connector's deploy) -- only align,
children, className, direction, gap, justify, sticky, wrap are valid.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule. Disconnect lives only in the
"App settings" screen (panels_settings.py). The one secondary "App
settings" button is always the LAST element at the bottom of the sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label, the placeholder text is always contextually
specific, the form's own container is stretched to the full width of the
left sidebar, and the form's inner content is stretched to fill that
container. The "How do I set this up?" instructions live ONLY in the help
modal below -- never duplicated as static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", icon="settings", on_click=ui.Call("__panel__buffer_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "Buffer account"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Buffer accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_form() -> ui.UINode:
    return ui.Form(
        submit_label="Connect Buffer",
        action=ui.Call("connect_buffer"),
        children=[
            ui.Stack(direction="v", gap=3, children=[
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Account label", variant="label"),
                    ui.Input(param_name="label", placeholder="e.g. Marketing team"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("API key", variant="label"),
                    ui.Input(param_name="access_token", placeholder="Paste your Buffer API key"),
                ]),
            ]),
        ],
    )


def _help_modal() -> ui.UINode:
    return ui.Modal(
        trigger=ui.Button("How do I set this up?", variant="ghost", size="sm"),
        title="Connecting Buffer",
        children=[
            ui.Stack(direction="v", gap=2, children=[
                ui.Text("1. Log in to your Buffer account.", variant="body"),
                ui.Text("2. Go to Settings > API.", variant="body"),
                ui.Text("3. Generate an API key.", variant="body"),
                ui.Text("4. Paste it in the form -- Webbee verifies it works before saving.", variant="body"),
            ]),
        ],
    )


@ext.panel("buffer_sidebar", slot="left")
async def buffer_sidebar(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    return ui.Stack(direction="v", gap=3, children=[
        ui.Text("Buffer", variant="heading"),
        _connections_section(connections),
        ui.Divider(),
        ui.Stack(direction="v", gap=2, children=[
            _connect_form(),
            _help_modal(),
        ]),
        ui.Spacer(),
        _settings_button(),
    ])