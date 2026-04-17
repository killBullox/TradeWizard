"""
Database models and session management for TradeWizard.
Uses SQLAlchemy with async SQLite.
"""

import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship


import os as _os

# SYSTEM_MODE selects DB and behavior. Default "production" (real MT5, fase 1 only).
# "lab" uses a separate DB, paper-mode, and activates all 4 phases.
SYSTEM_MODE = _os.getenv("SYSTEM_MODE", "production").lower()
_DB_NAME = "tradewizard_lab.db" if SYSTEM_MODE == "lab" else "tradewizard.db"
DATABASE_URL = f"sqlite+aiosqlite:///./{_DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY / SELL
    status = Column(String(20), default="PROPOSED")  # PROPOSED, APPROVED, ACTIVE, CLOSED, CANCELLED
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    lot_size = Column(Float)
    risk_percent = Column(Float)
    rr_ratio = Column(Float)
    ict_setup = Column(String(100))   # e.g. "FVG+OB", "Liquidity Sweep"
    ict_context = Column(Text)        # Full ICT analysis
    risk_analysis = Column(Text)      # Risk manager output
    analyst_verdict = Column(Text)    # Trade analyst verdict
    mt5_ticket = Column(String(50), nullable=True)
    open_time = Column(DateTime, default=datetime.utcnow)
    close_time = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    pnl_pips = Column(Float, nullable=True)
    pnl_usd = Column(Float, nullable=True)
    result = Column(String(20), nullable=True)  # WIN / LOSS / BREAKEVEN
    trailing_sl_updates = Column(Integer, default=0)
    tp_hits = Column(Integer, default=0)
    close_notes = Column(Text, nullable=True)        # audit trail: why/how trade was closed
    is_paper = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    market_context = Column(Text, nullable=True)     # JSON: market snapshot at entry
    rules_applied = Column(Text, nullable=True)      # JSON: learning_rules IDs that matched
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("AgentLog", back_populates="trade")
    journal_entries = relationship("JournalEntry", back_populates="trade")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    agent_name = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="logs")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    entry_type = Column(String(50))  # TRADE_OPEN, TRADE_UPDATE, TRADE_CLOSE, MEETING_NOTE
    content = Column(Text, nullable=False)
    metrics = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    trade = relationship("Trade", back_populates="journal_entries")
    meeting = relationship("Meeting", back_populates="journal_entries")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    meeting_type = Column(String(50))  # POST_TRADE, WEEKLY_REVIEW, STRATEGY_REVIEW
    trigger = Column(String(100))      # what triggered the meeting
    participants = Column(String(200)) # comma-separated agent names
    agenda = Column(Text)
    summary = Column(Text, nullable=True)
    conclusions = Column(Text, nullable=True)    # JSON list of conclusions
    improvements = Column(Text, nullable=True)   # JSON list of system improvements
    status = Column(String(20), default="SCHEDULED")  # SCHEDULED, IN_PROGRESS, COMPLETED
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    journal_entries = relationship("JournalEntry", back_populates="meeting")


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String(200), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StrategyMemory(Base):
    """Persistent per-setup learning memory — updated after every trade and every meeting."""
    __tablename__ = "strategy_memory"
    __table_args__ = (UniqueConstraint("setup_type", "symbol", name="uq_setup_symbol"),)

    id           = Column(Integer, primary_key=True)
    setup_type   = Column(String(50), nullable=False)   # "FVG", "OrderBlock", etc.
    symbol       = Column(String(20), nullable=True)    # NULL = all symbols combined
    win_count    = Column(Integer, default=0)
    loss_count   = Column(Integer, default=0)
    total_pnl_usd = Column(Float, default=0.0)
    failure_patterns = Column(Text, default="[]")       # JSON list[str]
    success_patterns = Column(Text, default="[]")       # JSON list[str]
    lessons      = Column(Text, default="[]")           # JSON list[str]
    strategy_notes = Column(Text, default="")           # Free-form guidance from JR
    last_updated = Column(DateTime, default=datetime.utcnow)


