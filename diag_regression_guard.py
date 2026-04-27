"""Verify the regression guard against today's bad config and the working
April-24 config."""
import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from orchestrator import Orchestrator

async def main():
    o = Orchestrator()

    # Bad config that strangled prod today (meeting #136 of 2026-04-27 09:14):
    bad = {
        "rm_min_rr_gate": "1.7",
        "rm_min_sl_pips_floor": "30",
        "rm_max_tp_atr_mult": "1.5",
        "rm_min_sl_atr_mult": "1.5",
    }
    v = await o._check_regression(bad)
    print("Bad config (today's strangulation):")
    print(f"  pending = {bad}")
    print(f"  guard verdict = {'REJECTED -- ' + v if v else 'ACCEPTED'}")

    # Working config (April 24 morning, 10 trades opened):
    good = {
        "rm_min_rr_gate": "1.2",
        "rm_min_sl_pips_floor": "0",
        "rm_max_tp_atr_mult": "3.0",
        "rm_min_sl_atr_mult": "1.0",
        "rr_ratio": "1.3",
    }
    v = await o._check_regression(good)
    print("\nGood config (apr24 morning):")
    print(f"  pending = {good}")
    print(f"  guard verdict = {'REJECTED -- ' + v if v else 'ACCEPTED'}")

asyncio.run(main())
