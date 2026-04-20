# TradeWizard Self-Learning & Auto-Improvement Architecture

## Stato Attuale: Cosa Funziona e Cosa No

### Funziona
- I trade vengono registrati con outcome (WIN/LOSS/BE, pnl_usd, pnl_pips)
- Le meeting post-trade generano `setup_memory_updates` con failure/success patterns e lessons
- `strategy_memory.py` salva tutto nella tabella `StrategyMemory`
- `build_context_string()` formatta la memoria e la inietta nei prompt degli agenti

### NON Funziona (il loop e' rotto qui)
1. **RM ignora completamente la memoria** — usa win rate hard-coded (FVG=60%, OTE=65%, ecc.) invece dei dati reali dalla StrategyMemory
2. **ICTEA legge la memoria ma non la rispetta** — propone setup CAUTION/AVOID ugualmente
3. **Le lessons sono testo libero** — "evitare FVG prima di news" e' una stringa, non una regola eseguibile
4. **Nessun meccanismo di enforcement** — gli agenti possono ignorare tutto cio' che hanno "imparato"
5. **system_improvements vanno nel config DB come stringhe** — centinaia di chiavi non strutturate mai lette

### Esempio Concreto del Problema
```
Trade 1: FVG su EURUSD → LOSS (news spike)
Meeting: "FVG fallisce con news entro 15 min, aggiungere filtro"
→ Salvato in failure_patterns: ["news spike within 15 min before entry"]

Trade 2: Stesso segnale FVG su EURUSD, 10 min prima di news
→ ICTEA legge "CAUTION — 12 losses vs 8 wins su FVG"
→ Propone comunque il trade (la memoria e' informativa, non vincolante)
→ RM usa il 60% hard-coded, non il 40% reale
→ Nessun check: "c'e' news entro 15 min?"
→ Stessa perdita ripetuta
```

---

## Architettura Proposta: 4 Layer

```
┌─────────────────────────────────────────────────────────┐
│                    LAYER 4: GOVERNANCE                   │
│  Validazione regole, A/B testing, circuit breaker,      │
│  dashboard metriche learning                            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 LAYER 3: RULE ENGINE                     │
│  Tabella learning_rules, query per contesto,            │
│  inject regole strutturate nei prompt agenti            │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              LAYER 2: RULE EXTRACTION                    │
│  Meeting produce JSON strutturato → regole tipizzate    │
│  con condizioni, azioni, confidenza                     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│            LAYER 1: DATA COLLECTION (GIA' OK)            │
│  Trade outcomes, strategy_memory counters,              │
│  meeting conclusions                                    │
└─────────────────────────────────────────────────────────┘
```

---

## LAYER 1: Data Collection (gia' funzionante — piccoli miglioramenti)

### 1.1 Arricchire i dati di trade
Aggiungere alla tabella `trades` o ad una tabella collegata:

```python
# Nuove colonne su trades (o tabella trade_context)
market_context_at_entry = Column(JSON)  # {
#   "minutes_to_next_news": 45,
#   "news_impact": "high",
#   "session": "london",
#   "kill_zone_minutes_remaining": 30,
#   "spread_pips": 1.2,
#   "atr_h1": 0.0045,
#   "htf_trend": "bullish",
#   "daily_range_used_pct": 35,
#   "open_trades_at_entry": 0,
#   "day_of_week": "tuesday"
# }
```

**Perche':** Senza contesto di mercato al momento dell'entry, le meeting possono solo indovinare perche' un trade ha fallito. Con questi dati, il sistema puo' fare correlazioni reali.

### 1.2 RM deve usare win rate reali

```python
# risk_manager.py — CAMBIAMENTO CHIAVE
async def evaluate(self, symbol, strategy, market_data, system_config, 
                   open_trades_count=0, memory_context=""):
    setup_type = strategy.get("setup_type", "Unknown")
    
    # PRIMA: hard-coded
    # base_prob = SETUP_WIN_RATES.get(setup_type, 0.55)
    
    # DOPO: query dalla StrategyMemory, fallback al hard-coded
    from services.strategy_memory import get_win_rate
    actual_wr = await get_win_rate(setup_type, symbol)
    
    if actual_wr is not None and actual_wr["sample_size"] >= 10:
        base_prob = actual_wr["win_rate"] / 100  # es. 42% → 0.42
    else:
        base_prob = SETUP_WIN_RATES.get(setup_type, 0.55)  # fallback
```

