"""BTC 24h-ahead forecast entry for make.fun competition btc-cent-forecast-01.

Method
------
Forecast the BTC/USDC price 240 minutes ahead of the case checkpoint:

    forecast = last_close * exp(total_log_adj)

where total_log_adj is clamped to +/-0.015 (log) and the result is rounded
to a 5-decimal grid and clamped into (0, 10,000,000).

    total_log_adj = drift_adj + hour_adj

* drift_adj: the mean log return per minute over the 72h window of 4320
  one-minute closes, shrunk by 0.15 and projected 240 minutes forward:

      drift_adj = 0.15 * ((log(last) - log(first)) / (len(prices) - 1)) * 240

  Only finite, positive prices enter the log computation: a non-finite
  price (e.g. inf) would otherwise pass a plain `p > 0` check and
  math.log(inf) would poison the forecast.

* hour_adj: 0.5 * HOUR_MEAN[UTC hour of the checkpoint "at"], where
  HOUR_MEAN is the shrunk mean 4h log return starting at each UTC hour,
  fitted on 60 days of public BTC closes (Binance BTCUSDT 1m,
  2026-09-15 to 2026-11-14, with a +10 prior on each hour mean).
  The profile is coherent: negative overnight UTC (22:00-02:00),
  positive in the UTC morning (03:00-08:00), slightly negative in the
  UTC afternoon. The shrinkage factor 0.5 is applied because the raw
  hour effect is only ~1 sigma once the true standard error (~60
  independent observations per hour) is taken into account.

Fitted constants (HOUR_MEAN, shrunk mean 4h log return by UTC hour):
    0: -0.0016595,  1: -0.00076591, 2: -0.00006556, 3:  0.00053048,
    4:  0.00082576, 5:  0.00083813, 6:  0.00113379, 7:  0.00125744,
    8:  0.00070841, 9: -0.00040954, 10: -0.00056205, 11: -0.00119602,
    12: -0.00121788, 13: -0.00080906, 14: -0.00056953, 15: -0.00049477,
    16: -0.00013386, 17: -0.00027797, 18: -0.00047886, 19: -0.00034531,
    20: -0.00077086, 21: -0.00078078, 22: -0.00154675, 23: -0.00198345

Backtest (honest numbers)
-------------------------
Practice kit, 5 cases p00-p04 with exact answers derived from the
overlapping windows (the next case's checkpoint close is this case's
+240min actual), Orca cbBTC/USDC prices:

    model (drift lambda 0.15 + hour shrinkage 0.5): MAE 46.189 cents
    persistence (forecast = checkpoint close):     MAE 47.055 cents
    ratio: 98.16% of persistence

On 341 hour-aligned Binance cases over 60 days the same model scored
41.101 cents vs 41.221 cents for persistence (99.71%). The edge over
persistence is thin (~1-2% MAE) and the final 12-case score will be
dominated by luck; no stronger claim is made.

I/O: reads <id>.in files from MAKEFUN_INPUT_DIR (default /input), writes
<id>.out to MAKEFUN_OUTPUT_DIR (default /output). Case JSON schema
makefun/btc-cent-case/v1. Output is exactly one line:
{"forecasts": [{"case": <id>, "price": <number>}]}

Python standard library only (json, math, os, datetime). Deterministic,
no network access, ~0.04 s per case.
"""

import json
import math
import os
from datetime import datetime

# Shrunk mean 4h log return starting at each UTC hour (see docstring).
HOUR_MEAN = {
    0: -0.0016595,
    1: -0.00076591,
    2: -0.00006556,
    3: 0.00053048,
    4: 0.00082576,
    5: 0.00083813,
    6: 0.00113379,
    7: 0.00125744,
    8: 0.00070841,
    9: -0.00040954,
    10: -0.00056205,
    11: -0.00119602,
    12: -0.00121788,
    13: -0.00080906,
    14: -0.00056953,
    15: -0.00049477,
    16: -0.00013386,
    17: -0.00027797,
    18: -0.00047886,
    19: -0.00034531,
    20: -0.00077086,
    21: -0.00078078,
    22: -0.00154675,
    23: -0.00198345,
}

DRIFT_SHRINKAGE = 0.15
HOUR_SHRINKAGE = 0.5
HORIZON_MINUTES = 240
MAX_LOG_ADJ = 0.015
MAX_PRICE = 10000000.0


def forecast_price(case):
    """Forecast the BTC/USDC price 240 minutes after the checkpoint."""
    prices = case["markets"][0]["prices"]
    last = prices[-1]
    # Only finite, positive prices enter the log computation: inf passes
    # a plain `p > 0` check, and math.log(inf) would poison the forecast.
    logs = [math.log(p) for p in prices if p > 0 and math.isfinite(p)]
    first_log = logs[0]
    last_log = logs[-1]
    n = len(logs)

    # Mean log return per minute over the 72h window, shrunk x0.15,
    # projected 240 minutes forward.
    drift_adj = (
        DRIFT_SHRINKAGE
        * ((last_log - first_log) / (n - 1))
        * HORIZON_MINUTES
    )

    # UTC hour of the checkpoint, half-strength seasonality.
    at = datetime.fromisoformat(case["at"].replace("Z", "+00:00"))
    hour_adj = HOUR_SHRINKAGE * HOUR_MEAN[at.hour]

    total_adj = drift_adj + hour_adj
    total_adj = max(-MAX_LOG_ADJ, min(MAX_LOG_ADJ, total_adj))

    price = last * math.exp(total_adj)
    # Round to a 5-decimal grid and clamp into (0, 10,000,000).
    price = round(price, 5)
    price = max(0.00001, min(9999999.99999, price))
    return price


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    for name in sorted(os.listdir(input_dir)):
        if not name.endswith(".in"):
            continue
        case_id = name[:-3]
        with open(os.path.join(input_dir, name), "r", encoding="utf-8") as f:
            case = json.load(f)
        price = forecast_price(case)
        out = {"forecasts": [{"case": case["case"], "price": price}]}
        with open(
            os.path.join(output_dir, case_id + ".out"), "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
