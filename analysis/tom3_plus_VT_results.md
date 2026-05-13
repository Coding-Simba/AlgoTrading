# Tom3 + candidate portfolio combo analysis (NT8 own numbers)

Date range: 2019-01-02 .. 2026-05-12 (1699 days)  
Tom3 trades CSV: `\Mac\Home\Documents\Samir strategies\NinjaTrader tom3 trades 2019 till 2026.csv`  
VariableTrend trades CSV: (see --cand)  

## Per-strategy metrics (overlap period)

| Strategy | Net | PF | MaxDD | Ret/DD | Worst day | Worst week | Worst month | Active days | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $674,920 | 1.52 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$45,390 | 1046 | 57.3% |
| **VariableTrend** | $189,749 | 1.13 | -$46,082 | 4.12 | -$9,613 | -$16,450 | -$34,107 | 1509 | 45.7% |

## Pearson correlation matrix (daily P&L)

| | Tom3 | VariableTrend |
|---|---:|---:|
| **Tom3** | +1.000 | -0.006 |
| **VariableTrend** | -0.006 | +1.000 |

## Tom3 worst-20-day cushion

On Tom3's 20 worst days, what did each candidate contribute?

| Candidate | Sum | Avg/day | Pos days | Neg days |
|---|---:|---:|---:|---:|
| **VariableTrend** | $53,265 | $2,663 | 9 | 9 |

## Portfolio combos (Tom3 + each candidate subset, 1×each)

| Combo | Net | MaxDD | Ret/DD | Worst day | Worst week | Worst month | DD overlap days |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Tom3+VariableTrend** | $864,669 | -$58,524 | 14.77 | -$23,325 | -$42,737 | -$40,551 | 1189 |
| **Tom3** | $674,920 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$45,390 | 1275 |

## Per-strategy yearly P&L

| Strategy | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $16,320 | $95,085 | $18,875 | $146,925 | $22,320 | $95,215 | $126,535 | $153,645 |
| **VariableTrend** | -$9,156 | $18,143 | $54,714 | $78,370 | $6,579 | $13,316 | $9,447 | $18,335 |

## How to read this

- **Ret/DD**: net / |MaxDD|. Higher = better risk-adjusted return.
- **Worst day**: single biggest losing day across the period. For prop-firm survival this matters more than MaxDD.
- **DD overlap days**: number of days when EVERY strategy in the combo was simultaneously below its peak. Lower = better diversification of drawdown timing.
- **Tom3 worst-20 cushion**: if a candidate's `sum` is negative, it lost money on the days Tom3 needed help most — that's a red flag the average correlation misses.
- **Pairwise correlation < 0.15** is the usual rule of thumb for meaningful diversification; < 0.30 is acceptable.