**Impatto:** Con 10+ trade su un setup, il RM usa dati reali. Se FVG su EURUSD ha win rate 40%, il RM riduce la size o blocca il trade.

---

## LAYER 2: Rule Extraction (il cambiamento principale)

### 2.1 Nuova tabella `learning_rules`

```python
class LearningRule(Base):
    __tablename__ = "learning_rules"
    
    id             = Column(Integer, primary_key=True)
    
    # IDENTITA'
    rule_type      = Column(String(30), nullable=False)
    # Tipi: FILTER, BOOST, BLOCK, ADJUST_PARAM, CONTEXT_NOTE
    
    # SCOPE
    setup_type     = Column(String(50), nullable=True)   # NULL = tutti i setup
    symbol         = Column(String(20), nullable=True)    # NULL = tutti i symbol
    session        = Column(String(20), nullable=True)    # NULL = tutte le sessioni
    
    # CONDIZIONE (quando si applica)
    condition      = Column(JSON, nullable=False)
    # Esempi:
    # {"field": "minutes_to_next_news", "op": "<", "value": 30}
    # {"field": "daily_range_used_pct", "op": ">", "value": 70}
    # {"field": "htf_trend", "op": "!=", "value": "strategy.direction"}
    # {"and": [cond1, cond2]}  — composizione
    
    # AZIONE (cosa fare)
    action         = Column(JSON, nullable=False)
    # Esempi:
    # {"type": "BLOCK", "reason": "News troppo vicina"}
    # {"type": "REDUCE_SIZE", "factor": 0.5}
    # {"type": "REQUIRE_CONFIRMATION", "from": "htf_trend"}
    # {"type": "ADJUST_SL", "min_pips": 40}
    # {"type": "ADD_CONTEXT", "text": "FVG su EURUSD tende a fallire il lunedi"}
    
    # METADATA
    confidence     = Column(Float, default=0.5)          # 0-1, cresce con conferme
    sample_size    = Column(Integer, default=0)           # trade che supportano la regola
    source_type    = Column(String(20), nullable=False)   # MEETING, BACKTEST, MANUAL
    source_id      = Column(Integer, nullable=True)       # meeting_id o backtest_run_id
    
    # LIFECYCLE
    status         = Column(String(20), default="CANDIDATE")
    # CANDIDATE → ACTIVE → CONFIRMED → DEPRECATED
    created_at     = Column(DateTime, default=datetime.utcnow)
    activated_at   = Column(DateTime, nullable=True)
    confirmed_at   = Column(DateTime, nullable=True)
    deprecated_at  = Column(DateTime, nullable=True)
    
    # TRACKING
    times_applied  = Column(Integer, default=0)           # quante volte e' stata applicata
    times_correct  = Column(Integer, default=0)           # quante volte ha evitato una perdita
    times_wrong    = Column(Integer, default=0)           # quante volte ha bloccato un win
```

### 2.2 Meeting Output Strutturato

Il prompt del Journalist deve produrre regole JSON, non testo libero:

```json
{
  "conclusions": ["FVG su EURUSD ha perso 3 trade consecutivi durante news ad alto impatto"],
  "system_improvements": [],
  "setup_memory_updates": [...],
  
  "proposed_rules": [
    {
      "rule_type": "FILTER",
      "setup_type": "FVG",
      "symbol": "EURUSD",
      "condition": {
        "field": "minutes_to_next_news",
        "op": "<",
        "value": 30,
        "news_impact": "high"
      },
      "action": {
        "type": "BLOCK",
        "reason": "FVG su EURUSD fallisce con news high-impact entro 30 min (0/3 win rate)"
      },
      "confidence": 0.6,
      "sample_size": 3,
      "evidence": "Trade #45, #47, #51 — tutti loss con news < 30 min"
    },
    {
      "rule_type": "BOOST",
      "setup_type": "OTE",
      "symbol": null,
      "session": "london",
      "condition": {
        "field": "htf_trend",
        "op": "==",
        "value": "strategy.direction"
      },
      "action": {
        "type": "INCREASE_SIZE",
        "factor": 1.5
      },
      "confidence": 0.7,
      "sample_size": 8,
      "evidence": "OTE con HTF alignment in London: 7/8 wins"
    }
  ]
}
```

