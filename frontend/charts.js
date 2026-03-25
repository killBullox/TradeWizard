/* ============================================================
   charts.js — ICT Chart Rendering for TradeWizard
   Uses Lightweight Charts v4 (TradingView OSS library)
   ============================================================ */
'use strict';

// ── Constants ─────────────────────────────────────────────────────────────────
const CHART_COLORS = {
  bg:          '#0f1117',
  grid:        '#1e2130',
  text:        '#94a3b8',
  border:      '#2d3450',
  bullCandle:  '#10b981',
  bearCandle:  '#ef4444',
  wickBull:    '#10b981',
  wickBear:    '#ef4444',
  ema20:       '#f59e0b',
  ema50:       '#8b5cf6',
  fvgBull:     'rgba(16,185,129,0.15)',
  fvgBear:     'rgba(239,68,68,0.15)',
  fvgBullBdr:  'rgba(16,185,129,0.5)',
  fvgBearBdr:  'rgba(239,68,68,0.5)',
  obBull:      'rgba(59,130,246,0.15)',
  obBear:      'rgba(245,158,11,0.15)',
  obBullBdr:   'rgba(59,130,246,0.5)',
  obBearBdr:   'rgba(245,158,11,0.5)',
  pdh:         '#f59e0b',
  pdl:         '#f59e0b',
  pdc:         '#94a3b8',
  swingHigh:   '#10b981',
  swingLow:    '#ef4444',
  entry:       '#3b82f6',
  sl:          '#ef4444',
  tp:          '#10b981',
};

const TIMEFRAMES = ['M5','M15','M30','H1','H4','D1'];
const PAIRS      = ['EURUSD','GBPUSD','USDJPY','XAUUSD','USDCHF','AUDUSD','GBPJPY','NZDUSD','USDCAD','EURJPY'];

// ── Chart Manager ─────────────────────────────────────────────────────────────
class ICTChartManager {
  constructor(containerId) {
    this.containerId = containerId;
    this.chart       = null;
    this.candleSeries = null;
    this.ema20Series  = null;
    this.ema50Series  = null;
    this.overlays     = [];   // priceLine + rectangle series references
    this.currentSymbol = 'EURUSD';
    this.currentTf     = 'H1';
    this._resizeObs    = null;
  }

  // ── Initialise chart ────────────────────────────────────────────────────────
  init() {
    const container = document.getElementById(this.containerId);
    if (!container) return;
    if (typeof LightweightCharts === 'undefined') {
      container.innerHTML = '<div class="chart-error">⚠️ Chart library not loaded. Check internet connection.</div>';
      return;
    }

    this.chart = LightweightCharts.createChart(container, {
      layout: {
        background: { color: CHART_COLORS.bg },
        textColor:  CHART_COLORS.text,
      },
      grid: {
        vertLines:  { color: CHART_COLORS.grid },
        horzLines:  { color: CHART_COLORS.grid },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: CHART_COLORS.border,
      },
      timeScale: {
        borderColor:     CHART_COLORS.border,
        timeVisible:     true,
        secondsVisible:  false,
      },
      width:  container.clientWidth,
      height: container.clientHeight || 480,
    });

    // Candlestick series
    this.candleSeries = this.chart.addCandlestickSeries({
      upColor:       CHART_COLORS.bullCandle,
      downColor:     CHART_COLORS.bearCandle,
      borderUpColor:   CHART_COLORS.wickBull,
      borderDownColor: CHART_COLORS.wickBear,
      wickUpColor:   CHART_COLORS.wickBull,
      wickDownColor: CHART_COLORS.wickBear,
    });

    // EMA lines
    this.ema20Series = this.chart.addLineSeries({
      color:     CHART_COLORS.ema20,
      lineWidth: 1,
      title:     'EMA 20',
      priceLineVisible: false,
    });
    this.ema50Series = this.chart.addLineSeries({
      color:     CHART_COLORS.ema50,
      lineWidth: 1,
      title:     'EMA 50',
      priceLineVisible: false,
    });

    // Auto-resize
    this._resizeObs = new ResizeObserver(() => {
      if (this.chart && container.clientWidth > 0) {
        this.chart.applyOptions({ width: container.clientWidth });
      }
    });
    this._resizeObs.observe(container);
  }

  // ── Load data ───────────────────────────────────────────────────────────────
  async loadSymbol(symbol, timeframe) {
    this.currentSymbol = symbol || this.currentSymbol;
    this.currentTf     = timeframe || this.currentTf;
    updateChartStatus('loading', `Loading ${this.currentSymbol} ${this.currentTf}…`);

    try {
      const url  = `/api/chart-data/${this.currentSymbol}?timeframe=${this.currentTf}&bars=300`;
      const data = await _fetchJSON(url);
      this._render(data);
      updateChartStatus('ok', `${this.currentSymbol} ${this.currentTf} — ${data.candles?.length ?? 0} bars`);
    } catch (err) {
      updateChartStatus('error', `Failed to load: ${err.message}`);
      console.error('Chart load error', err);
    }
  }

