import os, sys, asyncio
os.environ['SYSTEM_MODE'] = 'lab'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from services.setup_diagnostics import diagnose_setups, format_diagnostics_for_prompt

async def main():
    d = await diagnose_setups(days_back=14)
    print(format_diagnostics_for_prompt(d))
    print()
    print("--- RAW VERDICTS ---")
    for c in d['cells']:
        print(f"{c['setup']:<14}{c['symbol']:<10}{c['session']:<10}"
              f"n={c['n']} WR={c['wr']}% E={c['expectancy_r']}R -> {c['verdict']}")

asyncio.run(main())
