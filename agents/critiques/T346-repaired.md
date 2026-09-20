1. done - changed the title of parameter `k` to `index of the root of $F_{E,n}(x)$`; checked the live table still used `root number` for that parameter and that the final audit is clean.
2. already fixed - the live table and repaired generator no longer write `+ i * [0, 0]`; Sage counted zero such values and the attached generator verified `588/588 matched`.
3. done - rewrote the definition to introduce $P$ and say `root numbered $k$`; checked the rendered page has no MathJax error and the final audit is clean.
4. done - removed the uncited `RequestedIn10` link; checked it was still present and uncited in the live document before editing.
5. done - added the torsion-inclusion comment; Sage checked that all 63 stored $2$-torsion $x$-coordinates reappear under $n=4$ across the 21 curves.
6. done - expanded the completeness note with the range size and torsion coverage; Sage checked $N\leq17$ gives 21 curves, 588 entries, and rational torsion subgroup orders 1, 2, 4, 5, 6 and 8.
7. done - updated the Sage program to name the example curve and sort roots by the table's order; Sage ran the replacement snippet and got the expected 12 roots for 11a1 at $n=5$.
8. done - removed the trailing `represented in $\overline{\mathbb{Q}}$` clause from the order comment; Sage checked all 84 generated root groups are in the stated order.
9. done - moved the model-recovery convention into `comment-model` rather than the definition after the audit objected to a definition link; the final audit is clean.
10. declined - the PARI-convention contradiction belongs to the companion division-polynomial table, not T346; Sage checked T346's degrees and generator verification matched all 588 stored values.
11. declined - this is a site/private-draft file-visibility issue rather than a T346 table-document repair, and the current live T346 page and generator are public.
