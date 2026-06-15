#!/usr/bin/env python3
"""
seed_acceptance_scenario_10000_shirts.py — Creates the standard acceptance scenario:
a Project + BuyerInquiry + pre-populated DynamicForm for 10,000 white cotton shirts.

Usage:
    BASE_URL=http://localhost:8000 uv run python scripts/seed_acceptance_scenario_10000_shirts.py
"""

import asyncio
import os
import json
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@giraffe.technology")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "GiraffeAdmin2024!")

INQUIRY_TEXT = (
    "We need 10,000 white 100% cotton T-shirts, size S/M/L/XL in equal ratio, "
    "GSM 180g, round neck, short sleeve, buyer label required. "
    "Trade term: FOB Shenzhen. Delivery deadline: 60 days from order confirmation. "
    "Destination: Hamburg, Germany. Packing: 12pcs per carton, individual polybag."
)


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Login
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        if login_resp.status_code != 200:
            # Try register first
            await client.post(
                "/api/auth/register",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
            login_resp = await client.post(
                "/api/auth/login",
                data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create project
        proj_resp = await client.post(
            "/api/projects",
            json={"title": "10,000 White Cotton T-Shirts — Acceptance Scenario"},
            headers=headers,
        )
        assert proj_resp.status_code == 201, proj_resp.text
        project = proj_resp.json()
        print(f"Project created: {project['id']}")

        # Create buyer inquiry
        inq_resp = await client.post(
            f"/api/projects/{project['id']}/buyer-inquiries",
            json={"raw_text": INQUIRY_TEXT},
            headers=headers,
        )
        assert inq_resp.status_code == 201, inq_resp.text
        inquiry = inq_resp.json()
        print(f"Inquiry created: {inquiry['id']}")

        # Create dynamic form
        form_resp = await client.post(
            f"/api/projects/{project['id']}/dynamic-forms",
            json={"inquiry_id": inquiry["id"]},
            headers=headers,
        )
        assert form_resp.status_code == 201, form_resp.text
        form = form_resp.json()
        print(f"Dynamic form created: form_id={form['form_id']}, version_id={form['id']}")

        result = {
            "project_id": project["id"],
            "inquiry_id": inquiry["id"],
            "form_id": str(form["form_id"]),
            "form_version_id": str(form["id"]),
        }

        print("\nAcceptance scenario seeded successfully.")
        print(json.dumps(result, indent=2))
        return result


if __name__ == "__main__":
    asyncio.run(main())