### 2.3 Tipi di Regola

| rule_type | Cosa fa | Esempio |
|-----------|---------|---------|
| **FILTER** | Blocca un trade se la condizione e' vera | "Non tradare FVG se news < 30 min" |
| **BOOST** | Aumenta size/confidenza se la condizione e' vera | "OTE + HTF aligned in London → +50% size" |
| **BLOCK** | Blocca completamente un setup/pair | "Non tradare OrderBlock su GBPJPY (0% win rate su 15 trade)" |
| **ADJUST_PARAM** | Modifica un parametro | "SL minimo 40 pips su GBPJPY (invece di 30)" |
| **CONTEXT_NOTE** | Aggiunge contesto al prompt dell'agente | "FVG su EURUSD tende a fallire il lunedi'" |

---

## LAYER 3: Rule Engine (il cuore del sistema)

### 3.1 Nuovo servizio: `rule_engine.py`

```python
# backend/services/rule_engine.py

class RuleEngine:
    """Motore che applica le learning_rules alle decisioni di trading."""
    
    async def evaluate_trade(self, setup_type, symbol, session, 
                              market_context: dict) -> RuleVerdict:
        """
        Chiamato dall'orchestrator PRIMA di inviare al RM.
        Restituisce: ALLOW, BLOCK, REDUCE_SIZE, o MODIFY con dettagli.
        """
        rules = await self._get_active_rules(setup_type, symbol, session)
        
        blocks = []
        adjustments = []
        context_notes = []
        size_factor = 1.0
        
        for rule in rules:
            if self._condition_matches(rule.condition, market_context):
                rule.times_applied += 1
                
                if rule.action["type"] == "BLOCK":
                    blocks.append(rule)
                elif rule.action["type"] == "REDUCE_SIZE":
                    size_factor *= rule.action["factor"]
                elif rule.action["type"] == "INCREASE_SIZE":
                    size_factor *= rule.action["factor"]
                elif rule.action["type"] == "ADJUST_SL":
                    adjustments.append(rule)
                elif rule.action["type"] == "ADD_CONTEXT":
                    context_notes.append(rule.action["text"])
        
        if blocks:
            return RuleVerdict(
                action="BLOCK",
                reasons=[b.action["reason"] for b in blocks],
                rules_applied=[b.id for b in blocks]
            )
        
        return RuleVerdict(
            action="ALLOW",
            size_factor=size_factor,
            adjustments=adjustments,
            context_notes=context_notes,
            rules_applied=[r.id for r in rules if self._condition_matches(r.condition, market_context)]
        )
    
    def _condition_matches(self, condition: dict, context: dict) -> bool:
        """Valuta una condizione contro il contesto di mercato."""
        if "and" in condition:
            return all(self._condition_matches(c, context) for c in condition["and"])
        if "or" in condition:
            return any(self._condition_matches(c, context) for c in condition["or"])
        
        field = condition["field"]
        op = condition["op"]
        expected = condition["value"]
        actual = context.get(field)
        
        if actual is None:
            return False
        
        # Risolvi riferimenti dinamici (es. "strategy.direction")
        if isinstance(expected, str) and expected.startswith("strategy."):
            expected = context.get(expected)
        
        ops = {"<": lt, ">": gt, "<=": le, ">=": ge, "==": eq, "!=": ne}
        return ops.get(op, lambda a, b: False)(actual, expected)
```

### 3.2 Integrazione nell'Orchestrator

