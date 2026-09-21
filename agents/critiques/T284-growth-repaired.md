<<<<<<< HEAD
* declined -- The current range is not stopped early: I checked the live API and rendered page still show "Salem numbers less than 1.3" with 47 entries, and `agents/sage.sh generators/salem-numbers-less-than-1.3/generate.py` verified 47/47 values, so I did not add entries under the 1.3 title.
* done -- Added a cited comment explaining why the 1.3 cutoff is traditional and mathematically close to the plastic-constant accumulation point; I checked Sac-Épée §1.3 before writing it.
* left for a person -- I did not retitle or extend T284 to 49/37, because the critique says that is a person's call and it must be decided together with T301.
* done -- Updated and attached T284's `generate.py` so `entry_comment()` reproduces the five Coxeter-triangle comments and four Mossinghoff-discovery comments already on the live table; I checked 47/47 values with `verify(sample=None)` and checked all 47 generated comments against the live API with `/tmp/check_t284_comments.py`.
* left for a person -- Sac-Épée's rounded decimals versus Mossinghoff's truncated decimals matter only for a 49/37 extension, so I did not change the current 1.3 generator's source-decimal convention.
* left for a person -- The permanent slug/title mismatch risk belongs to the 49/37 retitle decision, so I made no title or slug-related edit.
* left for a person -- The T301 lockstep requirement belongs to the same 49/37 decision, so I did not edit T301.
* left for a person -- Keeping the classical 47 visible is a requirement for a future extended completeness note; the current table already names the 47 as its whole range.
* declined -- I did not use Mossinghoff's fixed-degree lists as growth, because the critique identifies them as a different family bounded by degree rather than by value.
* declined -- I left the praised completeness note and rigour details otherwise alone; after the edits, `GET /api/table/T284/audit` returned `{"findings": [], "clean": true}`.
=======
1. already fixed -- the live API document and rendered page now have `comment-bound`, explaining that Salem numbers below $1.3$ are called small and that the cutoff lies below the plastic-constant accumulation point; I checked the Sac-Epee paper for the terminology and ran Sage/PARI checks that the live table still has 47 irreducible reciprocal-polynomial entries below $1.3$, with the plastic root at about $1.324717957$.
2. declined -- the range has not moved, so the generator still only needs the Mossinghoff truncation check; no Sac-Epee rounded rows are being added, and the authenticated audit is clean.
3. left for a person -- a separate table indexed by degree would be a new table-design decision, not a repair to T284, so I did not create it.
4. declined -- the noted-only items require no table edit: the degree-$46$ caveat remains in `complete-note`, the table still has 47 entries below $1.3$, and `GET /api/table/T284/audit` returned `findings: []` and `clean: true`.
>>>>>>> origin/campaign/w3
