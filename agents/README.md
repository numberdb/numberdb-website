# Agents

Programs that reach the database only through the API, holding a key, rate
limited, named in `produced_by`, unable to publish. The same boundary a human
contributor works across; an agent should not have a private door. See
`docs/design/guarding-generated-tables.md`.

    table-ideas/    stage one: propose tables worth making
    table-build/    stage two: build one proposal, leave it offered for review
    lessons/        what a run met that the skill did not cover

Each stage is a fresh session, one batch at a time. The skill is the memory: if
a run cannot do the work from <https://numberdb.org/skill> alone, the skill is
incomplete, and a long session would hide that behind conversational memory
rather than fixing it. `docs/design/two-stage-tables.md` argues this out.
