# Execution Graph — Project `e2f71a01-5d5b-43ea-a578-5c0a787d3fef`

## Buyer

- **actor_id:** da35f508-4da5-4ecb-90fb-55d29cb9edd5
- **name:** V12 Buyer sample
- **actor_type:** BUYER

## Supplier

- **actor_id:** f322b95c-2a8e-4308-ad2b-f24b8f63964d
- **name:** V12 Supplier sample
- **actor_type:** SUPPLIER

## Structured Requirement

- **requirement_id:** b624542b-c0e4-408b-b97e-79efc18bb481
- **category:** Apparel
- **quantity:** 300
- **material:** Cotton
- **deadline:** 2026-09-30
- **destination:** New York
- **confidence_score:** 0.91

## Supplier Inquiries

- inquiry_id=`6fc11529-b793-4178-a389-6d752bd01549` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` status=`SENT` to=`f322b95c-2a8e-4308-ad2b-f24b8f63964d`

## Supplier Responses (all versions)

- response_id=`5697e8cb-cf09-47d7-b622-2c34d1570e3d` inquiry_id=`6fc11529-b793-4178-a389-6d752bd01549` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` can_supply=`True` price=`8.5 USD` lead_time_days=`30`

## Supplier Response Rollup

- **rollup_id:** 7d99ed91-f31a-4866-849e-ac0a73081472
- **can_accept_order:** True
- **main_capacity_summary:** _Not provided_
- **completeness_score:** 1.0
- **confidence_score:** 0.88

## Selected Edge

- **edge_id:** 3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3
- **status:** APPROVED
- **edge_type:** MAIN_B_TO_M
- **inquiry_id:** 6fc11529-b793-4178-a389-6d752bd01549
- **response_id:** 5697e8cb-cf09-47d7-b622-2c34d1570e3d
- **from_actor_id:** da35f508-4da5-4ecb-90fb-55d29cb9edd5
- **to_actor_id:** f322b95c-2a8e-4308-ad2b-f24b8f63964d

## Execution Event Timeline

1. ORDER_CONFIRMED @ 2026-06-13T18:01:08.846342 [event_id=5569096d]
2. PRODUCTION_UPDATE_RECEIVED @ 2026-06-13T18:01:08.847194 [event_id=5cc9be8c]
3. QC_UPDATE_RECEIVED @ 2026-06-13T18:01:08.848298 [event_id=706b9297]
4. LOGISTICS_HANDOVER_RECEIVED @ 2026-06-13T18:01:08.848601 [event_id=6075bf10]
5. ORDER_CLOSED @ 2026-06-13T18:01:08.848817 [event_id=d2ac24c1]

## Execution Events (detail)

- event_id=`5569096d-b46e-4fa2-a552-21ba6f30ee04` type=`ORDER_CONFIRMED` actor_id=`f322b95c-2a8e-4308-ad2b-f24b8f63964d` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` at=`2026-06-13T18:01:08.846342`
- event_id=`5cc9be8c-6f9e-45d0-b8f5-058d36ffa4a9` type=`PRODUCTION_UPDATE_RECEIVED` actor_id=`f322b95c-2a8e-4308-ad2b-f24b8f63964d` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` at=`2026-06-13T18:01:08.847194`
- event_id=`706b9297-a838-40d7-a455-8154cef25e0d` type=`QC_UPDATE_RECEIVED` actor_id=`f322b95c-2a8e-4308-ad2b-f24b8f63964d` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` at=`2026-06-13T18:01:08.848298`
- event_id=`6075bf10-4b6a-4e85-a7de-297b426068aa` type=`LOGISTICS_HANDOVER_RECEIVED` actor_id=`f322b95c-2a8e-4308-ad2b-f24b8f63964d` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` at=`2026-06-13T18:01:08.848601`
- event_id=`d2ac24c1-abc0-4a7d-a4c3-76ef49683208` type=`ORDER_CLOSED` actor_id=`f322b95c-2a8e-4308-ad2b-f24b8f63964d` edge_id=`3f7b8fd4-dfcb-4897-9372-b2a8a67d40d3` at=`2026-06-13T18:01:08.848817`
