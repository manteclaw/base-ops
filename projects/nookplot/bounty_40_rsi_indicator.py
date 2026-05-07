#!/usr/bin/env python3
"""
rsi_divergence_indicator.py — Bounty #40 Deliverable
Production-grade RSI divergence detector with reproducible backtest.

Detects:
  • Regular Bullish Divergence (price lower low, RSI higher low)
  • Regular Bearish Divergence (price higher high, RSI lower high)
  • Hidden Bullish Divergence (price higher low, RSI lower low)
  • Hidden Bearish Divergence (price lower high, RSI higher high)

Backtest: entry on divergence confirmation, exit on opposite signal or trailing stop.

Usage:
    python3 rsi_divergence_indicator.py --symbol BTC-USD --period 365 --plot
    python3 rsi_divergence_indicator.py --symbol ETH-USD --period 180

Requirements:
    pip install yfinance pandas numpy matplotlib

Author: Manteclaw (Agent ID: 3fbc58ec-1236-41d8-83a3-557f342adc3b)
License: MIT
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd

# ─── CONFIG ─────────────────────────────────────────────────────────

RSI_PERIOD = 14
MIN_SWING_PTS = 5      # Minimum bars between swing points
DIVERGENCE_LOOKBACK = 5 # Bars to look back for divergence
MIN_RSI_DIFF = 5       # Minimum RSI point difference for divergence
TRAILING_STOP_PCT = 0.03  # 3% trailing stop


# ─── DATA ─────────────────────────────────────────────────────────────

def fetch_data(symbol: str, days: int) -> pd.DataFrame:
    """Fetch OHLCV. Try yfinance first, fallback to sample data."""
    try:
        import yfinance as yf
        print(f"📊 Fetching {symbol} data for last {days} days...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d", interval="1d")
        df = df.dropna()
        print(f"  → {len(df)} bars loaded from Yahoo Finance")
        return df
    except ImportError:
        print("⚠️ yfinance not installed. Generating synthetic BTC-like data for demo...")
        return generate_sample_data(days)


def generate_sample_data(days: int) -> pd.DataFrame:
    """Generate synthetic price data for backtesting demo."""
    np.random.seed(42)
    n = days
    
    # Generate random walk with trend
    returns = np.random.normal(0.001, 0.03, n)
    price = 30000 * np.exp(np.cumsum(returns))
    
    # Add OHLC
    high = price * (1 + np.random.uniform(0, 0.02, n))
    low = price * (1 - np.random.uniform(0, 0.02, n))
    open_price = price * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.uniform(1e9, 5e9, n)
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n, freq="D")
    df = pd.DataFrame({
        "Open": open_price,
        "High": high,
        "Low": low,
        "Close": price,
        "Volume": volume,
    }, index=dates)
    
    print(f"  → {len(df)} synthetic bars generated")
    return df


# ─── RSI ──────────────────────────────────────────────────────────────

def compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ─── SWING POINTS ─────────────────────────────────────────────────────

def find_swing_points(series: pd.Series, min_bars: int = MIN_SWING_PTS) -> Tuple[List[int], List[int]]:
    """Find local highs and lows using a rolling window."""
    highs = []
    lows = []
    
    for i in range(min_bars, len(series) - min_bars):
        window = series.iloc[i - min_bars:i + min_bars + 1]
        center = series.iloc[i]
        
        if center == window.max() and center > series.iloc[i-1] and center > series.iloc[i+1]:
            highs.append(i)
        elif center == window.min() and center < series.iloc[i-1] and center < series.iloc[i+1]:
            lows.append(i)
    
    return highs, lows


# ─── DIVERGENCE DETECTION ───────────────────────────────────────────────

@dataclass
class Divergence:
    type: str           # "regular_bullish", "regular_bearish", "hidden_bullish", "hidden_bearish"
    idx1: int           # Earlier swing point
    idx2: int           # Later swing point
    price1: float
    price2: float
    rsi1: float
    rsi2: float
    confirmed: bool = False


def detect_divergences(df: pd.DataFrame) -> List[Divergence]:
    """Detect all four divergence types."""
    close = df["Close"].values
    rsi = df["RSI"].values
    
    price_highs, price_lows = find_swing_points(pd.Series(close))
    rsi_highs, rsi_lows = find_swing_points(pd.Series(rsi))
    
    divs = []
    
    # Regular Bullish: price lower low, RSI higher low
    for i in range(1, len(price_lows)):
        idx1, idx2 = price_lows[i-1], price_lows[i]
        if close[idx2] < close[idx1] and rsi[idx2] > rsi[idx1] + MIN_RSI_DIFF:
            divs.append(Divergence(
                type="regular_bullish",
                idx1=idx1, idx2=idx2,
                price1=close[idx1], price2=close[idx2],
                rsi1=rsi[idx1], rsi2=rsi[idx2],
            ))
    
    # Regular Bearish: price higher high, RSI lower high
    for i in range(1, len(price_highs)):
        idx1, idx2 = price_highs[i-1], price_highs[i]
        if close[idx2] > close[idx1] and rsi[idx2] < rsi[idx1] - MIN_RSI_DIFF:
            divs.append(Divergence(
                type="regular_bearish",
                idx1=idx1, idx2=idx2,
                price1=close[idx1], price2=close[idx2],
                rsi1=rsi[idx1], rsi2=rsi[idx2],
            ))
    
    # Hidden Bullish: price higher low, RSI lower low
    for i in range(1, len(price_lows)):
        idx1, idx2 = price_lows[i-1], price_lows[i]
        if close[idx2] > close[idx1] and rsi[idx2] < rsi[idx1] - MIN_RSI_DIFF:
            divs.append(Divergence(
                type="hidden_bullish",
                idx1=idx1, idx2=idx2,
                price1=close[idx1], price2=close[idx2],
                rsi1=rsi[idx1], rsi2=rsi[idx2],
            ))
    
    # Hidden Bearish: price lower high, RSI higher high
    for i in range(1, len(price_highs)):
        idx1, idx2 = price_highs[i-1], price_highs[i]
        if close[idx2] < close[idx1] and rsi[idx2] > rsi[idx1] + MIN_RSI_DIFF:
            divs.append(Divergence(
                type="hidden_bearish",
                idx1=idx1, idx2=idx2,
                price1=close[idx1], price2=close[idx2],
                rsi1=rsi[idx1], rsi2=rsi[idx2],
            ))
    
    return divs


# ─── BACKTEST ───────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    direction: str   # "long" or "short"
    exit_idx: Optional[int] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: Optional[str] = None


def backtest(df: pd.DataFrame, divs: List[Divergence]) -> Tuple[List[Trade], dict]:
    """Simple backtest: enter on divergence, exit on opposite signal or trailing stop."""
    close = df["Close"].values
    trades: List[Trade] = []
    active_trade: Optional[Trade] = None
    
    for i in range(len(df)):
        # Check for new divergence at this bar
        new_div = None
        for d in divs:
            if d.idx2 == i and not d.confirmed:
                d.confirmed = True
                new_div = d
                break
        
        # Enter trade
        if new_div and not active_trade:
            if "bullish" in new_div.type:
                active_trade = Trade(
                    entry_idx=i,
                    entry_price=close[i],
                    direction="long"
                )
            elif "bearish" in new_div.type:
                active_trade = Trade(
                    entry_idx=i,
                    entry_price=close[i],
                    direction="short"
                )
        
        # Manage active trade
        if active_trade:
            # Check trailing stop
            if active_trade.direction == "long":
                max_price = close[active_trade.entry_idx:i+1].max()
                stop_level = max_price * (1 - TRAILING_STOP_PCT)
                if close[i] <= stop_level:
                    active_trade.exit_idx = i
                    active_trade.exit_price = close[i]
                    active_trade.pnl_pct = (close[i] / active_trade.entry_price - 1) * 100
                    active_trade.exit_reason = "trailing_stop"
                    trades.append(active_trade)
                    active_trade = None
                    continue
                
                # Check opposite signal
                for d in divs:
                    if d.idx2 == i and "bearish" in d.type:
                        active_trade.exit_idx = i
                        active_trade.exit_price = close[i]
                        active_trade.pnl_pct = (close[i] / active_trade.entry_price - 1) * 100
                        active_trade.exit_reason = "opposite_signal"
                        trades.append(active_trade)
                        active_trade = None
                        break
            
            elif active_trade.direction == "short":
                min_price = close[active_trade.entry_idx:i+1].min()
                stop_level = min_price * (1 + TRAILING_STOP_PCT)
                if close[i] >= stop_level:
                    active_trade.exit_idx = i
                    active_trade.exit_price = close[i]
                    active_trade.pnl_pct = (active_trade.entry_price / close[i] - 1) * 100
                    active_trade.exit_reason = "trailing_stop"
                    trades.append(active_trade)
                    active_trade = None
                    continue
                
                # Check opposite signal
                for d in divs:
                    if d.idx2 == i and "bullish" in d.type:
                        active_trade.exit_idx = i
                        active_trade.exit_price = close[i]
                        active_trade.pnl_pct = (active_trade.entry_price / close[i] - 1) * 100
                        active_trade.exit_reason = "opposite_signal"
                        trades.append(active_trade)
                        active_trade = None
                        break
    
    # Close any open trade at end
    if active_trade:
        active_trade.exit_idx = len(df) - 1
        active_trade.exit_price = close[-1]
        if active_trade.direction == "long":
            active_trade.pnl_pct = (close[-1] / active_trade.entry_price - 1) * 100
        else:
            active_trade.pnl_pct = (active_trade.entry_price / close[-1] - 1) * 100
        active_trade.exit_reason = "end_of_data"
        trades.append(active_trade)
    
    # Compute metrics
    if not trades:
        return [], {}
    
    pnls = [t.pnl_pct for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)
    
    cumulative = 1.0
    peak = 1.0
    max_dd = 0.0
    for p in pnls:
        cumulative *= (1 + p / 100)
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / peak
        if dd > max_dd:
            max_dd = dd
    
    metrics = {
        "total_trades": len(trades),
        "win_rate": wins / len(trades) * 100,
        "wins": wins,
        "losses": losses,
        "avg_return": np.mean(pnls),
        "median_return": np.median(pnls),
        "max_return": max(pnls),
        "min_return": min(pnls),
        "total_return_pct": (cumulative - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
        "sharpe_approx": np.mean(pnls) / (np.std(pnls) + 1e-9) * np.sqrt(252 / len(trades)) if len(trades) > 1 else 0,
    }
    
    return trades, metrics


# ─── PLOT ───────────────────────────────────────────────────────────────

def plot_results(df: pd.DataFrame, divs: List[Divergence], trades: List[Trade], symbol: str):
    """Plot price, RSI, divergences, and trades."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("❌ matplotlib not installed. Run: pip install matplotlib")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1]})
    
    dates = df.index
    close = df["Close"].values
    rsi = df["RSI"].values
    
    # Price chart
    ax1.plot(dates, close, label="Close", color="black", linewidth=1)
    
    # Mark divergences
    colors = {
        "regular_bullish": "green",
        "regular_bearish": "red",
        "hidden_bullish": "lime",
        "hidden_bearish": "orange",
    }
    labels = {
        "regular_bullish": "Regular Bullish",
        "regular_bearish": "Regular Bearish",
        "hidden_bullish": "Hidden Bullish",
        "hidden_bearish": "Hidden Bearish",
    }
    
    for d in divs:
        if d.type in colors:
            ax1.plot([dates[d.idx1], dates[d.idx2]], [d.price1, d.price2],
                    color=colors[d.type], linestyle="--", alpha=0.7,
                    label=labels[d.type] if d == divs[0] else "")
            ax1.scatter([dates[d.idx1], dates[d.idx2]], [d.price1, d.price2],
                       color=colors[d.type], s=50, zorder=5)
    
    # Mark trades
    for t in trades:
        color = "green" if t.pnl_pct > 0 else "red"
        ax1.scatter(dates[t.entry_idx], t.entry_price, marker="^" if t.direction == "long" else "v",
                   color="blue", s=100, zorder=5)
        if t.exit_idx:
            ax1.scatter(dates[t.exit_idx], t.exit_price, marker="x",
                       color=color, s=100, zorder=5)
    
    ax1.set_title(f"RSI Divergence Analysis — {symbol}")
    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)
    
    # RSI chart
    ax2.plot(dates, rsi, label="RSI(14)", color="blue", linewidth=1)
    ax2.axhline(70, color="red", linestyle="--", alpha=0.5, label="Overbought (70)")
    ax2.axhline(30, color="green", linestyle="--", alpha=0.5, label="Oversold (30)")
    ax2.fill_between(dates, 30, 70, alpha=0.05, color="gray")
    
    for d in divs:
        if d.type in colors:
            ax2.plot([dates[d.idx1], dates[d.idx2]], [d.rsi1, d.rsi2],
                    color=colors[d.type], linestyle="--", alpha=0.7)
            ax2.scatter([dates[d.idx1], dates[d.idx2]], [d.rsi1, d.rsi2],
                       color=colors[d.type], s=50, zorder=5)
    
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"/root/.openclaw/workspace/projects/nookplot/rsi_divergence_{symbol.replace('-', '_')}.png", dpi=150)
    print(f"📈 Chart saved: rsi_divergence_{symbol.replace('-', '_')}.png")
    plt.close()


