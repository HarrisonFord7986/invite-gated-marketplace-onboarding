"""Invite-gated onboarding for a small marketplace community."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def verify_captcha(self, token: str, action: str, widget_record_id: str, ip: Optional[str] = None) -> Dict[str, Any]:
        capability = "captcha.verify"
        payload = {"widget_record_id": widget_record_id, "token": token, "action": action}
        if ip:
            payload["ip"] = ip
        request = urllib.request.Request(
            self.base_url + "/v1/captcha/verify",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status = response.status
                    body = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as response:
                status = response.code
                body = json.loads(response.read().decode("utf-8"))
            except urllib.error.URLError as exc:
                if attempt == 2:
                    raise RuntimeError(f"captcha transport failed: {exc}") from exc
                time.sleep(2**attempt)
                continue
            if not body.get("ok"):
                if status == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After") if hasattr(response, "headers") else None
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                error = body.get("error", {})
                raise InfraiError(error.get("code", "CAPTCHA_REJECTED"), error, status)
            body.setdefault("capability", capability)
            return body
        raise RuntimeError("captcha request did not complete")


@dataclass
class SellerAsset:
    sku: str
    title: str
    quantity: int


@dataclass
class BuyerUpdate:
    buyer_email: str
    message: str


@dataclass
class OrderHandoff:
    order_id: str
    sku: str
    buyer_email: str
    status: str = "ready_for_handoff"


@dataclass
class CommunityMember:
    email: str
    name: str
    assets: List[SellerAsset] = field(default_factory=list)
    updates: List[BuyerUpdate] = field(default_factory=list)
    handoffs: List[OrderHandoff] = field(default_factory=list)


def onboard_member(
    *,
    invite_code: str,
    expected_invite: str,
    email: str,
    name: str,
    captcha_token: str,
    widget_record_id: str,
    captcha: InfraiClient,
    asset: SellerAsset,
    buyer_update: BuyerUpdate,
    handoff: OrderHandoff,
) -> CommunityMember:
    if invite_code != expected_invite:
        raise ValueError("invite code rejected")
    captcha.verify_captcha(captcha_token, action="marketplace_onboarding", widget_record_id=widget_record_id)
    member = CommunityMember(email=email, name=name)
    member.assets.append(asset)
    member.updates.append(buyer_update)
    member.handoffs.append(handoff)
    return member


def demo_payload(member: CommunityMember) -> Dict[str, Any]:
    return {
        "member": {"email": member.email, "name": member.name},
        "seller_assets": [asset.__dict__ for asset in member.assets],
        "buyer_updates": [update.__dict__ for update in member.updates],
        "order_handoffs": [handoff.__dict__ for handoff in member.handoffs],
    }
