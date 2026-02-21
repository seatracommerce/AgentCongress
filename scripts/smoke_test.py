#!/usr/bin/env python3
"""
Smoke test: seeds a fake bill and runs a real debate (requires ANTHROPIC_API_KEY).

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/agentcongress
  export DRY_RUN=true
  python scripts/smoke_test.py
"""
from __future__ import annotations

import asyncio
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from backend.database import AsyncSessionLocal, engine, Base
    from backend.models.bill import Bill
    from backend.agents.debate_engine import run_debate
    from backend.services.social_publisher import publish_debate
    from sqlalchemy import select

    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Seed a test bill
        print("Seeding test bill...")
        test_bill_id = "119-hr-smoke-test"
        result = await db.execute(select(Bill).where(Bill.congress_bill_id == test_bill_id))
        bill = result.scalar_one_or_none()

        if not bill:
            bill = Bill(
                congress_bill_id=test_bill_id,
                title="American Healthcare Expansion and Cost Reduction Act",
                summary=(
                    "A comprehensive bill to expand Medicaid eligibility to all adults below 200% of the federal "
                    "poverty line, cap insulin prices at $35/month, allow Medicare to negotiate drug prices, "
                    "and fund 500 new community health centers in rural and underserved areas. "
                    "Estimated cost: $400 billion over 10 years, offset by pharmaceutical rebates and a 3.8% "
                    "net investment income surtax on incomes above $400,000."
                ),
                chamber="House",
                status="Roll call vote scheduled",
                sponsor="Rep. Johnson, D. (D-CA)",
                bill_type="hr",
                congress_number=119,
                importance_score=100.0,
                debate_triggered=True,
            )
            db.add(bill)
            await db.commit()
            await db.refresh(bill)
            print(f"Created bill ID={bill.id}")
        else:
            print(f"Using existing bill ID={bill.id}")

        # Run debate
        print(f"\nRunning debate for bill: {bill.title}")
        print("This will make Claude API calls — ~25 calls, expect 2-3 minutes...\n")
        debate = await run_debate(db, bill)

        print(f"\n{'='*60}")
        print(f"DEBATE COMPLETE")
        print(f"  Result:       {debate.result.upper()}")
        print(f"  Yea seats:    {debate.yea_seats}")
        print(f"  Nay seats:    {debate.nay_seats}")
        print(f"  Present:      {debate.present_seats}")
        print(f"  Summary:      {debate.summary}")
        print(f"{'='*60}\n")

        # Dry-run publish
        print("Publishing to X (DRY_RUN mode — will only log)...")
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(type(debate)).where(type(debate).id == debate.id)
            .options(selectinload(type(debate).votes))
        )
        debate_with_votes = result.scalar_one()
        await publish_debate(db, debate_with_votes)

        print("\nSmoke test complete. Check:")
        print(f"  GET http://localhost:8000/debates/{debate.id}")


if __name__ == "__main__":
    asyncio.run(main())
