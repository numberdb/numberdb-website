done -- moved the Dynkin-label and Bourbaki-numbering rule into the `weight` parameter; checked the live API document and rendered preview still had the convention only below the parameter block.
done -- rewrote the fundamental representation dimension lists in `rigour details` in Bourbaki node order; checked the five lists with `agents/sage.sh /tmp/check_t256_fundamental_dims.py`.
done -- shortened the `classical-types` comment to the scope fact; checked the rendered preview no longer contained the advice sentence.
done -- bound $V_{\mathfrak g}(\lambda)$ in the Definition and made the remaining notation explicit in the Weyl formula, completeness note and $E_8$ example; checked rendered previews and the final audit.
declined -- T233 and T243 were checked live and do share the same exceptional root-system names, but their relation is only a shared indexing family rather than representation dimensions, so adding both would dilute `Similar tables`.
declined -- reproduced the `sage -python` failure with `agents/sage.sh /tmp/t256_program_snippet.py`, but the program is labelled `Sage` and the issue is corpus-wide snippet environment guidance rather than a T256 table fault.
