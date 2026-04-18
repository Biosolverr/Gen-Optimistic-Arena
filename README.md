# OptimisticArena

An on-chain competitive writing game built as a **GenLayer Intelligent Contract**.

Players compete by submitting creative answers, voting, and resolving rounds through a hybrid system of:

- Human voting  
- AI scoring  
- Deterministic resolution (60% votes / 40% AI)  
- Optional optimistic claims with challenge windows  

Built for **:contentReference[oaicite:0]{index=0}**

---

## Core Features

- Session-based multiplayer system  
- AI-generated or manual prompts  
- AI scoring (clarity / creativity / relevance)  
- Voting system  
- Optimistic claim → challenge → finalize flow  
- AI score appeals with XP bonding  
- XP + win tracking  

---

## Game Flow

LOBBY → SUBMISSIONS → VOTING → FINALIZED → LOBBY

---

## Quick Start

1. Deploy `contracts/optimistic_arena.py` in GenLayer Studio  
2. Call `create_session()`  
3. Players join via `join_session()`  
4. Start round via `start_round()`  
5. Submit answers  
6. Close submissions  
7. Vote  
8. Finalize round  

---

## Docs

- `docs/ARCHITECTURE.md`
- `docs/API.md`

---

## Tech Stack

- GenLayer Intelligent Contracts  
- Python  
- LLM-based scoring & moderation  
