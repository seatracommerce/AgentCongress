"""Single caucus agent — wraps Claude API call with caucus persona."""
from __future__ import annotations

import logging
import re

import anthropic

from backend.agents.caucuses import Caucus
from backend.config import get_settings

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-6"


class CaucusAgent:
    def __init__(self, caucus: Caucus) -> None:
        self.caucus = caucus
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            settings = get_settings()
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def opening_statement(self, bill_title: str, bill_summary: str) -> str:
        """Generate opening statement on a bill."""
        prompt = (
            f"The US House is considering: **{bill_title}**\n\n"
            f"Bill summary:\n{bill_summary or 'No summary available.'}\n\n"
            f"Deliver your caucus's opening statement on this bill. "
            f"State your initial position (support/oppose/conditional) and your 2-3 key concerns or priorities. "
            f"Be direct and speak as the {self.caucus.display_name}."
        )
        return await self._call(prompt)

    async def debate_response(
        self,
        bill_title: str,
        bill_summary: str,
        prior_statements: list[dict[str, str]],
    ) -> str:
        """Generate a debate round response, engaging with prior statements."""
        transcript = "\n\n".join(
            f"**{s['caucus_name']}**: {s['content']}" for s in prior_statements
        )
        prompt = (
            f"The debate continues on: **{bill_title}**\n\n"
            f"Prior statements from other caucuses:\n\n{transcript}\n\n"
            f"Respond to the arguments made above. Directly address at least one other caucus by name. "
            f"Refine or defend your position based on what you've heard. "
            f"Speak as the {self.caucus.display_name}."
        )
        return await self._call(prompt)

    async def closing_and_vote(
        self,
        bill_title: str,
        bill_summary: str,
        prior_statements: list[dict[str, str]],
    ) -> tuple[str, str]:
        """Generate closing statement and cast vote.

        Returns (full_content, vote_choice) where vote_choice is 'yea', 'nay', or 'present'.
        """
        transcript = "\n\n".join(
            f"**{s['caucus_name']}**: {s['content']}" for s in prior_statements
        )
        prompt = (
            f"Final round of debate on: **{bill_title}**\n\n"
            f"Full debate transcript:\n\n{transcript}\n\n"
            f"Deliver your closing statement and declare your final vote. "
            f"End your response with exactly one of these lines:\n"
            f"VOTE: YEA\n"
            f"VOTE: NAY\n"
            f"VOTE: PRESENT\n"
            f"Speak as the {self.caucus.display_name}."
        )
        content = await self._call(prompt)
        vote = _extract_vote(content)
        return content, vote

    async def _call(self, user_prompt: str) -> str:
        client = self._get_client()
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=600,
            system=self.caucus.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text


def _extract_vote(content: str) -> str:
    """Parse VOTE: YEA/NAY/PRESENT from closing statement."""
    match = re.search(r"VOTE:\s*(YEA|NAY|PRESENT)", content, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    logger.warning("Could not parse vote from closing statement, defaulting to PRESENT")
    return "present"
