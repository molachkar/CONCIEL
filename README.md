# 🟡 GOLD MACRO INTELLIGENCE PIPELINE  
## 🧠 Multi-Agent, Multi-Model Decision System for Gold (XAU)

---

## 🔥 SYSTEM PURPOSE

This project is a **full-stack macro + market intelligence pipeline** built to **analyze, structure, validate, and trade gold** using **multiple AI models**, each specialized in a single cognitive task.

It is **not** a single-model bot.  
It is a **layered decision architecture** designed to mimic **institutional research + trading desks**.

---

## 🧩 HIGH-LEVEL CONCEPT

> **Raw macro & market data → Structured macro regime →  
> Multi-model intelligence council → Consensus trade decision**

The system separates:
- **Data collection**
- **Interpretation**
- **Validation**
- **Execution**

No model is allowed to do everything.

---

## 🗂️ CORE COMPONENTS

### 🟦 1. DATA_BOT (Runs Daily)

Responsible for **building the macro state of the world**.

#### 📥 Raw Inputs (35–40 Day Window)
- Economic calendar events
- Inflation data (monthly + daily)
- Market data (XAU, DXY, VIX, SPX)
- News headlines (macro-relevant)
- Social sentiment (Reddit clusters)

#### 🤖 Specialized Agents (Single-Task)
Each agent produces **one clean JSON**:
- Economic context
- Inflation pressure
- Market structure
- News risk
- Social positioning

#### 🧠 Aggregator
- Synthesizes all agents into:
  - `macro_structured.json` → **FOR MODELS**
  - `gold_regime.md` → **FOR HUMANS (optional)**

This file is the **ground truth macro snapshot**.

---

## 🧠 2. COUNCIL_BOT (On Demand)

Consumes the structured macro file and **makes a trade decision** through **multiple rounds**.

---

## 🧪 ROUND 0 — INTELLIGENCE LAYER

**9 models, 9 independent tasks**

| Model | Role |
|-----|-----|
| Qwen-235B | Regime probability |
| Gemini-2.5 | Technical pattern |
| Llama-3.3-70B | Volume & momentum |
| DeepSeek-V3.1 | Macro force weighting |
| Meta-Llama-3.3 | Support / resistance |
| Terminus | Risk identification |
| gpt-oss-120B | Correlation (DXY / Gold) |
| DeepSeek-V3-0324 | Trend strength |
| Llama-Swallow | Sentiment & positioning |

All models receive **the same macro inputs**.

Output: **Structured intelligence, not opinions**.

---

## 🗳️ ROUND 1 — DIRECTION VOTING

All 9 models vote:
- **BUY**
- **SELL**
- **NO_TRADE**

Votes are weighted by:
- Model role
- Confidence
- Regime alignment

Output: **Directional consensus**.

---

## 🎯 ROUND 2 — LEVEL GENERATION

- 7+ models propose:
  - Entry
  - Stop Loss
  - Take Profit
- A **Devil’s Advocate** model actively tries to invalidate the trade.

Output: **Refined, stress-tested levels**.

---

## ⚖️ ROUND 3 — EXECUTION VALIDATION

Final checks:
- Risk / reward
- Position sizing
- Regime consistency
- Invalidation logic

Output:
- `trade_plan.txt`
- `meeting_log.json` (full traceability)

---

## 🗃️ OUTPUT ARTIFACTS

### 📄 Machine-Readable
- `macro_structured.json`
- Round outputs (JSON)
- Full meeting logs

### 🧾 Human-Readable
- `gold_regime.md`
- `trade_plan.txt`

---

## 🧠 DESIGN PHILOSOPHY

- ❌ No single-model dominance  
- ❌ No black-box decisions  
- ❌ No narrative hallucination  

- ✅ Specialization over generalization  
- ✅ Consensus over confidence  
- ✅ Structure over intuition  

Gold is treated as a **macro-driven asset**, not a chart toy.

---

## 🧭 FINAL NOTE

This system is built to:
- Detect **regime shifts**
- Exploit **macro asymmetry**
- Prevent **single-model failure**

It is **research-grade**, **decision-grade**, and **institution-inspired**.

---
