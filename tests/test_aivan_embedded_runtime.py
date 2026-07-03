from aivan import __version__
from aivan.pricing.quote_calculator import calculate_buyer_quote
from aivan.schemas.openclaw import OpenClawEvent
from aivan.schemas.requirement import BuyerRequirement


def test_embedded_aivan_package_exposes_core_trade_runtime():
    requirement = BuyerRequirement(
        project_id="ga-aivan-smoke",
        product_type="cotton shirt",
        quantity=10000,
        destination="Vancouver",
        language="en",
    )
    event = OpenClawEvent(
        conversation_id="conv-ga-aivan-smoke",
        message_id="msg-ga-aivan-smoke",
        message_text="Need 10000 cotton shirts for Vancouver.",
    )
    quote = calculate_buyer_quote(
        unit_price=4.0,
        quantity=requirement.quantity or 0,
        international_logistics_fee=1000.0,
        margin_rate=0.2,
    )

    assert __version__
    assert requirement.is_complete()
    assert event.source == "openclaw"
    assert quote["buyer_total"] == 51250.0
    assert quote["buyer_unit_price"] == 5.13
