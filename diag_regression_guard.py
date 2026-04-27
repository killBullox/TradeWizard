"""Verify the regression guard against today's bad config and the working
April-24 config."""
import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from orchestrator import Orchestrator
from models.database import Trade, async_session_factory, get_config
from sqlalchemy import select

async def main():
    o = Orchestrator()
    keys = list(Orchestrator._REGRESSION_GUARD_KEYS)
    async with async_session_factory() as s:
        current = {k: float(await get_config(k, s) or 0) for k in keys}
        rows = (await s.execute(
            select(Trade).where(Trade.status == "CLOSED")
            .order_by(Trade.close_time.desc()).limit(30)
        )).scalars().all()
    print(f"Current config: {current}")
    cur_rej = o._replay_sanity_check(rows, current)
    print(f"Current config would reject {cur_rej}/{len(rows)} of last 30 closed trades\n")

    # Bad config (meeting #136 of today, strangled prod): tightening
    # gate from 1.2 → 1.7 + adding floor 30 + tp 1.5 should be REJECTED.
    bad = {
        "rm_min_rr_gate": "1.7",
        "rm_min_sl_pips_floor": "30",
        "rm_max_tp_atr_mult": "1.5",
    }
    v = await o._check_regression(bad)
    print("Bad config (delta tightening):")
    print(f"  pending = {bad}")
    print(f"  guard verdict = {'REJECTED -- ' + v if v else 'ACCEPTED'}")

    # Slight loosening — should be ACCEPTED (delta negative or near zero).
    loosen = {
        "rm_min_rr_gate": "1.0",
        "rr_ratio": "1.2",
    }
    v = await o._check_regression(loosen)
    print("\nLoosening config:")
    print(f"  pending = {loosen}")
    print(f"  guard verdict = {'REJECTED -- ' + v if v else 'ACCEPTED'}")

    # Same as current — delta = 0, must be ACCEPTED
    noop = {"rm_min_rr_gate": "1.2"}
    v = await o._check_regression(noop)
    print("\nNo-op config:")
    print(f"  pending = {noop}")
    print(f"  guard verdict = {'REJECTED -- ' + v if v else 'ACCEPTED'}")

asyncio.run(main())