```python
# orchestrator.py — _analyze_and_trade()

# PRIMA (attuale):
#   1. ICTEA.analyze()
#   2. RM.evaluate()
#   3. TR.generate_trade()
#   4. Execute

# DOPO (con rule engine):
#   1. ICTEA.analyze() — con context_notes dalle regole
#   2. ** RULE ENGINE ** — valuta pre-trade
#   3. Se BLOCK → skip (log il motivo)
#   4. RM.evaluate() — con win rate reali + size_factor
#   5. TR.generate_trade() — con adjustments (es. SL minimo)
#   6. Execute

async def _analyze_and_trade(self, symbol, market_data, config):
    memory_ctx = await _build_memory()
    market_context = self._build_market_context(symbol, market_data)
    
    # Pre-filter: regole BLOCK a livello di symbol
    pre_verdict = await self.rule_engine.evaluate_trade(
        setup_type=None, symbol=symbol, 
        session=self._current_session(), market_context=market_context
    )
    if pre_verdict.action == "BLOCK":
        logger.info(f"SKIP {symbol}: blocked by rules — {pre_verdict.reasons}")
        return
    
    # ICTEA con context notes
    extra_context = "\n".join(pre_verdict.context_notes) if pre_verdict.context_notes else ""
    ict_analysis = await self.ictea.analyze(
        symbol, market_data, config, 
        memory_context=memory_ctx + "\n" + extra_context
    )
    
    if not ict_analysis.get("strategies"):
        return
    
    strategy = self._pick_best_strategy(ict_analysis["strategies"])
    
    # Rule engine: valuta setup specifico
    verdict = await self.rule_engine.evaluate_trade(
        setup_type=strategy["setup_type"], symbol=symbol,
        session=self._current_session(), market_context=market_context
    )
    
    if verdict.action == "BLOCK":
        logger.info(f"SKIP {symbol}/{strategy['setup_type']}: {verdict.reasons}")
        # Log che la regola ha bloccato — per tracking
        await self._log_rule_block(symbol, strategy, verdict)
        return
    
    # RM con win rate reali e size factor
    rm_result = await self.rm.evaluate(
        symbol, strategy, market_data, config,
        open_trades_count=len(self.active_trades),
        memory_context=memory_ctx,
        size_factor=verdict.size_factor  # NUOVO parametro
    )
    
    # ... resto del flusso ...
```

### 3.3 Context Notes nell'ICTEA

Le regole di tipo `CONTEXT_NOTE` vengono iniettate nel prompt dell'ICTEA come sezione dedicata:

```
## LEARNED RULES (from past performance — MUST respect)

- FVG su EURUSD: win rate reale 40% (20 trade). Status: CAUTION.
  → REGOLA ATTIVA: Non proporre FVG se news high-impact < 30 min
  → REGOLA ATTIVA: FVG fallisce il lunedi su EURUSD (2/8 win rate)
  
- OTE con HTF alignment: win rate 78% (18 trade). Status: STRONG.
  → BOOST: size +50% quando HTF trend == direction in London session
```

**Differenza chiave:** Oggi la memoria e' "informativa". Con le regole, diventa una lista di vincoli che l'ICTEA DEVE rispettare (nel system prompt, non nel user message).

---

## LAYER 4: Governance

### 4.1 Lifecycle delle Regole

```
CANDIDATE ──→ ACTIVE ──→ CONFIRMED ──→ DEPRECATED
   │             │            │
   │             │            └─ Disattivata se win rate peggiora
   │             │               o se il mercato cambia
   │             │
   │             └─ Dopo 5+ applicazioni con >60% accuracy
   │
   └─ Creata dalla meeting, attivata automaticamente
      se confidence >= 0.5 E sample_size >= 5
      
      Se confidence < 0.5 o sample_size < 5:
      resta CANDIDATE fino a conferma da meeting successiva
```

### 4.2 Auto-Validazione Post-Trade

Dopo ogni trade, il sistema verifica le regole applicate:

```python
async def validate_rules_post_trade(self, trade, rules_applied_ids):
    """Dopo la chiusura del trade, aggiorna accuracy delle regole."""
    for rule_id in rules_applied_ids:
        rule = await get_rule(rule_id)
        
        if rule.action["type"] == "BLOCK":
            # La regola ha bloccato un trade. Era giusto?
            # Non possiamo saperlo direttamente, ma possiamo tracciare
            # i trade simili che SONO passati
            pass
        
        elif rule.action["type"] in ("REDUCE_SIZE", "INCREASE_SIZE"):
            if trade.result == "WIN" and rule.action["type"] == "INCREASE_SIZE":
                rule.times_correct += 1
            elif trade.result == "LOSS" and rule.action["type"] == "REDUCE_SIZE":
                rule.times_correct += 1
            else:
                rule.times_wrong += 1
        
        # Promuovi o depreca
        accuracy = rule.times_correct / max(rule.times_applied, 1)
        if rule.times_applied >= 5 and accuracy >= 0.6:
            rule.status = "CONFIRMED"
            rule.confirmed_at = datetime.utcnow()
        elif rule.times_applied >= 10 and accuracy < 0.4:
            rule.status = "DEPRECATED"
            rule.deprecated_at = datetime.utcnow()
```