# ─── REPORT ────────────────────────────────────────────────────────────

def print_report(symbol: str, divs: List[Divergence], trades: List[Trade], metrics: dict):
    print(f"\n{'='*70}")
    print(f"  RSI DIVERGENCE BACKTEST REPORT — {symbol}")
    print(f"{'='*70}")
    print(f"  Divergences found: {len(divs)}")
    
    by_type = {}
    for d in divs:
        by_type[d.type] = by_type.get(d.type, 0) + 1
    for t, c in sorted(by_type.items()):
        print(f"    {t.replace('_', ' ').title()}: {c}")
    
    print(f"\n  Trades executed: {metrics['total_trades']}")
    print(f"  Win rate: {metrics['win_rate']:.1f}% ({metrics['wins']} wins / {metrics['losses']} losses)")
    print(f"  Avg return: {metrics['avg_return']:.2f}%")
    print(f"  Median return: {metrics['median_return']:.2f}%")
    print(f"  Best trade: +{metrics['max_return']:.2f}%")
    print(f"  Worst trade: {metrics['min_return']:.2f}%")
    print(f"  Total return: {metrics['total_return_pct']:.2f}%")
    print(f"  Max drawdown: {metrics['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe (approx): {metrics['sharpe_approx']:.2f}")
    print(f"{'='*70}\n")


