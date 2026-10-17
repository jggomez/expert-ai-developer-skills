"""Shared synthetic scenarios used by reader unit tests and contract tests."""

from __future__ import annotations

from tests.fixtures.antigravity import (
    ERROR,
    GENERIC,
    PLANNER,
    SYSTEM,
    USER_INPUT,
    AgyCall,
    AgyConversation,
    AgyStep,
)
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeSession, tool_use, usage

__all__ = [
    "CLAUDE_SESSION_ID",
    "agy_child",
    "agy_root_conversation",
    "agy_standard_conversations",
    "claude_standard_session",
]

CLAUDE_SESSION_ID = "s-main-0001"


def claude_standard_session() -> ClaudeSession:
    """Two prompts, streaming duplicates, nested subagents, a background agent and noise lines."""
    s = ClaudeSession(CLAUDE_SESSION_ID)
    s.noise()
    p1 = s.prompt(0, "p1")
    a5 = s.assistant(
        5,
        "r1",
        parent=p1,
        use=usage(100, 10, cache_5m=300, cache_1h=200, cache_read=1_000),
    )
    a6 = s.assistant(
        6,
        "r1",
        parent=a5,
        use=usage(100, 30, cache_5m=300, cache_1h=200, cache_read=1_000),
    )
    a7 = s.assistant(
        7,
        "r1",
        parent=a6,
        use=usage(100, 25, cache_5m=300, cache_1h=200, cache_read=1_000),
        tools=[
            tool_use(
                "Agent",
                "tu-agent-1",
                description=CANARY,
                prompt=CANARY,
                subagent_type="code-implementer",
            ),
            tool_use(
                "Edit",
                "tu-edit-1",
                file_path=f"/Users/dev/work/demo-repo/{CANARY}.py",
                old_string=CANARY,
                new_string=CANARY,
            ),
            tool_use(
                "Edit",
                "tu-edit-2",
                file_path=f"/Users/dev/work/demo-repo/{CANARY}.py",
                old_string=CANARY,
                new_string="x",
            ),
            tool_use(
                "Write",
                "tu-write-1",
                file_path=f"/Users/dev/work/demo-repo/b-{CANARY}.py",
                content=CANARY,
            ),
            tool_use(
                "Bash", "tu-bash-1", command=f"pytest -q {CANARY}", description=CANARY
            ),
            tool_use("Bash", "tu-bash-2", command=f"ls {CANARY}"),
        ],
    )
    r8 = s.tool_result(8, "p1", parent=a7, tool_use_id="tu-edit-1")
    r9 = s.tool_result(9, "p1", parent=r8, tool_use_id="tu-bash-1", is_error=True)
    r10 = s.tool_result(10, "p1", parent=r9, tool_use_id="tu-bash-2")
    r10b = s.tool_result(10, "p1", parent=r10, tool_use_id="tu-edit-2")
    r10c = s.tool_result(10, "p1", parent=r10b, tool_use_id="tu-write-1")
    s.attachment(11, parent=r10c)
    a12 = s.assistant(12, "r2", parent=r10c, use=usage(200, 20, cache_read=2_000))
    s.turn_duration(90, parent=a12, duration_ms=90_000)
    s.tool_result(200, "p1", parent=a12, tool_use_id="tu-agent-1")
    p2 = s.prompt(1000, "p2")
    s.assistant(
        1010, "r3", parent=p2, model="<synthetic>", use=usage(0, 0, cache_read=0)
    )
    a1020 = s.assistant(
        1020, "r4", parent="uuid-that-does-not-exist", use=usage(10, 5, cache_read=0)
    )
    s.assistant(
        1030, "r5", parent=a1020, use=usage(10, 6, cache_read=0), api_error=True
    )

    a1 = s.subagent(
        "a1", agent_type="code-implementer", tool_use_id="tu-agent-1", spawn_depth=1
    )
    a1p = a1.prompt(20, "p1")
    a1a = a1.assistant(
        25,
        "ra1",
        parent=a1p,
        model="claude-sonnet-5-5",
        use=usage(1_000, 100, cache_read=5_000),
        tools=[
            tool_use("Agent", "tu-agent-2", description=CANARY, prompt=CANARY),
            tool_use("Edit", "tu-a1-edit", file_path=f"/tmp/{CANARY}/c.py"),
        ],
    )
    a1r = a1.tool_result(26, "p1", parent=a1a, tool_use_id="tu-a1-edit")
    a1late = a1.prompt(1500, "p2", parent=a1r)
    a1.assistant(
        1510,
        "ra1b",
        parent=a1late,
        model="claude-sonnet-5-5",
        use=usage(50, 5, cache_read=0),
    )

    a2 = s.subagent(
        "a2",
        agent_type="qa-tester",
        tool_use_id="tu-agent-2",
        spawn_depth=2,
        parent_agent_id="a1",
    )
    a2p = a2.prompt(30, "p1")
    a2.assistant(
        35,
        "ra2",
        parent=a2p,
        model="claude-haiku-4-5-20251001",
        use=usage(10, 1, cache_read=0),
    )

    a3 = s.subagent("a3", meta=False)
    a3p = a3.prompt(40, "p1")
    a3.assistant(45, "ra3", parent=a3p, use=usage(10, 1, cache_read=0))
    return s


