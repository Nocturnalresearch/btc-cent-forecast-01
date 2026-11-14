# btc-cent-forecast-01 — BTC 4-hour-ahead price forecast

Entry for make.fun's `btc-cent-forecast-01` competition: forecast Bitcoin's
price 240 minutes ahead, 12 times over 48 hours.

`main.py` (Python standard library only, offline, deterministic) reads one
case file (`<id>.in`: 4,320 one-minute BTC/USDC closes over the 72 hours
ending at the checkpoint) and writes one forecast (`<id>.out`) for the
close 240 minutes later.

Method: forecast = last close × exp(shrunk 72h drift + shrunk
intraday-seasonality adjustment), with the total log adjustment clamped to
±1.5% and the result rounded to the 5-decimal price grid. The drift is the
mean log return per minute over the 72h window, shrunk by 0.15 and
projected 240 minutes; the seasonality is the shrunk mean 4h log return
starting at the checkpoint's UTC hour, applied at half strength. See
`main.py`'s docstring for the fitted constants.

Backtest (honest numbers): on the 5 practice cases with exact answers
(derived from the overlapping case windows), the model scores MAE 46.189
cents vs 47.055 cents for persistence (98.16% of persistence). On 341
hour-aligned historical Binance cases it scored 41.101 vs 41.221 cents
(99.71%). The edge over the house persistence baseline is thin (~1–2%
MAE) and the final 12-case score will be dominated by luck; no stronger
claim is made.

## License

MIT — see `LICENSE`.
