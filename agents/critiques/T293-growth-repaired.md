*done* -- did not grow T293; checked the live table and the pinned-source Sage count, which gives 1171 rows at $N\leq250$, 1195 at $N\leq254$, and 1213 at $N\leq255$.
*left for a person* -- the BSD companion mismatch is real: T292 is still five fields with $N\leq150$, and only 309 of T293's 1171 rows have a class-level counterpart, but the repair belongs to T292 or to a new paired decision.
*left for a person* -- the rank-2 continuation is a new sibling table, not a repair to T293; the Sage source check confirmed T293 has 1163 rank-1 rows and 8 rank-2 rows.
*done* -- changed `comment-small-fields` through the API to name $199$ over $D=5$ and $103$ over $D=8$ directly and to say the $N\leq250$ bound leaves 17 rows over $D=5$ and 348 over $D=21$; checked those numbers with the generator under Sage and ran a clean audit.
*done* -- aligned the repository copy with the live table: updated `table.yaml`'s small-field comment, companion-table relation, and complete note, and removed the unused stale `curve_data.py`; checked the YAML parses and that no generator imports the deleted snapshot.
*declined* -- did not rebalance to equal per-field depth, because the current conductor-norm rule is easier for a reader to apply and the critique itself does not recommend the recut.
*declined* -- did not extend from $N\leq250$ to $N\leq254$; the Sage count confirms it would add only 24 rows, while $250$ is the clearer printed bound.
*declined* -- did not trim entry comments, because they carry conductor ideals, ranks, and equations that are not elsewhere in each row, and the table is constrained by entry count rather than bytes.
*declined* -- left the completeness note's soft-limit clause in place; it gives the reason for the cutoff, and the audit after the API edit is clean.
