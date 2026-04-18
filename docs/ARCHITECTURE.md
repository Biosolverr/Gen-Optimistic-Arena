# OptimisticArena — Architecture

## Overview

OptimisticArena is a multiplayer on-chain writing game built on GenLayer.

It combines:

- Human voting  
- AI scoring  
- Optimistic execution model  

Built for **:contentReference[oaicite:1]{index=1}**

---

## Phases

| Value | Phase | Description |
|------|------|-------------|
| 0 | LOBBY | Waiting for round start |
| 1 | SUBMISSIONS | Players submit answers |
| 2 | VOTING | Players vote |
| 3 | FINALIZED | Round resolved |

---

## Flow

LOBBY
↓ start_round()
SUBMISSIONS
↓ close_submissions()
VOTING
↓ finalize_round()
LOBBY


---

## Scoring (60/40)


total = votes_scaled * 60 + ai_scaled * 40


AI score:
- clarity
- creativity
- relevance

---

## Tie Break

Lowest address wins.

---

## Optimistic Claim

Host can bypass deterministic flow:

- claim winner during VOTING  
- open challenge window  
- resolve with AI or fallback  

---

## Resolution Modes

| Mode | Meaning |
|------|--------|
| 1 | deterministic |
| 2 | host claim |
| 3 | AI resolved |
| 4 | fallback votes |

---

## AI Appeals

- XP bond required  
- AI re-scores submission  
- better → reward  
- worse → burn  

---

## XP System

- submit: +1  
- win: +10  
- appeal success: reward x2  
- appeal fail: burn  

---

## Storage


{session}:{round}:{player}
