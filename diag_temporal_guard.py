"""Sanity-test the new temporal-coverage guard.

Scenario A: the broken config that bit us on 2026-04-27 (overlap windows
covering 67% of NY kill zone in Rome time). MUST be rejected.

Scenario B: a sane config (overlap windows at NY-open volatility burst,
14:30-15:00 UTC, only 17% of NY kill zone). MUST be accepted.

Scenario C: overlap_block_enabled=0. Always accepted regardless of windows.
"""
import os, sys, json, asyncio
os.environ['SYSTEM_MODE'] = 'production'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from orchestrator import Orchestrator
from models.database import async_session_factory, set_config, get_config


async def with_config(overrides):
    async with async_session_factory() as s:
        for k, v in overrides.items():
            await set_config(k, v, s)


async def restore_originals(originals):
    async with async_session_factory() as s:
        for k, v in originals.items():
            if v is not None:
                await set_config(k, v, s)


async def main():
    o = Orchestrator()

    # Snapshot original values so we don't pollute prod DB
    keys = list(Orchestrator._TEMPORAL_GATE_KEYS)
    async with async_session_factory() as s:
        originals = {k: await get_config(k, s) for k in keys}
    print(f"original config: {originals}\n")

    try:
        # Force kill_zones to current prod value used today
        await with_config({
            "kill_zones": '[{"start":"06:30","end":"11:00"},{"start":"14:00","end":"17:00"}]',
        })

        # === Scenario A: bug config ===
        pending_A = {
            "overlap_block_enabled": "1",
            "overlap_windows_utc": '[{"start":"12:00","end":"13:00"},{"start":"14:00","end":"15:30"}]',
        }
        v = await o._check_temporal_coverage(pending_A)
        print("Scenario A (broken config):")
        print(f"  pending = {pending_A}")
        print(f"  guard verdict = {'REJECTED — ' + v if v else 'ACCEPTED'}\n")
        assert v is not None, "guard should reject"

        # === Scenario B: sane narrow window ===
        pending_B = {
            "overlap_block_enabled": "1",
            "overlap_windows_utc": '[{"start":"12:30","end":"12:45"}]',
        }
        v = await o._check_temporal_coverage(pending_B)
        print("Scenario B (narrow 15-min news window):")
        print(f"  pending = {pending_B}")
        print(f"  guard verdict = {'REJECTED — ' + v if v else 'ACCEPTED'}\n")
        assert v is None, "guard should accept narrow window"

        # === Scenario C: block disabled ===
        pending_C = {
            "overlap_block_enabled": "0",
            "overlap_windows_utc": '[{"start":"00:00","end":"23:59"}]',
        }
        v = await o._check_temporal_coverage(pending_C)
        print("Scenario C (block disabled, windows ignored):")
        print(f"  pending = {pending_C}")
        print(f"  guard verdict = {'REJECTED — ' + v if v else 'ACCEPTED'}\n")
        assert v is None, "guard should accept when block disabled"

        print("All three scenarios behave as expected.")
    finally:
        await restore_originals(originals)
        print("Restored original config.")


asyncio.run(main())
