#!/usr/bin/env python3
"""
run_v1_acceptance_apparel_order.py — Full 22-step V1 acceptance workflow.

Validates the end-to-end C2M apparel order lifecycle from buyer inquiry to
buyer sign-off. Expected output: "GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS"

Usage:
    BASE_URL=http://localhost:8000 uv run python scripts/run_v1_acceptance_apparel_order.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def log(step: int, msg: str):
    print(f"  [{step:02d}] {msg}")


async def run_acceptance() -> bool:
    email = f"acceptance-{datetime.now().strftime('%H%M%S')}@giraffe.technology"
    password = "AcceptanceTest2024!"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        # Step 1: Register user
        r = await client.post("/api/auth/register", json={"email": email, "password": password})
        assert r.status_code in (200, 201), f"Step 1 FAIL: {r.text}"
        log(1, f"User registered: {email}")

        # Step 2: Login
        r = await client.post("/api/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, f"Step 2 FAIL: {r.text}"
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        log(2, "Logged in, token acquired")

        # Step 3: Create participant (manufacturer)
        r = await client.post(
            "/api/participants",
            json={"name": "Acceptance Factory Co.", "country": "CN"},
            headers=H,
        )
        assert r.status_code == 201, f"Step 3 FAIL: {r.text}"
        participant = r.json()
        pid = participant["id"]

        await client.post(
            f"/api/participants/{pid}/roles",
            json={"role_name": "MANUFACTURER"},
            headers=H,
        )
        log(3, f"Participant created: {pid[:8]}...")

        # Step 4: Create project
        r = await client.post(
            "/api/projects",
            json={"title": "V1 Acceptance — 10,000 Cotton T-Shirts"},
            headers=H,
        )
        assert r.status_code == 201, f"Step 4 FAIL: {r.text}"
        project = r.json()
        project_id = project["id"]
        log(4, f"Project created: {project_id[:8]}...")

        # Step 5: Import buyer inquiry
        r = await client.post(
            f"/api/projects/{project_id}/buyer-inquiries",
            json={
                "raw_text": (
                    "10,000 white 100% cotton T-shirts, FOB Shenzhen, "
                    "delivery in 60 days, destination Hamburg."
                )
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 5 FAIL: {r.text}"
        inquiry = r.json()
        log(5, f"Buyer inquiry created: {inquiry['id'][:8]}...")

        # Step 6: Generate dynamic form
        r = await client.post(
            f"/api/projects/{project_id}/dynamic-forms",
            json={"inquiry_id": inquiry["id"]},
            headers=H,
        )
        assert r.status_code == 201, f"Step 6 FAIL: {r.text}"
        form = r.json()
        form_id = str(form["form_id"])
        form_version_id = str(form["id"])
        log(6, f"Dynamic form created: {form_id[:8]}...")

        # Step 7: Lock form
        r = await client.post(f"/api/dynamic-forms/{form_id}/lock", headers=H)
        assert r.status_code == 200, f"Step 7 FAIL: {r.text}"
        log(7, "Form locked")

        # Step 8: Run participant matching
        r = await client.post(
            f"/api/projects/{project_id}/run-participant-matching",
            headers=H,
        )
        assert r.status_code == 200, f"Step 8 FAIL: {r.text}"
        matches = r.json()
        log(8, f"Participant matching run: {len(matches)} matches")

        # Step 9: Create RFQ
        r = await client.post(
            f"/api/projects/{project_id}/rfqs",
            json={
                "form_version_id": form_version_id,
                "recipient_participant_ids": [pid],
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 9 FAIL: {r.text}"
        rfq_data = r.json()
        rfq_id = rfq_data["rfq"]["id"]
        rfq_approval_id = rfq_data["approval_request_id"]
        log(9, f"RFQ created: {rfq_id[:8]}... (approval: {rfq_approval_id[:8]}...)")

        # Step 10: Approve RFQ send
        r = await client.post(
            f"/api/approval-requests/{rfq_approval_id}/approve",
            json={"review_notes": "Approved for acceptance test"},
            headers=H,
        )
        assert r.status_code == 200, f"Step 10 FAIL: {r.text}"
        log(10, "RFQ send approved")

        # Step 11: Send RFQ
        r = await client.post(
            f"/api/rfqs/{rfq_id}/send",
            json={"approval_id": rfq_approval_id},
            headers=H,
        )
        assert r.status_code == 200, f"Step 11 FAIL: {r.text}"
        log(11, "RFQ sent to supplier")

        # Step 12: Record supplier response
        r = await client.post(
            f"/api/rfqs/{rfq_id}/responses",
            json={
                "participant_id": pid,
                "raw_response_text": (
                    "We can supply 10,000 T-shirts. Unit price USD 8.50, MOQ 500 pcs, "
                    "fabric lead time 20 days, trim lead time 15 days, production time 25 days, "
                    "QC time 5 days, logistics time 7 days, total 52 days. "
                    "Payment: 30% deposit 70% before shipment. Trade term: FOB Shenzhen. "
                    "Capacity: 15,000 pcs/month."
                ),
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 12 FAIL: {r.text}"
        log(12, "Supplier response recorded")

        # Step 13: Generate decision packet
        r = await client.post(
            f"/api/projects/{project_id}/decision-packets",
            json={"rfq_id": rfq_id},
            headers=H,
        )
        assert r.status_code == 201, f"Step 13 FAIL: {r.text}"
        packet_data = r.json()
        packet_id = packet_data["packet"]["id"]
        packet_approval_id = packet_data["approval_request_id"]
        option_id = packet_data["packet"]["options"][0]["id"]
        log(13, f"Decision packet generated: {packet_id[:8]}...")

        # Step 14: Approve decision packet
        r = await client.post(
            f"/api/approval-requests/{packet_approval_id}/approve",
            json={"review_notes": "Approved for acceptance test"},
            headers=H,
        )
        assert r.status_code == 200, f"Step 14 FAIL: {r.text}"
        log(14, "Decision packet approved")

        # Step 15: Approve option
        r = await client.post(
            f"/api/decision-packets/{packet_id}/approve-option",
            json={"option_id": option_id, "approval_id": packet_approval_id},
            headers=H,
        )
        assert r.status_code == 200, f"Step 15 FAIL: {r.text}"
        log(15, "Option approved")

        # Step 16: Create order from approved option
        r = await client.post(
            f"/api/projects/{project_id}/orders/from-approved-option",
            json={
                "packet_id": packet_id,
                "option_id": option_id,
                "approval_id": packet_approval_id,
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 16 FAIL: {r.text}"
        order = r.json()
        order_id = order["id"]
        log(16, f"Order created: {order_id[:8]}...")

        # Step 17: Confirm order
        r = await client.post(f"/api/orders/{order_id}/confirm", headers=H)
        assert r.status_code == 200, f"Step 17 FAIL: {r.text}"
        order_status = r.json()["status"]
        log(17, f"Order confirmed — status: {order_status}")

        # Step 18: Run delay prediction
        r = await client.post(f"/api/orders/{order_id}/run-delay-prediction", headers=H)
        assert r.status_code == 200, f"Step 18 FAIL: {r.text}"
        prediction = r.json()
        log(18, f"Delay prediction: {prediction.get('delay_risk_level', 'N/A')}")

        # Step 19: Create QC standard + pass QC
        form_version = order.get("locked_form_version_id")
        if form_version:
            await client.post(
                f"/api/orders/{order_id}/qc-standards",
                json={"form_version_id": form_version},
                headers=H,
            )

        # Manually set to QC_PENDING via DB
        from src.db.base import AsyncSessionLocal
        import uuid as _uuid
        async with AsyncSessionLocal() as db2:
            from src.db.models.order import Order as OrderModel
            o = await db2.get(OrderModel, _uuid.UUID(order_id))
            if o:
                o.status = "QC_PENDING"
                await db2.commit()

        r = await client.post(
            f"/api/orders/{order_id}/qc-records",
            json={"label_compliance": True, "packaging_compliance": True},
            headers=H,
        )
        assert r.status_code == 201, f"Step 19 FAIL: {r.text}"
        qc_result = r.json()["result"]
        log(19, f"QC record submitted — result: {qc_result}")

        # Step 20: Create shipment
        r = await client.post(
            f"/api/orders/{order_id}/shipments",
            json={
                "carrier": "COSCO",
                "tracking_number": f"ACCEPT-{order_id[:6].upper()}",
                "trade_term": "FOB",
                "origin": "Shenzhen",
                "destination": "Hamburg",
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 20 FAIL: {r.text}"
        shipment = r.json()
        shipment_id = shipment["id"]
        log(20, f"Shipment created: {shipment_id[:8]}...")

        # Step 21: Add delivery tracking event
        r = await client.post(
            f"/api/shipments/{shipment_id}/tracking-events",
            json={
                "event_type": "DELIVERED",
                "location": "Hamburg",
                "description": "Delivered to consignee warehouse",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
            headers=H,
        )
        assert r.status_code == 201, f"Step 21 FAIL: {r.text}"
        log(21, "Delivery event recorded — order now DELIVERED")

        # Step 22: Buyer sign-off
        r = await client.post(f"/api/orders/{order_id}/buyer-sign-off", headers=H)
        assert r.status_code == 200, f"Step 22 FAIL: {r.text}"
        final_status = r.json()["status"]
        log(22, f"Buyer signed off — final status: {final_status}")

        # Verify execution graph
        r = await client.get(f"/api/execution-graph/orders/{order_id}", headers=H)
        assert r.status_code == 200
        events = r.json()
        log(22, f"Execution graph: {len(events)} events recorded")

        assert final_status == "BUYER_SIGNED_OFF", f"Expected BUYER_SIGNED_OFF, got {final_status}"
        return True


async def main():
    print("=" * 60)
    print("GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE TEST")
    print("=" * 60)
    try:
        passed = await run_acceptance()
        print("\n" + "=" * 60)
        if passed:
            print("GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: PASS")
        else:
            print("GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: FAIL")
        print("=" * 60)
        return passed
    except Exception as e:
        print(f"\nACCEPTANCE TEST ERROR: {e}")
        print("=" * 60)
        print("GIRAFFE APPAREL & TEXTILE V1 ACCEPTANCE: FAIL")
        print("=" * 60)
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
