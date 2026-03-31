# v0.1.0
# { "Depends": "py-genlayer:latest" }
from genlayer import *
import typing
import time
import json


class OptimisticArena(gl.Contract):
    # -------------------------
    # persisted storage
    # -------------------------
    next_session_id: u256
    last_session_id: u256

    session_host: TreeMap[u256, Address]
    session_max_players: TreeMap[u256, u256]
    session_member_count: TreeMap[u256, u256]
    session_round_no: TreeMap[u256, u256]
    session_phase: TreeMap[u256, u256]

    session_challenge_period_sec: TreeMap[u256, u256]
    session_llm_prompts_enabled: TreeMap[u256, u256]
    session_llm_judge_enabled: TreeMap[u256, u256]
    session_appeal_bond_xp: TreeMap[u256, u256]
    session_appeal_period_sec: TreeMap[u256, u256]

    session_active_claim_round: TreeMap[u256, u256]

    session_member_at: TreeMap[str, Address]
    session_member_index: TreeMap[str, u256]

    round_prompt: TreeMap[str, str]

    round_submission: TreeMap[str, str]
    round_has_submitted: TreeMap[str, u256]
    round_submission_valid: TreeMap[str, u256]

    round_score_clarity: TreeMap[str, u256]
    round_score_creativity: TreeMap[str, u256]
    round_score_relevance: TreeMap[str, u256]

    round_vote_of: TreeMap[str, str]
    round_votes_for: TreeMap[str, u256]

    round_scored: TreeMap[str, u256]
    round_appeal_deadline: TreeMap[str, u256]
    submission_appealed: TreeMap[str, u256]

    round_finalized: TreeMap[str, u256]

    round_claimed_winner: TreeMap[str, Address]
    round_claim_reason: TreeMap[str, str]
    round_claim_deadline: TreeMap[str, u256]
    round_challenge_count: TreeMap[str, u256]

    round_challenge_who: TreeMap[str, Address]
    round_challenge_alt: TreeMap[str, Address]
    round_challenge_reason: TreeMap[str, str]
    round_challenged_by: TreeMap[str, u256]

    round_final_winner: TreeMap[str, Address]
    round_resolution_mode: TreeMap[str, u256]
    round_llm_explanation: TreeMap[str, str]

    season_xp: TreeMap[Address, u256]
    season_wins: TreeMap[Address, u256]

    # -------------------------
    # constants / helpers
    # -------------------------
    def _PHASE_LOBBY(self) -> u256: return u256(0)
    def _PHASE_SUBMISSIONS(self) -> u256: return u256(1)
    def _PHASE_VOTING(self) -> u256: return u256(2)

    def _now(self) -> u256:
        return u256(int(time.time()))

    def _sid(self, session_id: int) -> u256:
        if session_id <= 0:
            raise UserError("session_id must be > 0")
        return u256(session_id)

    def _rk(self, sid: u256, rnd: u256) -> str:
        return f"{int(sid)}:{int(rnd)}"

    def _mkey(self, sid: u256, addr: Address) -> str:
        return f"{int(sid)}:{addr.as_hex}"

    def _mkey_idx(self, sid: u256, idx: int) -> str:
        return f"{int(sid)}:{idx}"

    def _skey(self, sid: u256, rnd: u256, addr: Address) -> str:
        return f"{int(sid)}:{int(rnd)}:{addr.as_hex}"

    def _voter_key(self, sid: u256, rnd: u256, voter: Address) -> str:
        return f"{int(sid)}:{int(rnd)}:{voter.as_hex}"

    def _cand_key(self, sid: u256, rnd: u256, cand_hex: str) -> str:
        return f"{int(sid)}:{int(rnd)}:{cand_hex}"

    def _chk_key(self, sid: u256, rnd: u256, idx: int) -> str:
        return f"{int(sid)}:{int(rnd)}:{idx}"

    def _challenged_by_key(self, sid: u256, rnd: u256, who: Address) -> str:
        return f"{int(sid)}:{int(rnd)}:{who.as_hex}"

    def _require_session(self, sid: u256) -> None:
        if self.session_host.get(sid) is None:
            raise UserError("Unknown session")

    def _require_host(self, sid: u256) -> None:
        if gl.message.sender_address != self.session_host[sid]:
            raise UserError("Only host")

    def _is_member(self, sid: u256, addr: Address) -> bool:
        return self.session_member_index.get(self._mkey(sid, addr), u256(0)) != u256(0)

    def _require_member(self, sid: u256, addr: Address) -> None:
        if not self._is_member(sid, addr):
            raise UserError("Only members can do this")

    def _phase(self, sid: u256) -> u256:
        return self.session_phase.get(sid, self._PHASE_LOBBY())

    def _active_claim_round(self, sid: u256) -> u256:
        return self.session_active_claim_round.get(sid, u256(0))

    def _require_no_active_claim(self, sid: u256) -> None:
        if self._active_claim_round(sid) != u256(0):
            raise UserError("Active claim pending; finalize it before starting a new round")

    def _require_round_exists(self, sid: u256) -> u256:
        rnd = self.session_round_no.get(sid, u256(0))
        if rnd == u256(0):
            raise UserError("Round not started")
        return rnd

    def _parse_json(self, raw: str) -> typing.Any:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)

    # -------------------------
    # LLM helpers
    # -------------------------
    def _ai_generate_submission(self, prompt: str) -> str:
        task = (
            "You are a witty player in a GenLayer writing game.\n"
            "Write ONE smart, concise line answering the given prompt.\n"
            "Requirements:\n"
            "- Plain text only (no quotes/markdown).\n"
            "- Single line (no newline chars).\n"
            "- Length <= 160 characters.\n"
            "- Non-empty.\n\n"
            f"Prompt: {json.dumps(prompt)}\n\n"
            "Return STRICT JSON: {\"answer\": \"...\"}."
        )

        def leader() -> str:
            res = _prompt(task)
            return str(res)

        def validator(result) -> bool:
            try:
                raw = result.value
            except Exception:
                return False
            try:
                data = self._parse_json(str(raw))
            except Exception:
                return False
            ans = data.get("answer")
            if not isinstance(ans, str):
                return False
            if len(ans) == 0 or len(ans) > 160:
                return False
            if "\n" in ans or "\r" in ans:
                return False
            return True

        out = gl._nondet(leader, validator)
        data = self._parse_json(str(out))
        return typing.cast(str, data["answer"])

    def _ai_pick_winner_from_set(
        self,
        sid: u256,
        rnd: u256,
        allowed_hexes: list[str],
        context_reason: str,
    ) -> tuple[Address, str]:
        rk = self._rk(sid, rnd)
        member_count = int(self.session_member_count.get(sid, u256(0)))
        if member_count == 0:
            raise UserError("No members")

        allowed_set = set(allowed_hexes)
        prompt_text = self.round_prompt.get(rk, "")
        cand_lines: list[str] = []

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            h = addr.as_hex
            if h not in allowed_set:
                continue
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue
            if self.round_submission_valid.get(sk, u256(0)) != u256(1):
                continue
            sub = self.round_submission.get(sk, "")
            v = int(self.round_votes_for.get(self._cand_key(sid, rnd, h), u256(0)))
            c = int(self.round_score_clarity.get(sk, u256(0)))
            cr = int(self.round_score_creativity.get(sk, u256(0)))
            r = int(self.round_score_relevance.get(sk, u256(0)))
            cand_lines.append(
                f"- Address {h}: votes={v}, clarity={c}, creativity={cr}, relevance={r}, submission={json.dumps(sub)}"
            )

        if len(cand_lines) == 0:
            raise UserError("No submissions for given candidate set")

        cand_block = "\n".join(cand_lines)

        task = (
            "You are an impartial AI judge for a GenLayer writing game.\n"
            "You receive the round prompt, candidate set, their submissions, vote counts and AI sub-scores.\n"
            "Your job is to pick the MOST DESERVING winner.\n\n"
            f"Context / host reasoning: {json.dumps(context_reason)}\n\n"
            f"Round prompt: {json.dumps(prompt_text)}\n\n"
            "Candidates:\n"
            f"{cand_block}\n\n"
            "Rules:\n"
            "- You MUST choose winner among the candidate addresses listed above.\n"
            "- Consider BOTH human votes and AI scores (clarity/creativity/relevance).\n"
            "- You may override the host's original claim if it looks unfair.\n\n"
            "Return STRICT JSON with two fields:\n"
            '{\"winner\": \"<address_hex>\", \"explanation\": \"<short_reason>\"}\n'
            "No markdown, no ``` fences."
        )

        def leader() -> str:
            res = _prompt(task)
            return str(res)

        def validator(result) -> bool:
            try:
                raw = result.value
            except Exception:
                return False
            try:
                data = self._parse_json(str(raw))
            except Exception:
                return False
            w = data.get("winner")
            expl = data.get("explanation")
            if not isinstance(w, str) or not isinstance(expl, str):
                return False
            if w not in allowed_set:
                return False
            if len(expl) == 0 or len(expl) > 500:
                return False
            return True

        out = gl._nondet(leader, validator)
        data = self._parse_json(str(out))
        winner_hex = typing.cast(str, data["winner"])
        explanation = typing.cast(str, data.get("explanation", ""))

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            if addr.as_hex == winner_hex:
                return addr, explanation

        raise UserError("AI returned invalid winner")

    # -------------------------
    # public write: core game
    # -------------------------
    @gl.public.write
    def create_session(
        self,
        max_players: int,
        challenge_period_sec: int = 0,
        llm_prompts_enabled: bool = True,
        llm_judge_enabled: bool = True,
        appeal_bond_xp: int = 10,
        appeal_period_sec: int = 60,
    ) -> int:
        if max_players < 2:
            raise UserError("max_players must be >= 2")
        if challenge_period_sec < 0 or appeal_period_sec < 0 or appeal_bond_xp < 0:
            raise UserError("periods and bond must be >= 0")

        host = gl.message.sender_address

        sid = self.next_session_id
        if sid == u256(0):
            sid = u256(1)
        self.next_session_id = sid + u256(1)
        self.last_session_id = sid

        self.session_host[sid] = host
        self.session_max_players[sid] = u256(max_players)
        self.session_member_count[sid] = u256(1)
        self.session_round_no[sid] = u256(0)
        self.session_phase[sid] = self._PHASE_LOBBY()
        self.session_challenge_period_sec[sid] = u256(challenge_period_sec)
        self.session_llm_prompts_enabled[sid] = u256(1 if llm_prompts_enabled else 0)
        self.session_llm_judge_enabled[sid] = u256(1 if llm_judge_enabled else 0)
        self.session_appeal_bond_xp[sid] = u256(appeal_bond_xp)
        self.session_appeal_period_sec[sid] = u256(appeal_period_sec)
        self.session_active_claim_round[sid] = u256(0)

        self.session_member_at[self._mkey_idx(sid, 0)] = host
        self.session_member_index[self._mkey(sid, host)] = u256(1)

        return int(sid)

    @gl.public.write
    def join_session(self, session_id: int) -> None:
        sid = self._sid(session_id)
        self._require_session(sid)

        sender = gl.message.sender_address
        if self._is_member(sid, sender):
            raise UserError("Already joined")

        cur = self.session_member_count.get(sid, u256(0))
        maxp = self.session_max_players[sid]
        if cur >= maxp:
            raise UserError("Session is full")

        idx = int(cur)
        self.session_member_at[self._mkey_idx(sid, idx)] = sender
        self.session_member_index[self._mkey(sid, sender)] = u256(idx + 1)
        self.session_member_count[sid] = cur + u256(1)

    @gl.public.write
    def start_round(self, session_id: int, prompt: str = "") -> int:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)
        self._require_no_active_claim(sid)

        if self._phase(sid) != self._PHASE_LOBBY():
            raise UserError("Round already running")

        rnd = self.session_round_no.get(sid, u256(0)) + u256(1)
        self.session_round_no[sid] = rnd

        rk = self._rk(sid, rnd)

        if prompt.strip() == "":
            prompt_text = f"Round {int(rnd)}: explain GenLayer in ONE sentence."
        else:
            prompt_text = prompt

        self.round_prompt[rk] = prompt_text
        self.round_finalized[rk] = u256(0)
        self.round_scored[rk] = u256(0)
        self.round_challenge_count[rk] = u256(0)
        self.session_phase[sid] = self._PHASE_SUBMISSIONS()

        return int(rnd)

    @gl.public.write
    def submit(self, session_id: int, text: str) -> None:
        sid = self._sid(session_id)
        self._require_session(sid)

        sender = gl.message.sender_address
        self._require_member(sid, sender)

        if self._phase(sid) != self._PHASE_SUBMISSIONS():
            raise UserError("Not in submissions phase")

        rnd = self._require_round_exists(sid)

        sk = self._skey(sid, rnd, sender)
        if self.round_has_submitted.get(sk, u256(0)) == u256(1):
            raise UserError("Already submitted")
        if text.strip() == "":
            raise UserError("Empty submission")

        self.round_submission[sk] = text
        self.round_has_submitted[sk] = u256(1)
        self.season_xp[sender] = self.season_xp.get(sender, u256(0)) + u256(1)

    @gl.public.write
    def submit_with_llm(self, session_id: int) -> None:
        sid = self._sid(session_id)
        self._require_session(sid)

        sender = gl.message.sender_address
        self._require_member(sid, sender)

        if self._phase(sid) != self._PHASE_SUBMISSIONS():
            raise UserError("Not in submissions phase")

        rnd = self._require_round_exists(sid)
        sk = self._skey(sid, rnd, sender)
        if self.round_has_submitted.get(sk, u256(0)) == u256(1):
            raise UserError("Already submitted")

        prompt = self.round_prompt.get(self._rk(sid, rnd), "")
        if prompt == "":
            raise UserError("Missing prompt")

        text = self._ai_generate_submission(prompt)
        self.round_submission[sk] = text
        self.round_has_submitted[sk] = u256(1)
        self.season_xp[sender] = self.season_xp.get(sender, u256(0)) + u256(1)

    @gl.public.write
    def close_submissions(self, session_id: int) -> None:
        """
        Закрытие приёма ответов БЕЗ AI-модерации.
        Все сабмиты автоматически валидны, оценки фиксированные 7/7/7.
        """
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        if self._phase(sid) != self._PHASE_SUBMISSIONS():
            raise UserError("Not in submissions phase")

        rnd = self._require_round_exists(sid)
        rk = self._rk(sid, rnd)

        member_count = int(self.session_member_count.get(sid, u256(0)))

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue

            self.round_submission_valid[sk] = u256(1)
            self.round_score_clarity[sk] = u256(7)
            self.round_score_creativity[sk] = u256(7)
            self.round_score_relevance[sk] = u256(7)

        self.round_scored[rk] = u256(1)
        self.round_appeal_deadline[rk] = u256(0)
        self.session_phase[sid] = self._PHASE_VOTING()

    @gl.public.write
    def vote(self, session_id: int, candidate: str) -> None:
        sid = self._sid(session_id)
        self._require_session(sid)

        voter = gl.message.sender_address
        self._require_member(sid, voter)

        if self._phase(sid) != self._PHASE_VOTING():
            raise UserError("Not in voting phase")

        rnd = self._require_round_exists(sid)
        rk = self._rk(sid, rnd)

        if self.round_finalized.get(rk, u256(0)) != u256(0):
            raise UserError("Voting closed")

        if self.round_scored.get(rk, u256(0)) != u256(1):
            raise UserError("Round not scored yet")

        cand_addr = Address(candidate)
        self._require_member(sid, cand_addr)

        if cand_addr == voter:
            raise UserError("No self-vote")

        voter_sk = self._skey(sid, rnd, voter)
        if self.round_has_submitted.get(voter_sk, u256(0)) != u256(1):
            raise UserError("Submit first, then vote")

        cand_sk = self._skey(sid, rnd, cand_addr)
        if self.round_has_submitted.get(cand_sk, u256(0)) != u256(1):
            raise UserError("Candidate did not submit")
        if self.round_submission_valid.get(cand_sk, u256(0)) != u256(1):
            raise UserError("Candidate submission invalid")

        vk = self._voter_key(sid, rnd, voter)
        if self.round_vote_of.get(vk) is not None:
            raise UserError("Already voted")

        cand_hex = cand_addr.as_hex
        self.round_vote_of[vk] = cand_hex
        tally_key = self._cand_key(sid, rnd, cand_hex)
        self.round_votes_for[tally_key] = self.round_votes_for.get(tally_key, u256(0)) + u256(1)

    # -------------------------
    # deterministic finalize (60% human / 40% AI scores)
    # -------------------------
    def _compute_winner_by_votes(self, sid: u256, rnd: u256) -> Address:
        member_count = int(self.session_member_count.get(sid, u256(0)))
        best_votes = u256(0)
        best_hex: typing.Optional[str] = None
        best_addr: typing.Optional[Address] = None
        found_any = False

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue
            if self.round_submission_valid.get(sk, u256(0)) != u256(1):
                continue
            found_any = True
            h = addr.as_hex
            v = self.round_votes_for.get(self._cand_key(sid, rnd, h), u256(0))
            if (best_hex is None) or (v > best_votes) or (v == best_votes and h < best_hex):
                best_hex = h
                best_votes = v
                best_addr = addr

        if not found_any or best_addr is None:
            raise UserError("No submissions")
        return best_addr

    @gl.public.write
    def finalize_round(self, session_id: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        if self._phase(sid) != self._PHASE_VOTING():
            raise UserError("Not in voting phase")
        if self._active_claim_round(sid) != u256(0):
            raise UserError("Active claim pending; use finalize_claim")

        rnd = self._require_round_exists(sid)
        rk = self._rk(sid, rnd)

        status = self.round_finalized.get(rk, u256(0))
        if status == u256(1):
            return self.round_final_winner[rk].as_hex
        if status == u256(2):
            raise UserError("Claim pending; use finalize_claim")

        if self.round_scored.get(rk, u256(0)) != u256(1):
            raise UserError("Round not scored yet")

        appeal_deadline = self.round_appeal_deadline.get(rk, u256(0))
        if appeal_deadline != u256(0) and self._now() <= appeal_deadline:
            raise UserError("Appeal window still open")

        member_count = int(self.session_member_count.get(sid, u256(0)))
        if member_count == 0:
            raise UserError("No members")

        candidates: list[tuple[Address, int, int]] = []
        max_votes = 0
        max_ai = 0

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue
            if self.round_submission_valid.get(sk, u256(0)) != u256(1):
                continue

            h = addr.as_hex
            votes = int(self.round_votes_for.get(self._cand_key(sid, rnd, h), u256(0)))
            c = int(self.round_score_clarity.get(sk, u256(0)))
            cr = int(self.round_score_creativity.get(sk, u256(0)))
            r = int(self.round_score_relevance.get(sk, u256(0)))
            ai_total = c + cr + r

            candidates.append((addr, votes, ai_total))
            if votes > max_votes:
                max_votes = votes
            if ai_total > max_ai:
                max_ai = ai_total

        if len(candidates) == 0:
            raise UserError("No valid submissions")

        best_score = -1
        best_hex: typing.Optional[str] = None
        best_addr: typing.Optional[Address] = None

        for addr, votes, ai_total in candidates:
            votes_scaled = (votes * 1000) // (max_votes if max_votes > 0 else 1)
            ai_scaled = (ai_total * 1000) // (max_ai if max_ai > 0 else 1)
            total_score = votes_scaled * 60 + ai_scaled * 40

            h = addr.as_hex
            if (best_addr is None) or (total_score > best_score) or (
                total_score == best_score and h < (best_hex or h)
            ):
                best_score = total_score
                best_hex = h
                best_addr = addr

        if best_addr is None:
            raise UserError("No winner")

        self.round_final_winner[rk] = best_addr
        self.round_finalized[rk] = u256(1)
        self.round_resolution_mode[rk] = u256(1)
        self.session_phase[sid] = self._PHASE_LOBBY()
        self.session_active_claim_round[sid] = u256(0)

        self.season_xp[best_addr] = self.season_xp.get(best_addr, u256(0)) + u256(10)
        self.season_wins[best_addr] = self.season_wins.get(best_addr, u256(0)) + u256(1)

        return best_addr.as_hex

    # -------------------------
    # optimistic claim flow
    # -------------------------
    def _set_claim(self, sid: u256, rnd: u256, winner: Address, reason: str) -> None:
        rk = self._rk(sid, rnd)
        if self.round_finalized.get(rk, u256(0)) != u256(0):
            raise UserError("Round already finalized or claim pending")

        self.round_claimed_winner[rk] = winner
        self.round_claim_reason[rk] = reason
        deadline = self._now() + self.session_challenge_period_sec.get(sid, u256(0))
        self.round_claim_deadline[rk] = deadline
        self.round_challenge_count[rk] = u256(0)

        self.round_finalized[rk] = u256(2)
        self.session_active_claim_round[sid] = rnd
        self.session_phase[sid] = self._PHASE_LOBBY()

    @gl.public.write
    def optimistic_claim_winner(self, session_id: int, candidate: str, reason: str = "") -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        if self._active_claim_round(sid) != u256(0):
            raise UserError("There is already an active claim")
        if self._phase(sid) != self._PHASE_VOTING():
            raise UserError("Claim allowed only in VOTING phase")

        rnd = self._require_round_exists(sid)
        cand_addr = Address(candidate)
        self._require_member(sid, cand_addr)

        sk = self._skey(sid, rnd, cand_addr)
        if self.round_has_submitted.get(sk, u256(0)) != u256(1):
            raise UserError("Candidate did not submit")
        if self.round_submission_valid.get(sk, u256(0)) != u256(1):
            raise UserError("Candidate submission invalid")

        self._set_claim(sid, rnd, cand_addr, reason)
        return cand_addr.as_hex

    @gl.public.write
    def optimistic_claim_by_votes(self, session_id: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        if self._active_claim_round(sid) != u256(0):
            raise UserError("There is already an active claim")
        if self._phase(sid) != self._PHASE_VOTING():
            raise UserError("Claim allowed only in VOTING phase")

        rnd = self._require_round_exists(sid)
        w = self._compute_winner_by_votes(sid, rnd)
        self._set_claim(sid, rnd, w, "Claimed by on-chain vote tally")
        return w.as_hex

    @gl.public.write
    def optimistic_claim_by_llm(self, session_id: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        if self.session_llm_judge_enabled.get(sid, u256(0)) != u256(1):
            raise UserError("LLM judge disabled for this session")
        if self._active_claim_round(sid) != u256(0):
            raise UserError("There is already an active claim")
        if self._phase(sid) != self._PHASE_VOTING():
            raise UserError("Claim allowed only in VOTING phase")

        rnd = self._require_round_exists(sid)
        rk = self._rk(sid, rnd)

        if self.round_scored.get(rk, u256(0)) != u256(1):
            raise UserError("Round not scored yet")

        member_count = int(self.session_member_count.get(sid, u256(0)))
        cand_hexes: list[str] = []

        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue
            if self.round_submission_valid.get(sk, u256(0)) != u256(1):
                continue
            cand_hexes.append(addr.as_hex)

        if len(cand_hexes) == 0:
            raise UserError("No submissions")

        w_addr, _expl = self._ai_pick_winner_from_set(
            sid, rnd, cand_hexes, "Initial claim by LLM judge"
        )

        self._set_claim(sid, rnd, w_addr, "Claimed by LLM judge")
        return w_addr.as_hex

    @gl.public.write
    def challenge_claim(self, session_id: int, alternative_winner: str, reason: str) -> int:
        sid = self._sid(session_id)
        self._require_session(sid)

        challenger = gl.message.sender_address
        self._require_member(sid, challenger)

        rnd = self._active_claim_round(sid)
        if rnd == u256(0):
            raise UserError("No active claim")

        rk = self._rk(sid, rnd)
        if self.round_finalized.get(rk, u256(0)) != u256(2):
            raise UserError("No active claim")

        if self._now() > self.round_claim_deadline.get(rk, u256(0)):
            raise UserError("Challenge window closed")

        cbk = self._challenged_by_key(sid, rnd, challenger)
        if self.round_challenged_by.get(cbk, u256(0)) == u256(1):
            raise UserError("Already challenged")

        alt = Address(alternative_winner)
        self._require_member(sid, alt)

        alt_sk = self._skey(sid, rnd, alt)
        if self.round_has_submitted.get(alt_sk, u256(0)) != u256(1):
            raise UserError("Alternative winner did not submit")
        if self.round_submission_valid.get(alt_sk, u256(0)) != u256(1):
            raise UserError("Alternative submission invalid")

        if reason.strip() == "":
            raise UserError("Empty reason")

        idx = int(self.round_challenge_count.get(rk, u256(0)))
        self.round_challenge_who[self._chk_key(sid, rnd, idx)] = challenger
        self.round_challenge_alt[self._chk_key(sid, rnd, idx)] = alt
        self.round_challenge_reason[self._chk_key(sid, rnd, idx)] = reason
        self.round_challenge_count[rk] = u256(idx + 1)
        self.round_challenged_by[cbk] = u256(1)

        return idx

    @gl.public.write
    def finalize_claim(self, session_id: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        rnd = self._active_claim_round(sid)
        if rnd == u256(0):
            raise UserError("No active claim")

        rk = self._rk(sid, rnd)
        if self.round_finalized.get(rk, u256(0)) != u256(2):
            raise UserError("No active claim")

        claimed = self.round_claimed_winner.get(rk)
        if claimed is None:
            raise UserError("No claimed winner")

        challenge_count = int(self.round_challenge_count.get(rk, u256(0)))
        deadline = self.round_claim_deadline.get(rk, u256(0))

        if challenge_count > 0 and self._now() <= deadline:
            raise UserError("Wait until challenge window ends")

        appeal_deadline = self.round_appeal_deadline.get(rk, u256(0))
        if appeal_deadline != u256(0) and self._now() <= appeal_deadline:
            raise UserError("AI-score appeal window still open")

        winner: Address = claimed
        mode: u256 = u256(2)
        explanation = "Accepted host claim (no challenges)."

        if challenge_count > 0:
            cand_hexes: list[str] = [claimed.as_hex]
            for i in range(challenge_count):
                alt = self.round_challenge_alt[self._chk_key(sid, rnd, i)]
                h = alt.as_hex
                if h not in cand_hexes:
                    cand_hexes.append(h)

            if self.session_llm_judge_enabled.get(sid, u256(0)) == u256(1):
                reason = "Disputed claim: host + challengers provided alternatives."
                winner, explanation = self._ai_pick_winner_from_set(
                    sid, rnd, cand_hexes, reason
                )
                mode = u256(3)
            else:
                winner = self._compute_winner_by_votes(sid, rnd)
                mode = u256(4)
                explanation = "Fallback to on-chain vote tally (LLM judge disabled)."

        self.round_final_winner[rk] = winner
        self.round_finalized[rk] = u256(1)
        self.round_resolution_mode[rk] = mode
        self.round_llm_explanation[rk] = explanation
        self.session_active_claim_round[sid] = u256(0)
        self.session_phase[sid] = self._PHASE_LOBBY()

        self.season_xp[winner] = self.season_xp.get(winner, u256(0)) + u256(10)
        self.season_wins[winner] = self.season_wins.get(winner, u256(0)) + u256(1)

        return winner.as_hex

    # -------------------------
    # XP helpers
    # -------------------------
    @gl.public.write
    def reward_player(self, session_id: int, round_no: int, player: str, amount: int) -> None:
        if amount <= 0:
            raise UserError("amount must be > 0")

        sid = self._sid(session_id)
        self._require_session(sid)
        self._require_host(sid)

        rnd = u256(round_no)
        addr = Address(player)
        self._require_member(sid, addr)

        sk = self._skey(sid, rnd, addr)
        if self.round_has_submitted.get(sk, u256(0)) != u256(1):
            raise UserError("Player did not submit in that round")

        self.season_xp[addr] = self.season_xp.get(addr, u256(0)) + u256(amount)

    @gl.public.write
    def add_xp(self, player: str, amount: int) -> None:
        if amount <= 0:
            raise UserError("amount must be > 0")
        addr = Address(player)
        cur = self.season_xp.get(addr, u256(0))
        self.season_xp[addr] = cur + u256(amount)

    # -------------------------
    # public view
    # -------------------------
    @gl.public.view
    def get_next_session_id(self) -> int:
        return int(self.next_session_id)

    @gl.public.view
    def get_last_session_id(self) -> int:
        nid = self.next_session_id
        if nid <= u256(1):
            return 0
        return int(nid - u256(1))

    @gl.public.view
    def get_session(self, session_id: int) -> dict[str, typing.Any]:
        sid = self._sid(session_id)
        self._require_session(sid)
        return {
            "session_id": int(sid),
            "host": self.session_host[sid].as_hex,
            "max_players": int(self.session_max_players[sid]),
            "member_count": int(self.session_member_count.get(sid, u256(0))),
            "round_no": int(self.session_round_no.get(sid, u256(0))),
            "phase": int(self._phase(sid)),
            "challenge_period_sec": int(self.session_challenge_period_sec.get(sid, u256(0))),
            "appeal_period_sec": int(self.session_appeal_period_sec.get(sid, u256(0))),
            "appeal_bond_xp": int(self.session_appeal_bond_xp.get(sid, u256(0))),
            "llm_prompts_enabled": int(self.session_llm_prompts_enabled.get(sid, u256(0))),
            "llm_judge_enabled": int(self.session_llm_judge_enabled.get(sid, u256(0))),
            "active_claim_round": int(self._active_claim_round(sid)),
        }

    @gl.public.view
    def is_member(self, session_id: int, player: str) -> bool:
        sid = self._sid(session_id)
        self._require_session(sid)
        return self._is_member(sid, Address(player))

    @gl.public.view
    def get_member_at(self, session_id: int, index: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        count = int(self.session_member_count.get(sid, u256(0)))
        if index < 0 or index >= count:
            raise UserError("index out of range")
        return self.session_member_at[self._mkey_idx(sid, index)].as_hex

    @gl.public.view
    def get_round_prompt(self, session_id: int, round_no: int) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        return self.round_prompt.get(self._rk(sid, u256(round_no)), "")

    @gl.public.view
    def get_submission(self, session_id: int, round_no: int, player: str) -> str:
        sid = self._sid(session_id)
        self._require_session(sid)
        addr = Address(player)
        return self.round_submission.get(self._skey(sid, u256(round_no), addr), "")

    @gl.public.view
    def list_round_submissions(self, session_id: int, round_no: int) -> list[dict[str, typing.Any]]:
        sid = self._sid(session_id)
        self._require_session(sid)
        rnd = u256(round_no)
        member_count = int(self.session_member_count.get(sid, u256(0)))

        out: list[dict[str, typing.Any]] = []
        for i in range(member_count):
            addr = self.session_member_at[self._mkey_idx(sid, i)]
            sk = self._skey(sid, rnd, addr)
            if self.round_has_submitted.get(sk, u256(0)) != u256(1):
                continue
            h = addr.as_hex
            votes = int(self.round_votes_for.get(self._cand_key(sid, rnd, h), u256(0)))
            valid = int(self.round_submission_valid.get(sk, u256(0))) == 1
            out.append(
                {
                    "author": h,
                    "text": self.round_submission.get(sk, ""),
                    "valid": valid,
                    "votes": votes,
                    "clarity": int(self.round_score_clarity.get(sk, u256(0))),
                    "creativity": int(self.round_score_creativity.get(sk, u256(0))),
                    "relevance": int(self.round_score_relevance.get(sk, u256(0))),
                }
            )
        return out

    @gl.public.view
    def get_votes_for(self, session_id: int, round_no: int, candidate: str) -> int:
        sid = self._sid(session_id)
        self._require_session(sid)
        rnd = u256(round_no)
        cand_hex = Address(candidate).as_hex
        return int(self.round_votes_for.get(self._cand_key(sid, rnd, cand_hex), u256(0)))

    @gl.public.view
    def get_round_info(self, session_id: int, round_no: int) -> dict[str, typing.Any]:
        sid = self._sid(session_id)
        self._require_session(sid)
        rnd = u256(round_no)
        rk = self._rk(sid, rnd)

        finalw = self.round_final_winner.get(rk)
        claimed = self.round_claimed_winner.get(rk)

        return {
            "prompt": self.round_prompt.get(rk, ""),
            "finalized_status": int(self.round_finalized.get(rk, u256(0))),
            "claim_deadline": int(self.round_claim_deadline.get(rk, u256(0))),
            "claim_reason": self.round_claim_reason.get(rk, ""),
            "claimed_winner": None if claimed is None else claimed.as_hex,
            "challenge_count": int(self.round_challenge_count.get(rk, u256(0))),
            "final_winner": None if finalw is None else finalw.as_hex,
            "resolution_mode": int(self.round_resolution_mode.get(rk, u256(0))),
            "llm_explanation": self.round_llm_explanation.get(rk, ""),
            "appeal_deadline": int(self.round_appeal_deadline.get(rk, u256(0))),
        }

    @gl.public.view
    def get_round_winner(self, session_id: int, round_no: int) -> typing.Optional[str]:
        sid = self._sid(session_id)
        self._require_session(sid)
        rk = self._rk(sid, u256(round_no))
        w = self.round_final_winner.get(rk)
        return None if w is None else w.as_hex

    @gl.public.view
    def get_xp(self, player: str) -> int:
        addr = Address(player)
        return int(self.season_xp.get(addr, u256(0)))

    @gl.public.view
    def get_my_xp(self) -> int:
        return int(self.season_xp.get(gl.message.sender_address, u256(0)))

    @gl.public.view
    def get_wins(self, player: str) -> int:
        addr = Address(player)
        return int(self.season_wins.get(addr, u256(0)))

    # -------------------------
    # constructor
    # -------------------------
    def __init__(self):
        self.next_session_id = u256(1)
        self.last_session_id = u256(0)
        