class LearningRule(Base):
    """Structured trading rules extracted from meeting insights.
    Rules go through lifecycle: CANDIDATE → ACTIVE → CONFIRMED → DEPRECATED.
    Evaluated by the rule engine before every trade."""
    __tablename__ = "learning_rules"

    id           = Column(Integer, primary_key=True)

    # Identity
    rule_type    = Column(String(30), nullable=False)
    # Types: FILTER, BOOST, BLOCK, ADJUST_PARAM, CONTEXT_NOTE

    # Scope — NULL means "applies to all"
    setup_type   = Column(String(50), nullable=True)
    symbol       = Column(String(20), nullable=True)
    session      = Column(String(20), nullable=True)

    # Condition (JSON): when does the rule apply
    condition    = Column(Text, nullable=False, default="{}")

    # Action (JSON): what does the rule do
    action       = Column(Text, nullable=False, default="{}")

    # Metadata
    confidence   = Column(Float, default=0.5)
    sample_size  = Column(Integer, default=0)
    source_type  = Column(String(20), nullable=False, default="MEETING")
    # Sources: MEETING, BACKTEST, MANUAL
    source_id    = Column(Integer, nullable=True)
    description  = Column(Text, nullable=True)

    # Lifecycle
    status       = Column(String(20), default="CANDIDATE")
    # Status: CANDIDATE, ACTIVE, CONFIRMED, DEPRECATED
    created_at   = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    deprecated_at = Column(DateTime, nullable=True)

    # Effectiveness tracking
    times_applied = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    times_wrong   = Column(Integer, default=0)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(20), nullable=False)
    timeframe   = Column(String(10), nullable=False)
    strategy    = Column(String(100), nullable=False)  # FVG, OrderBlock, Mixed
    bars        = Column(Integer, default=500)
    risk_percent = Column(Float, default=1.0)
    rr_ratio    = Column(Float, default=2.0)
    status      = Column(String(20), default="RUNNING")  # RUNNING, DONE, FAILED
    # Results (populated when DONE)
    total_trades = Column(Integer, nullable=True)
    wins         = Column(Integer, nullable=True)
    losses       = Column(Integer, nullable=True)
    win_rate     = Column(Float,   nullable=True)
    total_pips   = Column(Float,   nullable=True)
    total_return     = Column(Float, nullable=True)   # % return
    total_pnl_usd    = Column(Float, nullable=True)   # $ profit/loss
    max_drawdown     = Column(Float, nullable=True)   # % drawdown
    max_drawdown_usd = Column(Float, nullable=True)   # $ drawdown
    profit_factor = Column(Float,  nullable=True)
    avg_rr       = Column(Float,   nullable=True)
    sharpe       = Column(Float,   nullable=True)
    trades_json  = Column(Text,    nullable=True)   # JSON list of sim trades
    equity_json  = Column(Text,    nullable=True)   # JSON equity curve
    error        = Column(Text,    nullable=True)
    data_warning = Column(Text,    nullable=True)   # set when M1 data unavailable
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class MT5Account(Base):
    """Stored MT5 broker accounts. One can be active at a time."""
    __tablename__ = "mt5_accounts"

    id         = Column(Integer, primary_key=True, index=True)
    label      = Column(String(100), nullable=False)          # user-defined name
    login      = Column(String(50),  nullable=False)          # MT5 account number
    password   = Column(String(200), nullable=False, default="")
    server     = Column(String(100), nullable=False)          # broker server
    account_type = Column(String(10), default="demo")         # "demo" | "real"
    is_active  = Column(Boolean, default=False)
    balance    = Column(Float, nullable=True)                  # last fetched balance
    created_at = Column(DateTime, default=datetime.utcnow)


class OhlcvBar(Base):
    """Local cache of OHLCV bars to avoid repeated API calls during backtesting."""
    __tablename__ = "ohlcv_bars"

    id        = Column(Integer, primary_key=True, index=True)
    symbol    = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    time      = Column(String(30), nullable=False)   # ISO datetime string
    open      = Column(Float,    nullable=False)
    high      = Column(Float,    nullable=False)
    low       = Column(Float,    nullable=False)
    close     = Column(Float,    nullable=False)
    volume    = Column(Integer,  default=0)

    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'time', name='uq_ohlcv_bar'),
        Index('ix_ohlcv_sym_tf_time', 'symbol', 'timeframe', 'time'),
    )


class MarketSession(Base):
    __tablename__ = "market_sessions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    session_data = Column(Text, nullable=False)  # JSON OHLCV data
    analysis = Column(Text, nullable=True)        # ICT analysis
    created_at = Column(DateTime, default=datetime.utcnow)


