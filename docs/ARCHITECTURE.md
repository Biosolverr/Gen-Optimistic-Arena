# OptimisticArena — Architecture

## Phases

Every session has a current phase stored on-chain.

| Value | Name | Description |
|---|---|---|
| `0` | LOBBY | Waiting for host to start a round |
| `1` | SUBMISSIONS | Players submit their answers |
| `2` | VOTING | Players vote for each other's submissions |

### Phase Flow

LOBBY
│
│  host calls start_round()
▼
SUBMISSIONS
│
│  host calls close_submissions()
▼
VOTING
│
├─── host calls finalize_round()  ──────────────────► LOBBY (winner set)
│
└─── host calls optimistic_claim_*()
│
│  challenge window open
│  (members may call challenge_claim)
│
│  host calls finalize_claim()
▼
LOBBY (winner set)

---

## Deterministic Finalize (60/40)

Used by `finalize_round()`.

Each valid submission receives two normalized scores:


votes_scaled = (votes / max_votes) * 1000
ai_scaled    = (ai_total / max_ai_total) * 1000
total = votes_scaled * 60 + ai_scaled * 40

Where `ai_total = clarity + creativity + relevance` (each 0–10).

Tie-break: smallest address hex string wins.

---

## Optimistic Claim

An alternative to `finalize_round`. The host claims a winner during VOTING phase.

**States of `round_finalized`:**

| Value | Meaning |
|---|---|
| `0` | Not finalized |
| `1` | Finalized (winner set) |
| `2` | Claim pending (challenge window open) |

**Rules:**
- Only one active claim per session at a time
- While a claim is active, no new round can be started
- Any member can challenge with an alternative winner during the window
- After the window closes, host calls `finalize_claim`

**Resolution modes stored in `round_resolution_mode`:**

| Value | Mode |
|---|---|
| `1` | Deterministic 60/40 (finalize_round) |
| `2` | Accepted host claim (no challenges) |
| `3` | LLM judge resolved dispute |
| `4` | Fallback to vote tally (LLM disabled) |

---

## AI-Score Appeals

After `close_submissions`, players may appeal their AI score within `appeal_period_sec`.

- Costs `appeal_bond_xp` XP
- LLM re-scores the submission
- New score higher → scores updated, player receives `appeal_bond_xp * 2` XP back
- New score equal or lower → bond is burned

---

## XP System

| Event | XP |
|---|---|
| Submit an answer | +1 |
| Win a round | +10 |
| Successful appeal | bond ×2 returned |
| Failed appeal | bond burned |
| Host bonus reward | variable (host discretion) |

XP is tracked per address across all sessions (`season_xp`).
Wins are tracked separately (`season_wins`).

---

## Storage Keys

All TreeMap keys are composite strings to namespace by session, round, and player:

| Pattern | Used for |
|---|---|
| `"{sid}:{idx}"` | Member address by index |
| `"{sid}:{addr}"` | Member index lookup |
| `"{sid}:{rnd}"` | Round-level data (prompt, scored flag, etc.) |
| `"{sid}:{rnd}:{addr}"` | Per-player per-round data (submission, scores, votes) |
| `"{sid}:{rnd}:{idx}"` | Challenge entries by index |
