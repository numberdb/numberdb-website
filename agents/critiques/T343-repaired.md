declined -- audit unit warning: nats and bits are one divergence in two logarithmic-unit conventions; I checked T339 and T340 use the same unit pattern, and the repaired definition says "two conventions for the same number".
done -- definition: replaced the name-for-name opening with the Radon-Nikodym integral definition and absolute-continuity condition; I checked the final audit so the shorter 306-character definition no longer raises the length warning.
done -- shape rule: added the shared-count convention for binomial and negative-binomial shapes and labelled normal parameters as location and scale; Sage checked all 676 live entries, including the shared shape encoding and normal row `0,1;0,2`.
done -- request link: removed the uncited `Request56` link after checking the live `Links` and prose contained no `CITE{Request56}`.
done -- normal omission comment: deleted the misleading equal-scale normal sentence and put the fixed-mean rationale in the completeness note; Sage checked every live normal shape has both means $0$ and distinct scales.
done -- completeness note: named the negative-binomial probability set, explained the small probability grids and the fixed normal means, and checked the generator ranges and live 676-entry block before changing it.
done -- third similar-table relation: rewrote the T340 relation as constrained-system capacity, a logarithmic growth rate, rather than a divergence between probability laws; I checked T340's live definition first.
done -- noted `complete: false`: changed the live data property to `no` and quoted `complete: 'no'` in the kept source so PyYAML will not turn it back into boolean false.
done -- noted "the first distribution": changed rigour details to say numerical expectations under $P$.
declined -- noted distribution labels: the report itself judged the divergence-style labels informative; I only fixed the normal label ambiguity that made the shape tuple unreadable.
declined -- noted named entry citations: this is a site resolver limitation inherited from the pattern, not a T343 table fault, and the critique already wrote the lesson proposal.
declined -- noted Shannon relation: the uniform-$Q$ identity is the mathematical relation between KL divergence and Shannon entropy even though no T343 row has uniform $Q$.
