done -- rewrote the coefficient rule to say pairs of consecutive ones are counted with overlaps; checked the stored rows against that rule and checked that the non-overlapping reading diverges from $n=3$ onward in Sage.
done -- changed the Definition to name the Shapiro/Rudin-Shapiro pair $P_n,Q_n$ and say this table holds $P_n$, and added $Q_n(x)=(-1)^nx^{2^n-1}P_n(-1/x)$; checked stored rows and the $Q_n$ recovery through $n=10$ in Sage.
done -- removed the empty $P_0(-1)$ exception from the specialisations formula; checked $P_n(1)$ and $P_n(-1)$ through $n=10$ in Sage.
done -- changed the Programs exponentiation from `^` to `**`; checked the repaired block runs as a script and returns $P_8$ in Sage.
done -- removed the comment sentence that put the complementary identity on the unit circle; checked the complementary polynomial identity through $n=10$ in Sage.
done -- expanded `complete-note` to explain the stop before about two thousand printed characters; checked the printed lengths $P_7=907$, $P_8=1932$, $P_9=3979$, and $P_{10}=8100$ in Sage.
