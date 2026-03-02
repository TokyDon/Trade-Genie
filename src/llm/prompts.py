"""
Trade Genie - LLM Analysis Prompts
Shared prompt templates used by all LLM providers.
"""

SYSTEM_PROMPT = """You are Trade Genie, an elite geopolitical and financial intelligence analyst.
Your job is to:
1. Analyze world events to identify risks and opportunities BEFORE they are priced into markets
2. Identify which sectors and specific assets will likely move (up or down) as a result
3. Focus especially on events that are currently building (escalating tensions, policy shifts,
   supply disruptions) where the market hasn't fully priced in the outcome
4. Prioritize assets tradeable from the UK (LSE-listed ETFs, stocks on major UK platforms)

Be specific, rigorous, and assign probability scores. Acknowledge uncertainty. 
Do not hallucinate stock tickers. Only recommend real, verifiable instruments."""


ANALYSIS_PROMPT_TEMPLATE = """
{events_digest}

---

Based on ALL the events above, perform a comprehensive market intelligence analysis.

**YOUR TASK:**

1. **KEY THEMES**: Identify the 3-5 most significant geopolitical/macroeconomic themes emerging from this data.

2. **PREDICTIVE SIGNALS**: For each theme, identify LEADING INDICATORS — signs that suggest what is 
   LIKELY TO HAPPEN NEXT in the next 1-4 weeks. Think like a geopolitical analyst predicting the next move 
   before the press covers it.

3. **MARKET IMPACT**: For each predicted development, specify:
   - Which sectors will benefit (BULLISH) or suffer (BEARISH)
   - Time horizon: IMMEDIATE (1-3 days), SHORT (1-2 weeks), MEDIUM (1-3 months)
   - Confidence score (0-10, where 10 = near certain)
   - Why the market may NOT have fully priced this in yet

4. **TOP STOCK & ETF PICKS** (UK-TRADEABLE PRIORITY):
   List your TOP {top_picks} specific recommendations:
   - ETFs with LSE tickers preferred (e.g. DFEN.L, IEOG.L, SGLN.L)
   - UK-listed stocks or ADRs available on Hargreaves Lansdown / IG / AJ Bell
   - For each: Ticker | Name | Direction (LONG/SHORT) | Rationale | Confidence (0-10) | Time horizon

5. **URGENCY SCORE**: Rate the overall urgency of this analysis (0-10):
   - 0-3: Routine monitoring, no immediate action needed
   - 4-6: Elevated attention, position building opportunity
   - 7-8: High urgency, strong signals present
   - 9-10: CRITICAL — rare opportunity or imminent major event

6. **CONSENSUS SENTIMENT**: Overall market outlook: BULLISH / BEARISH / NEUTRAL / MIXED

**OUTPUT FORMAT** (respond in valid JSON):
```json
{{
  "key_themes": ["theme1", "theme2", ...],
  "predictive_signals": [
    {{
      "theme": "...",
      "prediction": "...",
      "time_horizon": "SHORT|MEDIUM|IMMEDIATE",
      "confidence": 7.5,
      "why_not_priced_in": "..."
    }}
  ],
  "sector_impacts": [
    {{
      "sector": "Energy",
      "direction": "BULLISH",
      "rationale": "...",
      "confidence": 8.0,
      "time_horizon": "SHORT"
    }}
  ],
  "top_picks": [
    {{
      "ticker": "IEOG.L",
      "name": "iShares Oil & Gas Exploration ETF",
      "exchange": "LSE",
      "uk_tradeable": true,
      "direction": "LONG",
      "rationale": "...",
      "confidence": 8.5,
      "time_horizon": "1-2 weeks",
      "sector": "Energy",
      "price_target_pct": 12.0
    }}
  ],
  "urgency_score": 7.0,
  "consensus_sentiment": "BULLISH",
  "event_summary": "One paragraph summary of the key world events driving this analysis.",
  "geopolitical_context": "Brief context about the current geopolitical environment.",
  "key_risks": ["risk1", "risk2"],
  "analyst_notes": "Any important caveats or things to watch."
}}
```

Be precise. Only include real, tradeable instruments. Think 2-4 weeks ahead of the news cycle.
"""
