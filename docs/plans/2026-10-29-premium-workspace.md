# Nivesh research workspace upgrade

## Intent
Turn the sparse search form into a coherent, premium analyst workspace while
preserving the tested fundamental calculations, data provenance, and public access.

## Implementation plan
1. Establish a restrained navy / teal identity using native Streamlit theme tokens,
   a persistent navigation rail, a useful research home, and one-click company entry.
2. Add bounded recent research, restore previously loaded companies without a provider
   call, and keep company / frequency context visible across workspace sections.
3. Put price history and coverage ahead of lengthy detail; add time-range controls,
   compact company context, and clear evidence-backed research cards.
4. Add a session-scoped research notebook with thesis, risks, next checks, and a
   downloadable Markdown snapshot. Explicitly disclose session-only retention.
5. Verify state transitions, notebook isolation/export, annual and quarterly research,
   comparison, refresh, errors, keyboard access, and narrow-screen layout.
6. Run the repository release checks before publishing. Push the tested commit to
   the existing main deployment branch, verify the remote SHA and live Streamlit UI.

## Acceptance
- No fabricated prices, performance, users, subscriptions, or real-time status.
- Existing formulas, provider semantics, demo disclosures, and downloads remain intact.
- No external account, authentication, billing, or shared private-note storage added.
- Release evidence distinguishes local tests, publication, and observed live behavior.
