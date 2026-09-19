done -- the live table had already raised the conductor-norm bound to $250$ for $D\in\{5,8,12,13,17\}$; I added the next field, $D=21$, by running a generator against pinned ecnf-data, bringing the table from 823 to 1171 entries.
already fixed -- the live API and rendered page already included $D=5$ and $D=8$ rows and the comment recording their first positive-rank conductor norms, $199$ and $103$.
done -- the generator reads ecnf-data directly at commit `10b28418e80392032b106ea00e6c5aa109d28e7b`, uses `publish(overwrite=False)`, and left the existing 823 entries untouched.
done -- the 35-significant-digit convention was checked against every pre-existing row before adding D=21 and used for all new D=21 regulators.
done -- the D=21 extension includes the rank-2 rows; I checked the eight rank-2 source regulators in Sage by recomputing the height-pairing determinant from the recorded equations and generators, and updated the rigour note.
done -- the generator checks the BSD quotient against the recorded analytic order of Sha for every generated row; after the repair, `verify(sample=None)` reported `1171/1171 matched`.
done -- the table remains under the 1200-entry soft limit at 1171 entries, and `GET /api/table/T293/audit` returned `clean: true`.
left for a person -- adding $D=24$ and later fields at the same norm bound would require a size/range decision, since $D=24$ alone would raise the table to 1748 entries, above the soft limit.
