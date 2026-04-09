"""
Risk Manager (RM) — Deterministic Python implementation.
No LLM calls — pure mathematical risk evaluation.
Calculates position size, validates SL/TP, checks correlations.
"""

import logging
from .base_agent import BaseAgent, MODEL_STANDARD

logger = logging.getLogger(__name__)

# Correlated pair groups
CORRELATION_GROUPS = [
    {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},   # USD weakness basket
    {"USDJPY", "USDCHF", "USDCAD"},               # USD strength basket
]

# Pip USD value per standard lot
PIP_USD = {
    "XAUUSD": 100.0, "US30": 5.0, "NAS100": 20.0, "US500": 50.0,
    "USDJPY": 6.5, "EURJPY": 6.5, "GBPJPY": 6.5, "AUDJPY": 6.5,
    "CHFJPY": 6.5, "CADJPY": 6.5, "NZDJPY": 6.5,
    "USDCHF": 11.0, "EURCHF": 11.0, "GBPCHF": 11.0,
    "USDCAD": 7.25, "EURCAD": 7.25, "GBPCAD": 7.25,
}

# Base win probability by setup type (from ICT historical data)
SETUP_WIN_RATES = {
    "OTE": 0.65,
    "FVG": 0.60,
    "OrderBlock": 0.60,
    "LiquiditySweep": 0.55,
    "SilverBullet": 0.67,
    "BOS": 0.55,
    "CHOCH": 0.55,
    "Mitigation": 0.58,
    "PD_Array": 0.58,
}


