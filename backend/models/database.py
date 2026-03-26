"""
Database models and session management for TradeWizard.
Uses SQLAlchemy with async SQLite.
"""

import json
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship


DATABASE_URL = "sqlite+aiosqlite:///./tradewizard.db"

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
    is_paper = Column(Boolean, default=False)     # True = paper trade
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
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class MarketSession(Base):
    __tablename__ = "market_sessions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    session_data = Column(Text, nullable=False)  # JSON OHLCV data
    analysis = Column(Text, nullable=True)        # ICT analysis
    created_at = Column(DateTime, default=datetime.utcnow)


def _migrate_backtest_runs(conn):
    """Add columns that may be missing from older DB versions."""
    from sqlalchemy import text as _text
    new_cols = [
        ("total_pnl_usd",    "FLOAT"),
        ("max_drawdown_usd", "FLOAT"),
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
        await conn.run_sync(_migrate_backtest_runs)

    # Insert default config values
    async with async_session_factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(SystemConfig).where(SystemConfig.key == "risk_percent"))
        if not result.scalar_one_or_none():
            defaults = [
                SystemConfig(key="risk_percent", value="1.0", description="Default risk per trade (%)"),
                SystemConfig(key="rr_ratio", value="2.0", description="Default risk/reward ratio"),
                SystemConfig(key="max_open_trades", value="3", description="Maximum concurrent open trades"),
                SystemConfig(key="account_balance", value="10000.0", description="Trading account balance"),
                SystemConfig(key="enabled_pairs", value='["EURUSD","GBPUSD","USDJPY","XAUUSD","USDCHF"]', description="Forex pairs to analyze"),
                SystemConfig(key="analysis_interval", value="3600", description="Analysis interval in seconds"),
                SystemConfig(key="ict_strategies", value='["FVG","OrderBlock","Liquidity","BOS","CHOCH","Mitigation","PD_Array"]', description="ICT strategies to use"),
                SystemConfig(key="system_performance", value='{"total_trades":0,"wins":0,"losses":0,"breakeven":0,"win_rate":0,"avg_rr":0}', description="System performance metrics"),
                SystemConfig(key="paper_mode",    value="false", description="Enable paper trading mode (virtual execution)"),
                SystemConfig(key="paper_balance", value="10000.0", description="Current paper trading account balance"),
                SystemConfig(key="news_block_minutes_before", value="30", description="Minutes before high-impact news to block trading"),
                SystemConfig(key="news_block_minutes_after",  value="30", description="Minutes after high-impact news to block trading"),
                SystemConfig(key="news_block_medium",         value="false", description="Also block Medium-impact events"),
            ]
            session.add_all(defaults)
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
