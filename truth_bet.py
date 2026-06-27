# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import json
import typing


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


@allow_storage
@dataclass
class BetInfo:
    yes_amount: u256
    no_amount: u256
    claimed: bool


class TruthBet(gl.Contract):
    """
    TruthBet: a two-sided betting market that resolves itself.

    Two outcomes ("YES" and "NO") for a real-world question. Anyone can
    bet GEN on either side while the market is open. Once resolution
    time has passed, anyone can call resolve() — the contract fetches
    a web page, asks an LLM to judge the outcome from that page, and
    all validators must agree (Equivalence Principle) before the
    contract accepts the result. Winners then withdraw their share of
    the total pool, proportional to their stake on the winning side.
    """

    question: str
    resolution_url: str
    closes_at: str

    yes_pool: u256
    no_pool: u256
    bets: TreeMap[Address, BetInfo]

    resolved: bool
    outcome: str
    rationale: str

    def __init__(self, question: str, resolution_url: str, closes_at: str):
        self.question = question
        self.resolution_url = resolution_url
        self.closes_at = closes_at

        self.yes_pool = u256(0)
        self.no_pool = u256(0)
        self.bets = TreeMap()

        self.resolved = False
        self.outcome = ""
        self.rationale = ""

    @gl.public.write.payable
    def bet_yes(self) -> None:
        self._place_bet(is_yes=True)

    @gl.public.write.payable
    def bet_no(self) -> None:
        self._place_bet(is_yes=False)

    def _place_bet(self, is_yes: bool) -> None:
        if self.resolved:
            raise gl.vm.UserError("Market already resolved, no more bets accepted")

        v = gl.message.value
        if v == u256(0):
            raise gl.vm.UserError("Send GEN with your bet")

        sender = gl.message.sender_address
        info = self.bets.get(sender, None)
        if info is None:
            info = BetInfo(u256(0), u256(0), False)

        if is_yes:
            self.yes_pool = self.yes_pool + v
            info.yes_amount = info.yes_amount + v
        else:
            self.no_pool = self.no_pool + v
            info.no_amount = info.no_amount + v

        self.bets[sender] = info

    @gl.public.write
    def resolve(self) -> typing.Any:
        if self.resolved:
            return {"already_resolved": True, "outcome": self.outcome}

        def judge() -> str:
            response = gl.nondet.web.get(self.resolution_url)
            web_data = response.body.decode("utf-8")
            print(web_data)

            task = f"""You are adjudicating a yes/no prediction market.

Question: {self.question}
The market is only meant to resolve on or after: {self.closes_at}

Web page content (use this as your evidence):
{web_data}
End of web page content.

Based only on the evidence above, decide the answer to the question.

Respond with this exact JSON format and nothing else:
{{
    "outcome": str,
    "rationale": str
}}
It is mandatory that you respond only using the JSON format above,
nothing else. No markdown formatting, no code fences, no extra words.
This result must be parsable by a JSON parser without errors.
"""
            result = (
                gl.nondet.exec_prompt(task)
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            print(result)
            return json.dumps(json.loads(result), sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(judge))

        if result_json["outcome"] in ("YES", "NO"):
            self.resolved = True
            self.outcome = result_json["outcome"]
            self.rationale = result_json["rationale"]

        return result_json

    @gl.public.write
    def claim(self) -> u256:
        if not self.resolved:
            raise gl.vm.UserError("Market not resolved yet")

        sender = gl.message.sender_address
        info = self.bets.get(sender, None)
        if info is None:
            raise gl.vm.UserError("No bets found for this address")

        if info.claimed:
            raise gl.vm.UserError("Already claimed")

        winning_pool = self.yes_pool if self.outcome == "YES" else self.no_pool
        losing_pool = self.no_pool if self.outcome == "YES" else self.yes_pool
        my_stake = info.yes_amount if self.outcome == "YES" else info.no_amount

        if my_stake == u256(0):
            raise gl.vm.UserError("No winning stake for this address")

        if winning_pool == u256(0):
            raise gl.vm.UserError("No winning pool to distribute")

        payout = my_stake + (my_stake * losing_pool) // winning_pool

        info.claimed = True
        self.bets[sender] = info

        _Recipient(sender).emit_transfer(value=payout)

        return payout

    @gl.public.view
    def get_market(self) -> dict:
        return {
            "question": self.question,
            "resolution_url": self.resolution_url,
            "closes_at": self.closes_at,
            "yes_pool": str(self.yes_pool),
            "no_pool": str(self.no_pool),
            "resolved": self.resolved,
            "outcome": self.outcome,
            "rationale": self.rationale,
        }

    @gl.public.view
    def get_my_bets(self, addr: Address) -> dict:
        info = self.bets.get(addr, None)
        if info is None:
            return {"yes": "0", "no": "0", "claimed": False}
        return {
            "yes": str(info.yes_amount),
            "no": str(info.no_amount),
            "claimed": info.claimed,
        }
