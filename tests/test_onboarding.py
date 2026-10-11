import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_onboarding import (
    BuyerUpdate,
    InfraiClient,
    OrderHandoff,
    SellerAsset,
    onboard_member,
)


class CaptchaStub:
    def __init__(self):
        self.calls = []

    def verify_captcha(self, token, action, widget_record_id):
        self.calls.append((token, action, widget_record_id))
        return {"ok": True, "data": {"verified": True}}


def test_valid_invite_creates_the_three_marketplace_records():
    captcha = CaptchaStub()
    member = onboard_member(
        invite_code="SHIP-2026",
        expected_invite="SHIP-2026",
        email="seller@example.com",
        name="Mina",
        captcha_token="captcha-token",
        widget_record_id="widget-123",
        captcha=captcha,
        asset=SellerAsset("lamp-01", "Desk lamp", 4),
        buyer_update=BuyerUpdate("buyer@example.com", "Packed"),
        handoff=OrderHandoff("order-1001", "lamp-01", "buyer@example.com"),
    )
    assert member.assets[0].sku == "lamp-01"
    assert member.updates[0].buyer_email == "buyer@example.com"
    assert member.handoffs[0].status == "ready_for_handoff"
    assert captcha.calls == [("captcha-token", "marketplace_onboarding", "widget-123")]


def test_wrong_invite_does_not_call_captcha():
    captcha = CaptchaStub()
    with pytest.raises(ValueError, match="invite code rejected"):
        onboard_member(
            invite_code="NOPE",
            expected_invite="SHIP-2026",
            email="seller@example.com",
            name="Mina",
            captcha_token="captcha-token",
            widget_record_id="widget-123",
            captcha=captcha,
            asset=SellerAsset("lamp-01", "Desk lamp", 4),
            buyer_update=BuyerUpdate("buyer@example.com", "Packed"),
            handoff=OrderHandoff("order-1001", "lamp-01", "buyer@example.com"),
        )
    assert captcha.calls == []


def test_captcha_request_includes_widget_record_id(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return b'{"ok": true, "data": {"verified": true}}'

    def urlopen(request, timeout):
        assert json.loads(request.data) == {
            "widget_record_id": "widget-123",
            "token": "captcha-token",
            "action": "marketplace_onboarding",
        }
        return Response()

    monkeypatch.setattr("src.marketplace_onboarding.urllib.request.urlopen", urlopen)
    assert InfraiClient(api_key="test-key").verify_captcha(
        "captcha-token", "marketplace_onboarding", "widget-123"
    )["ok"]
