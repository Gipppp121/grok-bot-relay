"""Seeded week. No network. Same ideas, scores, and prices every run.

Wake math for this set, one run() per step:

  scout 1
  pain miner 13
  judge 13
  4 ideas die under 5/8, so 9 continue
  builder 9, pitch 9, buyer 9
  6 buys fit under $40, so chief 6

  1 + 13 + 13 + 9 + 9 + 9 + 6 = 60
"""

from __future__ import annotations

from relay.models import Idea

# Reads charged for one run. Each stays inside that bot's minute slice.
READ_COST = {
    "scout": 9,
    "pain_miner": 4,
    "judge": 2,
    "builder": 1,
    "pitch": 2,
    "buyer": 0,
    "chief": 1,
}

# Human yeses the demo records before Buyer runs. Buyer still checks the file.
# idea-10 is approved and then hits the spend cap. idea-12 and idea-13 are not.
DEMO_YES = frozenset(
    {
        "idea-01",
        "idea-02",
        "idea-04",
        "idea-06",
        "idea-07",
        "idea-09",
        "idea-10",
    }
)


def _idea(
    number: int,
    title: str,
    summary: str,
    price_cents: int,
    scores: tuple[int, int, int, int],
    pains: list[str],
    pitch: str,
) -> Idea:
    pain_sharp, buyer_reachable, build_small, channel_fit = scores
    return Idea(
        id=f"idea-{number:02d}",
        title=title,
        summary=summary,
        price_cents=price_cents,
        scores={
            "pain_sharp": pain_sharp,
            "buyer_reachable": buyer_reachable,
            "build_small": build_small,
            "channel_fit": channel_fit,
        },
        pains=pains,
        pitch=pitch,
    )


IDEAS: tuple[Idea, ...] = (
    _idea(
        1,
        "Signup friction log",
        "People quit the form when the third field appears.",
        900,
        (2, 2, 2, 2),
        [
            "The third field has no label a buyer understands.",
            "Support mail is mostly 'where did my signup go'.",
        ],
        "Ship a one field signup and keep the rest for later.",
    ),
    _idea(
        2,
        "Pricing page hesitation",
        "Visitors open pricing and leave without a click.",
        800,
        (2, 2, 2, 1),
        [
            "The page has four plans and no default.",
            "Session recordings stop on the pricing scroll.",
        ],
        "One plan, one price, one button.",
    ),
    _idea(
        3,
        "AI for everything",
        "A vague pitch with no named buyer.",
        500,
        (1, 1, 1, 1),
        ["No one can point at a task they would pay to remove."],
        "Not sharp enough to build.",
    ),
    _idea(
        4,
        "Waitlist rate limit",
        "The waitlist returns 200 when it should say try again.",
        700,
        (2, 2, 1, 2),
        [
            "A burst of signups looks like success and drops names.",
            "The handler never returns a retry status.",
        ],
        "Return a clear retry after the cap, and count the drops.",
    ),
    _idea(
        5,
        "Another chatbot wrapper",
        "A thin wrapper with no specific pain.",
        500,
        (2, 0, 1, 1),
        ["The pitch is 'chat, but for work' and names no workflow."],
        "No buyer to reach.",
    ),
    _idea(
        6,
        "Ledger not email",
        "Handoffs live in a file the next bot can read.",
        600,
        (2, 2, 0, 2),
        [
            "Status is copied into mail and goes stale.",
            "The next bot cannot see why the last one stopped.",
        ],
        "One append only ledger. The next bot starts on DONE.",
    ),
    _idea(
        7,
        "Domain cap watch",
        "Track a short list of names and stop at a spend cap.",
        500,
        (1, 2, 2, 2),
        [
            "Good names get bought by reflex.",
            "Nobody wrote down the cap before the cart filled.",
        ],
        "Watch the list. Buy only with a yes, under the cap.",
    ),
    _idea(
        8,
        "Blank landing page",
        "A page with no offer and no reader.",
        500,
        (0, 1, 1, 1),
        ["The hero is empty. There is nothing to judge."],
        "Nothing to launch.",
    ),
    _idea(
        9,
        "Morning brief on change",
        "A chief note only when the ledger grew.",
        400,
        (2, 1, 2, 1),
        [
            "Daily mail fires even when every bot slept.",
            "People mute the channel that was supposed to matter.",
        ],
        "Print the brief when the ledger changes. Stay quiet when it does not.",
    ),
    _idea(
        10,
        "Status wall for launch",
        "One screen of bot state for a filming day.",
        300,
        (2, 2, 1, 1),
        [
            "The launch state is spread across six tools.",
            "Filming day needs one picture, not a tour.",
        ],
        "A local wall that reads the ledger. No extra spend.",
    ),
    _idea(
        11,
        "Repost tool",
        "Repeats other people's posts on a timer.",
        500,
        (1, 0, 2, 1),
        ["No original pain. The plan is volume."],
        "Do not build a repost timer.",
    ),
    _idea(
        12,
        "Paid ads blast",
        "Spend first and learn later.",
        1000,
        (2, 2, 2, 2),
        [
            "The idea is clear and the invoice is the whole plan.",
            "Nobody has written a yes for this spend.",
        ],
        "Hold the buy until there is an explicit yes.",
    ),
    _idea(
        13,
        "Sticker pack",
        "Cute, and not the launch.",
        200,
        (2, 2, 1, 1),
        ["Fun, with no launch job attached."],
        "Leave it unapproved.",
    ),
)


def idea_by_id(idea_id: str) -> Idea:
    for idea in IDEAS:
        if idea.id == idea_id:
            return idea
    raise KeyError(idea_id)
