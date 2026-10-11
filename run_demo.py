import os

from src.marketplace_onboarding import InfraiClient, OrderHandoff, SellerAsset, BuyerUpdate, onboard_member, demo_payload


def main() -> None:
    client = InfraiClient()
    member = onboard_member(
        invite_code=os.environ.get("MARKETPLACE_INVITE", "SHIP-2026"),
        expected_invite="SHIP-2026",
        email="seller@example.com",
        name="Mina",
        captcha_token=os.environ.get("CAPTCHA_TOKEN", ""),
        widget_record_id=os.environ.get("CAPTCHA_WIDGET_RECORD_ID", ""),
        captcha=client,
        asset=SellerAsset("lamp-01", "Desk lamp", 4),
        buyer_update=BuyerUpdate("buyer@example.com", "Your lamp is packed."),
        handoff=OrderHandoff("order-1001", "lamp-01", "buyer@example.com"),
    )
    print(demo_payload(member))


if __name__ == "__main__":
    main()
