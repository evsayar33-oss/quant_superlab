# H106 — Fixed cross-asset relative-strength hypothesis

A new signal source, **not** a variant of H103 trend/breakout. Uses BTC/ETH aligned native 1H USDT perpetual candles from H104. The fixed 24-hour BTC minus ETH close-return spread crosses +1 percentage point for BTC long or -1 percentage point for ETH long. Enter next bar open; 14-bar range ATR proxy, stop at 2x, target at 3x, maximum 48 hours, stop-first, non-overlapping positions per venue, 20/40/80bps assumed round-trip costs. No optimization, no synthetic candles. Source SHA-256 checked.

This is a directional winner-selection proxy, **not a market-neutral spread or hedged portfolio**. Historical tail is not prospective. Venue evidence is dependent. No funding, execution or multiplicity validation. No production/H089 changes and alpha_accepted remains false.

After PR checks pass, merge and dispatch H106 on main.