# ─── MAIN ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RSI Divergence Indicator + Backtest")
    parser.add_argument("--symbol", default="BTC-USD", help="Yahoo Finance symbol (default: BTC-USD)")
    parser.add_argument("--period", type=int, default=365, help="Days of history (default: 365)")
    parser.add_argument("--plot", action="store_true", help="Generate chart PNG")
    parser.add_argument("--json", action="store_true", help="Output metrics as JSON")
    args = parser.parse_args()
    
    # Fetch
    df = fetch_data(args.symbol, args.period)
    
    # Compute RSI
    df["RSI"] = compute_rsi(df["Close"])
    df = df.dropna()
    
    # Detect divergences
    divs = detect_divergences(df)
    
    # Backtest
    trades, metrics = backtest(df, divs)
    
    # Report
    print_report(args.symbol, divs, trades, metrics)
    
    # Plot
    if args.plot:
        plot_results(df, divs, trades, args.symbol)
    
    # JSON output
    if args.json:
        output = {
            "symbol": args.symbol,
            "period_days": args.period,
            "bars": len(df),
            "divergences": len(divs),
            "divergence_breakdown": {t: sum(1 for d in divs if d.type == t) for t in set(d.type for d in divs)},
            "trades": len(trades),
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        print(json.dumps(output, indent=2))
    
    return metrics


if __name__ == "__main__":
    metrics = main()
    sys.exit(0 if metrics.get("total_trades", 0) > 0 else 1)
