# OptimisticArena — API Reference

## Write Methods

### Core Game

#### `create_session`
Creates a new game session. The caller becomes the host and is automatically added as a member.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_players` | int | — | Maximum number of players (min 2) |
| `challenge_period_sec` | int | `0` | Seconds to challenge an optimistic claim |
| `llm_prompts_enabled` | bool | `true` | Allow AI-generated round prompts |
| `llm_judge_enabled` | bool | `true` | Allow LLM judge to resolve disputes |
| `appeal_bond_xp` | int | `10` | XP bond required to appeal an AI score |
| `appeal_period_sec` | int | `60` | Seconds to appeal AI scores after close_submissions |

Returns: `session_id` (int)

---

#### `join_session(session_id)`
Join an existing session as a player. Host cannot call this (already a member).

---

#### `start_round(session_id, prompt="")`
Host starts a new round. Session must be in LOBBY phase with no active claim pending.

If `prompt` is empty, a default prompt is used: `"Round N: explain GenLayer in ONE sentence."`

Returns: `round_no` (int)

---

#### `submit(session_id, text)`
Submit a written answer for the current round. Each member may submit once.
Awards +1 XP on submission.

---

#### `submit_with_llm(session_id)`
Let the AI write your submission. Requires `llm_prompts_enabled = true`.
Awards +1 XP on submission.

---

#### `close_submissions(session_id)`
Host closes the submission phase. All submitted answers are validated and scored.
Session moves to VOTING phase.

> **Note:** In the current build, AI moderation is disabled. All submissions receive fixed scores of 7/7/7 (clarity/creativity/relevance) and are automatically marked valid.

---

#### `vote(session_id, candidate_hex)`
Vote for another player's submission. Rules:
- Must have submitted yourself
- Cannot vote for yourself
- One vote per player per round
- Candidate must have a valid submission

---

#### `finalize_round(session_id)`
Host finalizes the round using the deterministic 60/40 formula.
Awards winner +10 XP and +1 win.

See [ARCHITECTURE.md](ARCHITECTURE.md) for scoring details.

---

### AI-Score Appeals

#### `appeal_ai_score(session_id, round_no)`
Appeal your AI score. Requires paying `appeal_bond_xp`.
- If new score is higher → scores updated, bond returned ×2
- If new score is lower or equal → bond is burned

> Only available during the appeal window after `close_submissions`.

---

### Optimistic Claim

#### `optimistic_claim_winner(session_id, candidate_hex, reason="")`
Host claims a specific player as the winner. Opens a challenge window.

#### `optimistic_claim_by_votes(session_id)`
Host claims the player with the most votes as winner.

#### `optimistic_claim_by_llm(session_id)`
Host lets the LLM judge pick the winner. Requires `llm_judge_enabled = true`.

#### `challenge_claim(session_id, alternative_hex, reason)`
Any member can challenge the current claim within the challenge window, proposing an alternative winner.

#### `finalize_claim(session_id)`
Host finalizes the optimistic claim after the challenge window closes.
- No challenges → claimed winner wins
- Challenges present + LLM enabled → LLM picks from claimed + alternatives
- Challenges present + LLM disabled → fallback to on-chain vote tally

Awards winner +10 XP and +1 win.

---

### XP

#### `reward_player(session_id, round_no, player_hex, amount)`
Host manually awards bonus XP to a player who submitted in the given round.

#### `add_xp(player_hex, amount)`
Direct XP grant to any address. Can be called by anyone.

---

## View Methods

#### `get_session(session_id)`
Returns full session state: host, phase, member count, round number, flags, active claim.

#### `get_round_info(session_id, round_no)`
Returns round state: prompt, finalization status, claim info, challenge count, winner, resolution mode, LLM explanation.

#### `list_round_submissions(session_id, round_no)`
Returns all submissions for a round with scores, vote counts, and validity flags.

#### `get_round_prompt(session_id, round_no)`
Returns the prompt text for a given round.

#### `get_round_winner(session_id, round_no)`
Returns the final winner address hex, or null if not finalized.

#### `get_votes_for(session_id, round_no, candidate_hex)`
Returns vote count for a specific candidate in a given round.

#### `get_submission(session_id, round_no, player_hex)`
Returns the submission text for a specific player and round.

#### `get_member_at(session_id, index)`
Returns the hex address of the member at a given index.

#### `is_member(session_id, player_hex)`
Returns true if the address is a member of the session.

#### `get_xp(player_hex)`
Returns total XP for a player.

#### `get_my_xp()`
Returns XP for the caller.

#### `get_wins(player_hex)`
Returns total wins for a player.

#### `get_last_session_id()`
Returns the most recently created session ID.

#### `get_next_session_id()`
Returns the next session ID that will be assigned.