  // ── Main render ─────────────────────────────────────────────────────────────
  _render(data) {
    if (!this.chart) return;
    const { candles = [], indicators = {}, active_trades = [] } = data;

    // 1. Candles
    const candleData = candles.map(c => ({
      time:  _toUnix(c.time),
      open:  c.open,
      high:  c.high,
      low:   c.low,
      close: c.close,
    })).filter(c => c.time > 0);

    this.candleSeries.setData(candleData);

    // 2. EMAs — computed client-side from close prices
    if (candleData.length >= 20) {
      this.ema20Series.setData(_computeEMA(candleData, 20));
      this.ema50Series.setData(_computeEMA(candleData, 50));
    }

    // 3. Remove old overlays
    this._clearOverlays();

    // 4. Key horizontal levels
    this._addHLine(indicators.pdh, 'PDH', CHART_COLORS.pdh, 'dashed');
    this._addHLine(indicators.pdl, 'PDL', CHART_COLORS.pdl, 'dashed');
    this._addHLine(indicators.pdc, 'PDC', CHART_COLORS.pdc, 'dotted');

    for (const sh of (indicators.swing_highs || [])) {
      this._addHLine(sh.price, 'SwH', CHART_COLORS.swingHigh, 'dotted');
    }
    for (const sl of (indicators.swing_lows || [])) {
      this._addHLine(sl.price, 'SwL', CHART_COLORS.swingLow, 'dotted');
    }

    // 5. FVG zones
    for (const fvg of (indicators.fvgs || [])) {
      this._addZone(
        fvg.bottom, fvg.top,
        fvg.type === 'bullish' ? CHART_COLORS.fvgBull : CHART_COLORS.fvgBear,
        fvg.type === 'bullish' ? CHART_COLORS.fvgBullBdr : CHART_COLORS.fvgBearBdr,
        `FVG ${fvg.type === 'bullish' ? '▲' : '▼'}`,
      );
    }

    // 6. Order Block zones
    for (const ob of (indicators.order_blocks || [])) {
      this._addZone(
        ob.bottom, ob.top,
        ob.type === 'bullish' ? CHART_COLORS.obBull : CHART_COLORS.obBear,
        ob.type === 'bullish' ? CHART_COLORS.obBullBdr : CHART_COLORS.obBearBdr,
        `OB ${ob.type === 'bullish' ? '▲' : '▼'}`,
      );
    }

    // 7. Active trade levels
    for (const t of active_trades) {
      this._addHLine(t.entry_price, `#${t.id} Entry`, CHART_COLORS.entry, 'solid');
      this._addHLine(t.stop_loss,   `#${t.id} SL`,    CHART_COLORS.sl,    'solid');
      if (t.take_profit_1) this._addHLine(t.take_profit_1, `#${t.id} TP1`, CHART_COLORS.tp, 'solid');
      if (t.take_profit_2) this._addHLine(t.take_profit_2, `#${t.id} TP2`, CHART_COLORS.tp, 'dotted');
      if (t.take_profit_3) this._addHLine(t.take_profit_3, `#${t.id} TP3`, CHART_COLORS.tp, 'dotted');
    }

    // 8. Fit all visible data
    this.chart.timeScale().fitContent();

    // 9. Update legend
    this._updateLegend(indicators, active_trades);
  }

  // ── Overlay helpers ─────────────────────────────────────────────────────────

  _addHLine(price, title, color, style) {
    if (!price || !this.candleSeries) return;
    const lineStyle = {
      'solid':  LightweightCharts.LineStyle.Solid,
      'dashed': LightweightCharts.LineStyle.Dashed,
      'dotted': LightweightCharts.LineStyle.Dotted,
    }[style] ?? LightweightCharts.LineStyle.Solid;

    const line = this.candleSeries.createPriceLine({
      price,
      color,
      lineWidth: 1,
      lineStyle,
      axisLabelVisible: true,
      title,
    });
    this.overlays.push({ type: 'priceLine', ref: line, series: this.candleSeries });
  }

