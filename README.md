# OptimisticArena

An on-chain writing game built as a GenLayer Intelligent Contract.

Players compete each round by submitting creative written answers to a prompt.
Winners are determined by a combination of human votes and AI scoring.
Disputes are resolved through an optimistic claim and challenge system.

## Features

- Sessions with multiple rounds
- Manual or AI-generated round prompts
- AI moderation and scoring (clarity / creativity / relevance)
- Human voting
- Deterministic finalization: 60% votes / 40% AI scores
- Optimistic claim → challenge → finalize flow
- AI-score appeals with XP bond
- On-chain XP and win tracking

## Repository Structure

contracts/
optimistic_arena.py     # GenLayer Intelligent Contract
docs/
API.md                  # All public methods with parameters and descriptions
ARCHITECTURE.md         # Phase flow, scoring formula, resolution modes
README.md
.gitignore

## Quick Start

1. Deploy `contracts/optimistic_arena.py` in [GenLayer Studio](https://studio.genlayer.com)
2. Call `create_session` from the host wallet
3. Have other players call `join_session`
4. Host calls `start_round` with a prompt
5. All players call `submit`
6. Host calls `close_submissions`
7. All players call `vote`
8. Host calls `finalize_round`

See [docs/API.md](docs/API.md) for full method reference.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for phase flow and scoring details.

## Phase Overview

| Phase | Value | Description |
|---|---|---|
| LOBBY | 0 | Waiting to start a round |
| SUBMISSIONS | 1 | Players submitting answers |
| VOTING | 2 | Players voting for submissions |

## Tech Stack

- [GenLayer](https://genlayer.com) — Intelligent Contract platform
- Python — Contract language
- LLM consensus — Used for AI scoring, submission generation, and dispute resolution
