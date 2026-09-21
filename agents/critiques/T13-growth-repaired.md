done -- added `complete: no` and a `complete-note` for $0\leq n\leq 250`; checked the live table had no completeness fields and, after the edit, rendered the range sentence on the page.
done -- extended the table from $0\leq n\leq 100$ to $0\leq n\leq 250`; checked the proposed range under `agents/sage.sh`, including the log-gamma term minimum at $n=228$ for about 100 digits and the $250/\log 10=108.57$ digit estimate.
done -- generated the 150 new entries with `publish(overwrite=False)` from a `numberdb.Generator`; checked all $B_n$ for $0\leq n\leq 250$ against the recurrence from $\sum_{k=0}^m {m+1\choose k}B_k=0$ before publishing.
done -- replaced the current `generate.sage` attachment with a package-style generator; checked it previews cleanly after the write and then `verify(sample=None)` reported `251/251 matched`.
declined -- left the zero entries without `equals` links to T0; the report's reason is right, and the zeros are useful as entries while links on every zero would add noise.
declined -- left the sign-convention comment as a comment; adding the $B_n^+$ convention as a parameter would duplicate the table for one changed row.
done -- linked `sums of powers` to `HREF{Sums_of_powers}`; checked the live audit finding, and the post-edit audit is clean.
done -- captioned the Bernoulli-polynomial link; checked the rendered page now shows "Bernoulli polynomial" as the link text rather than the bare slug.
done -- fixed "generating functon" to "generating function"; checked the live definition still had the typo before editing and not after.
declined -- left `both signs: True` alone; the report is right that `(Unknown key)` is the renderer's label-map fault, not a table-data fault.
done -- replaced the stale Sage program with `bernoulli(n)`; checked the rendered Programs block after the edit.