def agy_root_conversation() -> AgyConversation:
    return AgyConversation(
        conversation_id="c-root",
        trajectory_id="t-root",
        steps=[
            AgyStep(0, SYSTEM, 0),
            AgyStep(1, PLANNER, 2, tokens=(5, 5, 5)),
            AgyStep(2, USER_INPUT, 10),
            AgyStep(
                3,
                PLANNER,
                15,
                tokens=(1_000, 10_000, 200),
                tool_calls=(
                    ("invoke_subagent", {"Prompt": CANARY, "toolSummary": CANARY}),
                    (
                        "write_to_file",
                        {
                            "TargetFile": f"/Users/dev/{CANARY}.py",
                            "CodeContent": CANARY,
                        },
                    ),
                    (
                        "run_command",
                        {"CommandLine": f"pytest -q {CANARY}", "Cwd": f"/{CANARY}"},
                    ),
                ),
            ),
            AgyStep(4, GENERIC, 20),
            AgyStep(5, GENERIC, 21),
            AgyStep(6, GENERIC, 22, status="ERROR", error=f"boom {CANARY}"),
            AgyStep(
                7,
                PLANNER,
                30,
                tokens=(500, 2_000, 100),
                tool_calls=(("view_file", {"AbsolutePath": CANARY}),),
            ),
            AgyStep(8, GENERIC, 31),
            AgyStep(9, ERROR, 32, error=f"err {CANARY}"),
            AgyStep(10, USER_INPUT, 1000),
            AgyStep(11, PLANNER, 1005, tokens=(7, 70, 3)),
            AgyStep(12, PLANNER, 1010),
        ],
        calls=[
            AgyCall(
                0,
                input=5,
                cache_read=5,
                output=5,
                thinking=1,
                visible=4,
                trajectory_id="t-old",
            ),
            AgyCall(
                2, input=1_000, cache_read=10_000, output=200, thinking=50, visible=150
            ),
            AgyCall(
                6,
                input=500,
                cache_read=2_000,
                output=100,
                thinking=0,
                visible=100,
                model="claude-sonnet-4-6",
                label="Claude Sonnet 4.6 (Thinking)",
                latency=(1, 0),
            ),
            AgyCall(
                10, input=7, cache_read=70, output=3, thinking=1, visible=2, model=""
            ),
            AgyCall(11, usage=False, latency=None),
        ],
        parent_refs=(("t-old", 1),),
    )


def agy_child(
    cid: str, parent: str, agent: str, spawn: int | None, base: float, **kw: object
) -> AgyConversation:
    return AgyConversation(
        conversation_id=cid,
        trajectory_id=f"t-{cid}",
        parent_id=parent,
        agent_name=agent,
        spawn_step_index=spawn,
        steps=[
            AgyStep(0, USER_INPUT, base),
            AgyStep(
                1,
                PLANNER,
                base + 2,
                tokens=(10, 100, 20),
                tool_calls=(("view_file", {"AbsolutePath": CANARY}),),
            ),
            AgyStep(2, GENERIC, base + 3),
        ],
        calls=[AgyCall(0, input=10, cache_read=100, output=20, thinking=5, visible=15)],
        **kw,  # type: ignore[arg-type]
    )


def agy_standard_conversations() -> list[AgyConversation]:
    other = AgyConversation(
        conversation_id="c-other",
        trajectory_id="t-other",
        steps=[AgyStep(0, USER_INPUT, 5000), AgyStep(3, PLANNER, 5005)],
        calls=[
            AgyCall(
                2, input=1_000, cache_read=10_000, output=200, trajectory_id="t-root"
            ),
            AgyCall(2, input=1, cache_read=1, output=1),
        ],
        parent_refs=(("t-root", 3),),
    )
    return [
        agy_root_conversation(),
        agy_child("c-child1", "c-root", "code-implementer", 3, 16),
        agy_child("c-child2", "c-child1", "qa-tester", 1, 26),
        agy_child(
            "c-child3", "c-root", "compliance-verifier", None, 1001, transcript=False
        ),
        other,
    ]
