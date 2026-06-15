#!/usr/bin/env python3
"""
seed_reference_data.py — Creates Tenant, Admin User, and 8 sample participants.

Usage:
    BASE_URL=http://localhost:8000 uv run python scripts/seed_reference_data.py
"""

import asyncio
import os
import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

PARTICIPANTS = [
    {
        "name": "Shenzhen Garment Manufacturing Co.",
        "country": "CN",
        "role": "MANUFACTURER",
        "profile": {
            "product_categories": ["T-shirts", "Polo shirts", "Casual wear"],
            "production_capacity_pcs_per_month": 50000,
            "moq_pcs": 500,
            "fabric_types": ["cotton", "polyester", "blended"],
            "lead_time_days": 45,
            "trade_terms": ["FOB", "CIF"],
            "location_city": "Shenzhen",
            "quality_certifications": ["ISO9001", "OEKO-TEX"],
        },
    },
    {
        "name": "Guangzhou Fabric Sourcing Ltd.",
        "country": "CN",
        "role": "FABRIC_SUPPLIER",
        "profile": {
            "product_categories": ["Woven fabrics", "Knit fabrics"],
            "fabric_types": ["cotton", "linen", "polyester"],
            "moq_pcs": 200,
            "lead_time_days": 20,
            "trade_terms": ["EXW", "FOB"],
            "location_city": "Guangzhou",
        },
    },
    {
        "name": "Yiwu Trim & Accessory Factory",
        "country": "CN",
        "role": "TRIM_SUPPLIER",
        "profile": {
            "product_categories": ["Buttons", "Zippers", "Labels", "Tags"],
            "moq_pcs": 1000,
            "lead_time_days": 15,
            "trade_terms": ["EXW"],
            "location_city": "Yiwu",
        },
    },
    {
        "name": "Shanghai Packaging Solutions Co.",
        "country": "CN",
        "role": "PACKAGING_SUPPLIER",
        "profile": {
            "product_categories": ["Poly bags", "Cartons", "Hangtags"],
            "moq_pcs": 500,
            "lead_time_days": 12,
            "trade_terms": ["EXW", "FOB"],
            "location_city": "Shanghai",
        },
    },
    {
        "name": "COSCO Shipping Lines",
        "country": "CN",
        "role": "LOGISTICS_PROVIDER",
        "profile": {
            "trade_terms": ["FOB", "CIF", "CFR"],
            "routes": ["Asia-Europe", "Asia-North America", "Intra-Asia"],
            "lead_time_days": 28,
            "location_city": "Shanghai",
        },
    },
    {
        "name": "Dongguan Premium Garments Ltd.",
        "country": "CN",
        "role": "MANUFACTURER",
        "profile": {
            "product_categories": ["Outerwear", "Jackets", "Trousers"],
            "production_capacity_pcs_per_month": 30000,
            "moq_pcs": 300,
            "fabric_types": ["wool", "nylon", "polyester"],
            "lead_time_days": 60,
            "trade_terms": ["FOB", "EXW"],
            "location_city": "Dongguan",
            "quality_certifications": ["ISO9001", "BSCI"],
        },
    },
    {
        "name": "Hangzhou Silk & Textile Mill",
        "country": "CN",
        "role": "FABRIC_SUPPLIER",
        "profile": {
            "product_categories": ["Silk fabrics", "High-end wovens"],
            "fabric_types": ["silk", "viscose", "chiffon"],
            "moq_pcs": 100,
            "lead_time_days": 25,
            "trade_terms": ["EXW", "FOB"],
            "location_city": "Hangzhou",
        },
    },
    {
        "name": "Hamburg QC Inspection Services GmbH",
        "country": "DE",
        "role": "QC_INSPECTOR",
        "profile": {
            "inspection_types": ["Pre-shipment", "During production", "Final random inspection"],
            "lead_time_days": 5,
            "trade_terms": ["EXW"],
            "location_city": "Hamburg",
            "certifications": ["SGS", "Bureau Veritas"],
        },
    },
]


async def main():
    admin_email = "admin@giraffe.technology"
    admin_password = "GiraffeAdmin2024!"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # Register admin user
        print("Registering admin user...")
        reg_resp = await client.post(
            "/api/auth/register",
            json={"email": admin_email, "password": admin_password},
        )
        if reg_resp.status_code not in (200, 201, 409):
            print(f"  WARNING: Registration returned {reg_resp.status_code}: {reg_resp.text}")
        else:
            print(f"  Admin user: {admin_email}")

        # Login
        login_resp = await client.post(
            "/api/auth/login",
            data={"username": admin_email, "password": admin_password},
        )
        if login_resp.status_code != 200:
            print(f"  ERROR: Login failed: {login_resp.text}")
            return
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create participants
        print(f"\nCreating {len(PARTICIPANTS)} reference participants...")
        for p in PARTICIPANTS:
            create_resp = await client.post(
                "/api/participants",
                json={"name": p["name"], "country": p["country"]},
                headers=headers,
            )
            if create_resp.status_code != 201:
                print(f"  SKIP: {p['name']} — {create_resp.status_code}")
                continue

            participant = create_resp.json()
            pid = participant["id"]

            # Assign role
            role_resp = await client.post(
                f"/api/participants/{pid}/roles",
                json={"role_name": p["role"]},
                headers=headers,
            )

            # Update profile
            profile_resp = await client.patch(
                f"/api/participants/{pid}",
                json={"profile": p["profile"]},
                headers=headers,
            )

            print(f"  ✓ {p['name']} [{p['role']}] (id={pid[:8]}...)")

    print("\nReference data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(main())
