"""Telegram Bot API (free). Falls back to the in-app Telegram simulator when no token is set."""
import asyncio
import json
from typing import Callable, Optional

import httpx

from .. import store
from ..config import settings


def _api(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.telegram_token}/{method}"


async def send_message(client: httpx.AsyncClient, *, chat_id: str, text: str, to_label: str,
                       channel: str, buttons: Optional[list] = None, run_id: Optional[str] = None) -> bool:
    """buttons: list of (label, callback_data). Always recorded in the simulator outbox."""
    delivered = "simulated"
    ok = False
    if settings.telegram_enabled and chat_id:
        payload: dict = {"chat_id": chat_id, "text": text[:4000]}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": [[{"text": l, "callback_data": d} for l, d in buttons]]}
        try:
            r = await client.post(_api("sendMessage"), json=payload, timeout=settings.http_timeout)
            r.raise_for_status()
            delivered, ok = "telegram", True
        except Exception as e:  # keep the pipeline alive; the simulator still shows the message
            delivered = f"telegram-failed ({type(e).__name__})"
    store.add_outbox(channel=channel, to=to_label, text=text, buttons=buttons, run_id=run_id, delivered=delivered)
    return ok


async def poll_updates(handler: Callable[[str], str]) -> None:
    """Long-polling loop (no public webhook URL needed for local use)."""
    offset = None
    async with httpx.AsyncClient(timeout=40) as client:
        while True:
            try:
                params = {"timeout": 25, "allowed_updates": json.dumps(["callback_query"])}
                if offset is not None:
                    params["offset"] = offset
                r = await client.get(_api("getUpdates"), params=params)
                for upd in r.json().get("result", []):
                    offset = upd["update_id"] + 1
                    cq = upd.get("callback_query")
                    if cq:
                        text = handler(cq.get("data", ""))
                        await client.post(_api("answerCallbackQuery"),
                                          json={"callback_query_id": cq["id"], "text": text})
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(3)