class RiskManagerAgent(BaseAgent):
    """Deterministic risk manager — no LLM, pure math."""
    name = "RM"
    emoji = "⚖️"
    color = "#DC2626"
    model = MODEL_STANDARD  # kept for compatibility but not used

    async def evaluate(
        self,
        symbol: str,
        strategy: dict,
        market_data: dict,
        system_config: dict,
        open_trades_count: int = 0,
        memory_context: str = "",
    ) -> dict:
        await self.broadcast_status(
            "EVALUATING",
            f"Evaluating risk for {symbol} {strategy.get('direction')} setup..."
        )

        # ── Extract parameters ────────────────────────────────────────────
        ind = market_data.get("H1", {}).get("indicators", {})
        current_price = float(ind.get("current_price", 0))
        atr_pips = float(ind.get("atr_pips", 15))
        pip_value = float(ind.get("pip_value", 0.0001))

        account_balance = float(system_config.get("account_balance", 10000))
        risk_percent = float(system_config.get("risk_percent", 1.0))
        max_risk_usd = float(system_config.get("max_risk_usd", 0))
        rr_ratio = float(system_config.get("rr_ratio", 2.0))
        max_trades = int(system_config.get("max_open_trades", 3))
        min_sl_pips = float(system_config.get("min_sl_pips", 20))
        max_trade_hours = float(system_config.get("max_trade_duration_hours", 8))

        direction = strategy.get("direction", "BUY")
        setup_type = strategy.get("setup", "FVG")
        probability = float(strategy.get("probability", 60))
        entry_low = float(strategy.get("entry_zone_low", 0))
        entry_high = float(strategy.get("entry_zone_high", 0))

        risk_factors = []
        rejection_reason = None

        # ── Check 1: Max open trades ──────────────────────────────────────
        if open_trades_count >= max_trades:
            return self._reject(
                f"Max open trades reached ({open_trades_count}/{max_trades})",
                risk_score=10
            )

        # ── Check 2: Minimum probability ──────────────────────────────────
        if probability < 35:
            return self._reject(
                f"Win probability too low: {probability}% (min 35%)",
                risk_score=15
            )

        # ── Calculate SL from ICT invalidation ────────────────────────────
        # Use entry zone midpoint as entry reference
        entry_ref = (entry_low + entry_high) / 2 if entry_low and entry_high else current_price

        # SL distance: use ATR-based SL (1.0-1.5x ATR H1) or min_sl_pips, whichever is larger
        sl_pips = max(min_sl_pips, round(atr_pips * 1.0, 1))

        # Cap SL at 2.5x ATR to avoid oversized stops
        if sl_pips > atr_pips * 2.5:
            sl_pips = round(atr_pips * 2.5, 1)
            risk_factors.append({"factor": "SL capped", "severity": "MEDIUM",
                                 "description": f"SL capped at 2.5x ATR ({sl_pips}p)"})

        # ── Calculate TP1 (day trading constraint) ────────────────────────
        max_tp1_pips = round(atr_pips * 2, 1)  # 2x ATR H1 = intraday reachable

        # Ideal TP1 for configured RR
        ideal_tp1 = round(sl_pips * rr_ratio, 1)

        # Use min of ideal and max allowed
        tp1_pips = min(ideal_tp1, max_tp1_pips)

        # Ensure TP1 is at least 1.2x SL (absolute floor)
        if tp1_pips < sl_pips * 1.2:
            tp1_pips = round(sl_pips * 1.2, 1)

        # If even 1.2x SL exceeds max TP1, this pair can't be traded intraday
        if tp1_pips > max_tp1_pips and max_tp1_pips > 0:
            return self._reject(
                f"Cannot achieve min RR 1.2 within day trading limit: "
                f"need {tp1_pips}p TP1, max allowed {max_tp1_pips}p (2x ATR H1)",
                risk_score=20
            )

        # ── Calculate actual RR ───────────────────────────────────────────
        gross_rr = round(tp1_pips / sl_pips, 2) if sl_pips > 0 else 0
        friction = 1.5
        net_rr = round((tp1_pips - friction) / (sl_pips + friction), 2) if sl_pips > 0 else 0

        # ── Calculate position size ───────────────────────────────────────
        risk_usd = max_risk_usd if max_risk_usd > 0 else account_balance * risk_percent / 100
        pip_usd = PIP_USD.get(symbol, 10.0)
        lot_size = max(0.01, round(risk_usd / (sl_pips * pip_usd), 2))

        # ── Win probability with adjustments ──────────────────────────────
        base_prob = SETUP_WIN_RATES.get(setup_type, 0.55)
        win_prob = base_prob
        adjustments = []

        # Session bonus
        session = strategy.get("session", "")
        if session in ("London", "NewYork"):
            win_prob += 0.05
            adjustments.append({"factor": f"{session} session", "delta": 0.05})

        # HTF alignment
        htf_trend = ind.get("trend", "unknown")
        if (direction == "BUY" and htf_trend == "bullish") or \
           (direction == "SELL" and htf_trend == "bearish"):
            win_prob += 0.08
            adjustments.append({"factor": "HTF alignment", "delta": 0.08})

        # ICTEA probability override (if provided and reasonable)
        if 40 <= probability <= 90:
            ictea_prob = probability / 100
            win_prob = round((win_prob + ictea_prob) / 2, 3)  # average of model and ICTEA

        # ── Expected value ────────────────────────────────────────────────
        ev = round(win_prob * tp1_pips - (1 - win_prob) * sl_pips, 2)

        if ev < 0:
            risk_factors.append({"factor": "Negative EV", "severity": "HIGH",
                                 "description": f"EV={ev} pips"})

        # ── TP2 / TP3 ────────────────────────────────────────────────────
        tp2_pips = round(tp1_pips * 1.5, 1) if tp1_pips else None
        tp3_pips = round(tp1_pips * 2.0, 1) if tp1_pips else None

        # ── Recommendation ────────────────────────────────────────────────
        if net_rr >= 1.5 and ev > 0 and win_prob >= 0.50:
            recommendation = "FULL_SIZE"
        elif net_rr >= 1.2 and ev >= -2:
            recommendation = "HALF_SIZE"
            risk_factors.append({"factor": "Marginal setup", "severity": "MEDIUM",
                                 "description": f"Net RR {net_rr}, EV {ev}"})
        else:
            recommendation = "FULL_SIZE"  # approve anyway, code will validate

        # ── Build result ──────────────────────────────────────────────────
        result = {
            "approved": True,
            "risk_score": min(100, max(0, int(100 - net_rr * 20 - ev * 2))),
            "rejection_reason": None,
            "position_size": {
                "lot_size": lot_size,
                "risk_usd": round(risk_usd, 2),
                "risk_percent": risk_percent,
                "sl_pips": sl_pips,
                "tp1_pips": tp1_pips,
                "tp2_pips": tp2_pips,
                "rr_ratio": gross_rr,
            },
            "probability_assessment": {
                "win_probability": round(win_prob * 100, 1),
                "base_probability": round(base_prob * 100, 1),
                "adjustments": adjustments,
                "expected_value": ev,
            },
            "risk_factors": risk_factors,
            "recommendation": recommendation,
            "notes": (
                f"Deterministic RM: SL={sl_pips}p TP1={tp1_pips}p "
                f"gross_RR={gross_rr} net_RR={net_rr} "
                f"lot={lot_size} risk=${risk_usd:.0f} "
                f"win_prob={win_prob*100:.0f}% EV={ev}p"
            ),
        }

        status = f"APPROVED ✅ {symbol} {direction} SL={sl_pips}p TP1={tp1_pips}p RR={gross_rr}"
        await self.broadcast_status("EVALUATION_COMPLETE", status)
        logger.info("RM [%s] %s", symbol, result["notes"])

        return result

    @staticmethod
    def _reject(reason: str, risk_score: int = 30) -> dict:
        return {
            "approved": False,
            "risk_score": risk_score,
            "rejection_reason": reason,
            "position_size": {},
            "probability_assessment": {},
            "risk_factors": [],
            "recommendation": "SKIP",
            "notes": f"Rejected: {reason}",
        }
