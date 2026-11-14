# H109 — Negative-control diagnostic for rejected H106 signal

Fixed-seed sign-flip null applied to the already-rejected H106 strategy's SHA-256-verified realized trade gross R, preserving the per-trade assumed 20 bps cost. Descriptive null distribution and tail ranks across OKX/Gate. This does not search for a better parameter or imply reversing the strategy would be profitable.

This sign-flip experiment is **not a causal counterfactual**: stop/target path dependence makes reversed trades different. Trade sign flips ignore serial dependence and cross-venue correlation. No production/H089 changes, no alpha approval.

Merge only after CI and H109 evidence pass, then dispatch H109 on main.
