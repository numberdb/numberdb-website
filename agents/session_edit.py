"""Commit a table edit made in a session with a person.

Two accounts write to this database and the distinction is about who decided,
not about which software typed. An autonomous run writes as zeta3 and its
revisions name the tool. An edit made while somebody is sitting there writes
as that person -- but must still say that a program was involved, because a
reader is entitled to know and because `accepted_edit_count` reads the phrase
`assisted by` when deciding what a track record is worth.

Every edit made from a conversation went in with `produced_by` empty until
this existed: twenty revisions across fourteen tables that the history claimed
were typed by hand. Import this rather than calling `commit_table` directly,
and the field cannot be forgotten.

    from agents.session_edit import edit_with_person
    edit_with_person(table, tree, person, 'what changed and why')
"""

#: What to record when a session does not say which assistant it is. Named
#: rather than left blank: "some program" is more honest than nothing, and
#: nothing is what the history said for a day.
DEFAULT_ASSISTANT = 'an assistant'


def producer(assistant=DEFAULT_ASSISTANT):
    """The `produced_by` string for an edit made with a person.

    Begins with `assisted by` because that is the phrase the trust counter
    looks for, and the field is capped at 100 characters by the model.
    """
    return ('assisted by %s' % (assistant or DEFAULT_ASSISTANT).strip())[:100]


def edit_with_person(table, tree, person, message, assistant=DEFAULT_ASSISTANT,
                     **kwargs):
    """Commit `tree` as `person`, recording that an assistant helped.

    Everything else is `commit_table`'s, including `base`, which defaults to
    the table's head here because a session edit is always made against what
    is currently there.
    """
    from numberdb_app.editing import commit_table

    kwargs.setdefault('base', table.head_revision)
    return commit_table(table, tree, author=person, message=message,
                        produced_by=producer(assistant), **kwargs)