def _migrate_trades(conn):
    """Add columns to trades table that may be missing from older DB versions."""
    from sqlalchemy import text as _text
    new_cols = [
        ("trailing_sl_updates", "INTEGER DEFAULT 0"),
        ("tp_hits",             "INTEGER DEFAULT 0"),
        ("close_notes",         "TEXT"),
        ("is_paper",            "BOOLEAN DEFAULT 0"),
        ("archived",            "BOOLEAN DEFAULT 0"),
        ("market_context",      "TEXT"),   # JSON: session, news distance, spread, htf_trend, etc.
        ("rules_applied",       "TEXT"),   # JSON list[int]: learning_rules IDs that matched
    ]
    cur = conn.execute(_text("PRAGMA table_info(trades)"))
    existing = {row[1] for row in cur.fetchall()}
    for col_name, col_type in new_cols:
        if col_name not in existing:
            conn.execute(_text(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}"))


def _migrate_backtest_runs(conn):
    """Add columns that may be missing from older DB versions."""
    from sqlalchemy import text as _text
    new_cols = [
        ("total_pnl_usd",    "FLOAT"),
        ("max_drawdown_usd", "FLOAT"),
        ("data_warning",     "TEXT"),
    ]
    cur = conn.execute(_text("PRAGMA table_info(backtest_runs)"))
    existing = {row[1] for row in cur.fetchall()}
    for col_name, col_type in new_cols:
        if col_name not in existing:
            conn.execute(_text(f"ALTER TABLE backtest_runs ADD COLUMN {col_name} {col_type}"))


async def init_db():
    """Initialize the database, creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_trades)
        await conn.run_sync(_migrate_backtest_runs)

    # Insert default config values (only on first run — risk_percent absent means fresh DB)
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == "risk_percent"))
        if not result.scalar_one_or_none():
            # Check if user saved custom defaults previously
            ud_row = await session.execute(select(SystemConfig).where(SystemConfig.key == "_user_defaults"))
            ud = ud_row.scalar_one_or_none()
            if ud:
                import json as _json
                saved = _json.loads(ud.value)
                defaults = [SystemConfig(key=k, value=v) for k, v in saved.items() if k != "_user_defaults"]
            else:
                paper_default = "true" if SYSTEM_MODE == "lab" else "true"  # both default to paper; production can be flipped
                defaults = [
                    SystemConfig(key="risk_percent",    value="0.5",   description="Default risk per trade (%)"),
                    SystemConfig(key="rr_ratio",        value="2.0",   description="Default risk/reward ratio"),
                    SystemConfig(key="max_open_trades", value="1",     description="Maximum concurrent open trades"),
                    SystemConfig(key="account_balance", value="5000.0",description="Trading account balance"),
                    SystemConfig(key="max_risk_usd",    value="250",   description="Max loss per trade in USD (0 = use risk_percent)"),
                    SystemConfig(key="enabled_pairs",   value='["EURUSD","GBPUSD","AUDUSD","NZDUSD","XAUUSD"]', description="Forex pairs to analyze"),
                    SystemConfig(key="analysis_interval",value="900",  description="Analysis interval in seconds"),
                    SystemConfig(key="kill_zones",      value='[{"start":"05:00","end":"19:00"}]', description="Kill zone windows (Rome time)"),
                    SystemConfig(key="ict_strategies",  value='["FVG","OrderBlock","Liquidity","BOS","CHOCH","Mitigation","PD_Array"]', description="ICT strategies to use"),
                    SystemConfig(key="system_performance", value='{"total_trades":0,"wins":0,"losses":0,"breakeven":0,"win_rate":0,"avg_rr":0}', description="System performance metrics"),
                    SystemConfig(key="paper_mode",      value=paper_default, description="Enable paper trading mode (virtual execution)"),
                    SystemConfig(key="paper_balance",   value="5000.0",description="Current paper trading account balance"),
                    SystemConfig(key="news_block_minutes_before", value="30",    description="Minutes before high-impact news to block trading"),
                    SystemConfig(key="news_block_minutes_after",  value="30",    description="Minutes after high-impact news to block trading"),
                    SystemConfig(key="news_block_medium",         value="false", description="Also block Medium-impact events"),
                    SystemConfig(key="model_mode",      value="economy", description="AI model mode: economy (Haiku) or quality (Sonnet)"),
                    SystemConfig(key="min_sl_pips",     value="30",      description="Minimum SL distance in pips (anti-scalping)"),
                ]
            session.add_all(defaults)
            await session.commit()
        else:
            # Ensure max_risk_usd exists and is non-zero on older DBs
            mr = await session.execute(select(SystemConfig).where(SystemConfig.key == "max_risk_usd"))
            row = mr.scalar_one_or_none()
            if not row:
                session.add(SystemConfig(key="max_risk_usd", value="250", description="Max loss per trade in USD (0 = use risk_percent)"))
                await session.commit()
            elif not row.value or float(row.value or 0) == 0:
                row.value = "250"
                await session.commit()
            # Ensure MT5 credential keys exist (added in later version)
            for key, desc in [
                ("mt5_login",    "MT5 account number (login)"),
                ("mt5_password", "MT5 account password"),
                ("mt5_server",   "MT5 broker server name (e.g. ICMarkets-Demo)"),
            ]:
                res = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
                if not res.scalar_one_or_none():
                    session.add(SystemConfig(key=key, value="", description=desc))
            # Ensure min_sl_pips exists on older DBs
            msl = await session.execute(select(SystemConfig).where(SystemConfig.key == "min_sl_pips"))
            if not msl.scalar_one_or_none():
                session.add(SystemConfig(key="min_sl_pips", value="30", description="Minimum SL distance in pips (anti-scalping)"))
            await session.commit()


async def get_config(key: str, session: AsyncSession) -> Optional[str]:
    from sqlalchemy import select
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_config(key: str, value: str, session: AsyncSession):
    from sqlalchemy import select
    result = await session.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        session.add(SystemConfig(key=key, value=value))
    await session.commit()