  _addZone(bottom, top, fillColor, borderColor, label) {
    if (!bottom || !top || !this.chart) return;
    // Use a band via two line series (histogram hack gives better fills in v4)
    // Lightweight Charts v4 doesn't have native rectangle primitives in the base bundle,
    // so we simulate zones with a band series (area series capped at top/bottom).
    try {
      const band = this.chart.addLineSeries({
        color:           borderColor,
        lineWidth:       1,
        lineStyle:       LightweightCharts.LineStyle.Dashed,
        title:           label,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      // Just draw the midpoint line — cleaner than faking a band
      const mid = (bottom + top) / 2;
      // We store but don't actually set data (price line approach is cleaner)
      band.remove?.();  // remove immediately, use price lines instead
    } catch (_) {}

    // Draw top and bottom borders of the zone
    this._addHLine(top,    label + ' top', borderColor, 'dashed');
    this._addHLine(bottom, label + ' bot', borderColor, 'dashed');
  }

  _clearOverlays() {
    for (const ov of this.overlays) {
      try {
        if (ov.type === 'priceLine' && ov.series) {
          ov.series.removePriceLine(ov.ref);
        } else if (ov.type === 'series' && this.chart) {
          this.chart.removeSeries(ov.ref);
        }
      } catch (_) {}
    }
    this.overlays = [];
  }

  // ── Legend ──────────────────────────────────────────────────────────────────
  _updateLegend(indicators, trades) {
    const el = document.getElementById('chart-legend');
    if (!el) return;

    const trend = indicators.trend || '—';
    const tIcon = trend === 'bullish' ? '🟢' : '🔴';

    const fvgCount = (indicators.fvgs || []).length;
    const obCount  = (indicators.order_blocks || []).length;

    el.innerHTML = `
      <span class="legend-item" style="color:${CHART_COLORS.ema20}">● EMA20: ${_p(indicators.ema20)}</span>
      <span class="legend-item" style="color:${CHART_COLORS.ema50}">● EMA50: ${_p(indicators.ema50)}</span>
      <span class="legend-item">${tIcon} Trend: <b>${trend}</b></span>
      <span class="legend-item">ATR: ${_p(indicators.atr)} (${indicators.atr_pips ?? '—'}p)</span>
      <span class="legend-item" style="color:${CHART_COLORS.pdh}">PDH: ${_p(indicators.pdh)}</span>
      <span class="legend-item" style="color:${CHART_COLORS.pdl}">PDL: ${_p(indicators.pdl)}</span>
      <span class="legend-item" style="color:rgba(16,185,129,0.8)">FVG: ${fvgCount}</span>
      <span class="legend-item" style="color:rgba(59,130,246,0.8)">OB: ${obCount}</span>
      ${trades.length ? `<span class="legend-item" style="color:${CHART_COLORS.entry}">● ${trades.length} active trade(s)</span>` : ''}
    `;
  }

  // ── Cleanup ─────────────────────────────────────────────────────────────────
  destroy() {
    if (this._resizeObs) this._resizeObs.disconnect();
    if (this.chart)      this.chart.remove();
    this.chart = null;
  }
}

// ── Static helpers ────────────────────────────────────────────────────────────

function _toUnix(isoStr) {
  try {
    return Math.floor(new Date(isoStr).getTime() / 1000);
  } catch {
    return 0;
  }
}

function _computeEMA(candles, period) {
  if (candles.length < period) return [];
  const k = 2 / (period + 1);
  let ema  = candles.slice(0, period).reduce((s, c) => s + c.close, 0) / period;
  const result = [];
  for (let i = period - 1; i < candles.length; i++) {
    if (i === period - 1) {
      ema = candles[i].close;
    } else {
      ema = candles[i].close * k + ema * (1 - k);
    }
    result.push({ time: candles[i].time, value: ema });
  }
  return result;
}

function _p(val) {
  if (val == null) return '—';
  const n = parseFloat(val);
  return isNaN(n) ? '—' : n.toFixed(5);
}

async function _fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ── UI wiring ─────────────────────────────────────────────────────────────────
let chartManager = null;

function initCharts() {
  if (chartManager) return;
  chartManager = new ICTChartManager('chart-canvas');
  chartManager.init();

  const sym = document.getElementById('chart-symbol');
  const tf  = document.getElementById('chart-tf');
  const btn = document.getElementById('btn-chart-load');

  // Populate selectors
  if (sym) {
    sym.innerHTML = PAIRS.map(p =>
      `<option value="${p}" ${p === 'EURUSD' ? 'selected' : ''}>${p}</option>`
    ).join('');
  }
  if (tf) {
    tf.innerHTML = TIMEFRAMES.map(t =>
      `<option value="${t}" ${t === 'H1' ? 'selected' : ''}>${t}</option>`
    ).join('');
  }

  btn?.addEventListener('click', () => {
    const s = sym?.value || 'EURUSD';
    const t = tf?.value  || 'H1';
    chartManager.loadSymbol(s, t);
  });

  // Auto-load default
  chartManager.loadSymbol('EURUSD', 'H1');
}

function updateChartStatus(type, msg) {
  const el = document.getElementById('chart-status');
  if (!el) return;
  el.className = `chart-status chart-status-${type}`;
  el.textContent = msg;
}

// Called when the Charts tab is activated
window.activateChartsTab = function () {
  if (!chartManager) {
    // Small delay to ensure container is visible and has dimensions
    setTimeout(initCharts, 50);
  } else {
    // Trigger resize in case container size changed
    chartManager.chart?.applyOptions({
      width: document.getElementById('chart-canvas')?.clientWidth || 800,
    });
  }
};
