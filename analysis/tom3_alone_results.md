# Tom3 + candidate portfolio combo analysis (NT8 own numbers)

Date range: 2019-01-02 .. 2026-05-12 (1048 days)  
Tom3 trades CSV: `\Mac\Home\Documents\Samir strategies\NinjaTrader tom3 trades 2019 till 2026.csv`  

## Per-strategy metrics (overlap period)

| Strategy | Net | PF | MaxDD | Ret/DD | Worst day | Worst week | Worst month | Active days | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $674,920 | 1.52 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$51,655 | 1046 | 57.3% |

## Pearson correlation matrix (daily P&L)

| | Tom3 |
|---|---:|
| **Tom3** | +1.000 |

## Portfolio combos (Tom3 + each candidate subset, 1×each)

| Combo | Net | MaxDD | Ret/DD | Worst day | Worst week | Worst month | DD overlap days |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $674,920 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$51,655 | 822 |

## Per-strategy yearly P&L

| Strategy | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $16,320 | $95,085 | $18,875 | $146,925 | $22,320 | $95,215 | $126,535 | $153,645 |

## How to read this

- **Ret/DD**: net / |MaxDD|. Higher = better risk-adjusted return.
- **Worst day**: single biggest losing day across the period. For prop-firm survival this matters more than MaxDD.
- **DD overlap days**: number of days when EVERY strategy in the combo was simultaneously below its peak. Lower = better diversification of drawdown timing.
- **Tom3 worst-20 cushion**: if a candidate's `sum` is negative, it lost money on the days Tom3 needed help most — that's a red flag the average correlation misses.
- **Pairwise correlation < 0.15** is the usual rule of thumb for meaningful diversification; < 0.30 is acceptable.