### 4.3 Circuit Breaker

Protezione contro regole che peggiorano le performance:

```python
# Se nelle ultime 24h le regole hanno bloccato > 5 trade 
# e i trade simili (stesso setup/pair) che sono passati 
# hanno avuto win rate > 60%, la regola viene sospesa.

# Se il sistema ha 5+ loss consecutivi, 
# tutte le regole BOOST vengono temporaneamente disattivate.

# Se una regola BLOCK ha bloccato un trade e un trade identico
# (stesso setup, symbol, sessione) passa su un altro account
# e vince, la regola perde confidenza.
```

### 4.4 Dashboard Metriche (frontend)

Nuova sezione nella UI:

```
┌─ Learning Dashboard ─────────────────────────────┐
│                                                   │
│  Regole Attive: 12  |  Candidate: 5  |  Dep: 3  │
│                                                   │
│  Oggi:                                            │
│    Trade bloccati da regole: 4                    │
│    Trade passati: 8                               │
│    Regole applicate: 23 volte                     │
│    Accuracy media regole attive: 67%              │
│                                                   │
│  Top regole per impatto:                          │
│    1. BLOCK FVG + news < 30min → evitate 3 loss  │
│    2. BOOST OTE + HTF London → +450 USD           │
│    3. FILTER GBPJPY lunedi → evitato 1 loss      │
│                                                   │
│  Regole in osservazione (CANDIDATE):              │
│    - "OrderBlock fallisce se spread > 2 pips"     │
│      → 3/5 sample necessari per attivazione       │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## Piano di Implementazione (fasi)

### Fase 1: Foundation (piu' impatto con meno sforzo)
1. **RM usa win rate reali** — query StrategyMemory invece di hard-coded
2. **Tabella `learning_rules`** — migration DB
3. **`rule_engine.py`** — servizio base con evaluate_trade()
4. **Integrazione orchestrator** — rule engine nel flusso pre-trade
5. **Market context al trade** — salvare contesto di mercato all'entry

### Fase 2: Extraction
6. **Journalist prompt aggiornato** — output `proposed_rules` JSON strutturato
7. **Rule ingestion** — salva proposed_rules come CANDIDATE
8. **Auto-attivazione** — CANDIDATE → ACTIVE con soglie

### Fase 3: Feedback Loop
9. **Post-trade rule validation** — aggiorna accuracy regole dopo ogni trade
10. **Rule lifecycle** — promozione/deprecazione automatica
11. **ICTEA enforcement** — regole nel system prompt come vincoli

### Fase 4: Governance & UI
12. **Circuit breaker** — protezione contro regole dannose
13. **Dashboard learning** — metriche nel frontend
14. **API per regole manuali** — possibilita' di aggiungere regole a mano

---

## Stima Complessita'

| Fase | File Modificati | File Nuovi | Complessita' |
|------|----------------|------------|--------------|
| 1 | risk_manager.py, orchestrator.py, database.py, strategy_memory.py | rule_engine.py | Media |
| 2 | journalist.py, orchestrator.py | — | Media |
| 3 | orchestrator.py, rule_engine.py | — | Media-Alta |
| 4 | orchestrator.py, frontend components | learning_dashboard | Alta |

---

## Rischi e Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Regole troppo aggressive bloccano troppi trade | Circuit breaker + soglia minima sample_size=5 |
| Meeting genera regole sbagliate | Status CANDIDATE, servono conferme prima di ACTIVE |
| Overfitting su pochi trade | Confidence decay, sample_size minimo, expiry dopo 30 giorni senza conferma |
| Costo API sale (prompt piu' lunghi con regole) | Max 10 regole attive per prompt, le piu' rilevanti per scope |
| Regole contraddittorie | Priorita' per confidence, regole BLOCK vincono sempre su BOOST |
