1. *done* -- the dead-link part was already fixed before I edited: unauthenticated `/T327` returned 200 and keyed `/api/table/T331/audit` was clean; I kept the link and changed the relation from "these gallery families" to "the test matrix families listed here".
2. *done* -- added the Sage 0-based-indexing comment to the program; I checked under `agents/sage.sh` that the stored snippet returns `1/2160` and that the 1-based formula copied into the Sage lambda raises `ZeroDivisionError`.
3. *done* -- defined $M$ as the Mertens function in the Redheffer formula and cited the existing Pascal and Redheffer links; I checked the live document had both links declared but uncited and no definition of $M$.
4. *done* -- rewrote `rigour details` so the exact Bareiss computation and independent checks appear first, and removed the repository file name and storage-size measurements; I checked the keyed audit after the edit was clean.
5. *done* -- changed the `family` constraint to "one of the named test matrix families defined in the comments"; I checked the edit left the parameter keys and their order unchanged.
6. *done* -- added the Cauchy, Parter and Ris substitutions to the Cauchy determinant identity; I checked all 87 affected rows for $2\leq n\leq30$ under `agents/sage.sh`.
7. *left for a person* -- `matrix` does not exist as a tag, and adding it only to T331 would create a one-table tag; I checked `/api/tag?url=matrix` and left the cross-table T327/T329/T330/T331 tag decision alone.
8. *done* -- removed the website-search apology from the omitted-families comment and put the range reason in `complete-note`; I checked the keyed audit after the edit was clean.
9. *done* -- added T329 to `Similar tables`; I checked unauthenticated `/T329` returned 200.
10. *done* -- defined the Kac-Murdock-Szegő parameter by writing $A_{ij}=\rho^{|i-j|}$ with $\rho=1/2$ before the specialized formula uses $\rho$.
11. *done* -- added "Kac-Murdock-Szegő matrix" to `Keywords` and used the accented display label; I checked the keyed API read back both accented and unaccented keywords.
12. *done* -- defined "classical test matrix" in the definition with the existing MathWorks gallery citation and stated that the toolbox families use `gallery`'s default parameters.
