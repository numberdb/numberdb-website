audit tag "functional analysis": declined -- the live tag page still lists T92, so the audit finding is the draft off-by-one described in the critique.
audit tag "inequality": declined -- the live tag page still lists T92, so the audit finding is the same false positive.
audit size: done -- kept the 1240 entries but rewrote the exception with a real range reason and measured 103-character longest value and 139,451-byte entries block.
1. done -- replaced the false 166-character and 262 KB measurements after recomputing 1240 entries, 103 maximum value characters, and 139,451 bytes with the server limit code.
2. done -- narrowed the range argument instead of deleting rows: n=20 is kept because T92 carries p=2 dual rows through n=20, and the denominator-at-most-4 grid covers integer, half, third, and quarter exponents without holes.
3. done -- removed the unreachable dry_run.py sentence from rigour details and kept the ball-arithmetic method plus the T92 duality check, which Sage verified for all shared p=2 rows.
4. done -- replaced the duplicate Frank-Lieb arXiv link with the Wikipedia Hardy-Littlewood-Sobolev lemma link, checked live at HTTP 200.
5. done -- rewrote the comment to define the general p,q condition, the diagonal specialization, and the least-constant convention; the p=q substitution was checked algebraically.
6. done -- rewrote the Similar tables relation as a sentence with the identity C_{n,n-2}=1/(A_nS_{n,2}^2); Sage checked it against T92 in every shared p=2 dimension.
7. done -- added print(C) to the Sage program and checked the example overlaps the stored n=3, lambda=3/2 interval.
8. declined -- no table change: Keywords already carry both the hyphenated and en-dash spellings.
9. declined -- the rendered "(Unknown key)" is the site label for the valid Size exception key, not table data.
