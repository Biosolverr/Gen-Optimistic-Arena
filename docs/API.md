# OptimisticArena — API Reference

## Core

### create_session

Creates session. Host = caller.

---

### join_session(session_id)

Join session.

---

### start_round(session_id, prompt="")

Starts round.

---

### submit(session_id, text)

Submit answer.

---

### submit_with_llm(session_id)

AI-generated answer.

---

### close_submissions(session_id)

Locks submissions + triggers scoring.

---

### vote(session_id, candidate_hex)

Vote for player.

Rules:
- no self vote
- one vote per player

---

### finalize_round(session_id)

Deterministic resolution:

60% votes + 40% AI


---

## Optimistic System

### optimistic_claim_winner()

Host claims winner.

---

### challenge_claim()

Oppose claim.

---

### finalize_claim()

Resolve claim (AI or fallback)

---

## AI Appeals

### appeal_ai_score()

- pays XP bond  
- AI re-evaluates  

---

## XP

### reward_player()

Manual XP reward.

---

## Views

- get_session  
- get_round_info  
- get_submission  
- get_xp  
- get_wins  
