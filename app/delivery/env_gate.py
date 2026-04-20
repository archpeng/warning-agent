"""Environment-gated delivery resolution helpers for live vendor seams."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Mapping

if TYPE_CHECKING:
    from app.delivery.runtime import EnvGatedLiveRoute

EnvGateState = Literal["ready", "missing_env"]


@dataclass(frozen=True)
class ResolvedFeishuTarget:
    channel: Literal["feishu"]
    chat_id: str | None = None
    open_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class EnvGatedLiveResolution:
    state: EnvGateState
    endpoint: str | None
    target: ResolvedFeishuTarget | None
    missing_env: tuple[str, ...]



def _read_env_value(env: Mapping[str, str | None], key: str | None) -> str | None:
    if not key:
        return None
    value = env.get(key)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None



def resolve_adapter_feishu_env_gate(
    route: "EnvGatedLiveRoute",
    env: Mapping[str, str | None] = os.environ,
) -> EnvGatedLiveResolution:
    missing_env: list[str] = []

    endpoint = _read_env_value(env, route.endpoint_env)
    if endpoint is None:
        missing_env.append(route.endpoint_env)
    else:
        endpoint = endpoint.rstrip("/")

    chat_id = _read_env_value(env, route.target.chat_id_env)
    open_id = _read_env_value(env, route.target.open_id_env)
    thread_id = _read_env_value(env, route.target.thread_id_env)

    if endpoint is None:
        if chat_id is None and open_id is None:
            if route.target.chat_id_env:
                missing_env.append(route.target.chat_id_env)
            if route.target.open_id_env:
                missing_env.append(route.target.open_id_env)
        return EnvGatedLiveResolution(
            state="missing_env",
            endpoint=None,
            target=None,
            missing_env=tuple(missing_env),
        )

    if chat_id is None and open_id is None:
        if route.target.chat_id_env:
            missing_env.append(route.target.chat_id_env)
        if route.target.open_id_env:
            missing_env.append(route.target.open_id_env)
        return EnvGatedLiveResolution(
            state="missing_env",
            endpoint=endpoint,
            target=None,
            missing_env=tuple(missing_env),
        )

    return EnvGatedLiveResolution(
        state="ready",
        endpoint=endpoint,
        target=ResolvedFeishuTarget(
            channel="feishu",
            chat_id=chat_id,
            open_id=open_id,
            thread_id=thread_id,
        ),
        missing_env=(),
    )
