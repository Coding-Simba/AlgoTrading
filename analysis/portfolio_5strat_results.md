# Tom3 + candidate portfolio combo analysis (NT8 own numbers)

Date range: 2019-01-02 .. 2026-05-12 (1832 days)  
Tom3 trades CSV: `\Mac\Home\Documents\Samir strategies\NinjaTrader tom3 trades 2019 till 2026.csv`  
VariableTrend trades CSV: (see --cand)  
BlueLightning trades CSV: (see --cand)  
NQPivots trades CSV: (see --cand)  
MomentumNQ trades CSV: (see --cand)  

## Per-strategy metrics (overlap period)

| Strategy | Net | PF | MaxDD | Ret/DD | Worst day | Worst week | Worst month | Active days | Win rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $674,920 | 1.52 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$45,390 | 1046 | 57.3% |
| **VariableTrend** | $189,749 | 1.13 | -$46,082 | 4.12 | -$9,613 | -$16,450 | -$34,107 | 1509 | 45.7% |
| **BlueLightning** | $133,910 | 1.43 | -$16,905 | 7.92 | -$2,250 | -$4,390 | -$9,000 | 622 | 38.1% |
| **NQPivots** | $87,352 | 1.20 | -$19,731 | 4.43 | -$4,041 | -$8,081 | -$10,534 | 793 | 62.8% |
| **MomentumNQ** | -$3,877 | 0.90 | -$15,340 | -0.25 | -$541 | -$1,081 | -$1,892 | 159 | 6.9% |

## Pearson correlation matrix (daily P&L)

| | Tom3 | VariableTrend | BlueLightning | NQPivots | MomentumNQ |
|---|---:|---:|---:|---:|---:|
| **Tom3** | +1.000 | -0.006 | +0.106 | -0.043 | -0.048 |
| **VariableTrend** | -0.006 | +1.000 | +0.165 | -0.094 | -0.035 |
| **BlueLightning** | +0.106 | +0.165 | +1.000 | -0.063 | -0.046 |
| **NQPivots** | -0.043 | -0.094 | -0.063 | +1.000 | +0.047 |
| **MomentumNQ** | -0.048 | -0.035 | -0.046 | +0.047 | +1.000 |

## Tom3 worst-20-day cushion

On Tom3's 20 worst days, what did each candidate contribute?

| Candidate | Sum | Avg/day | Pos days | Neg days |
|---|---:|---:|---:|---:|
| **VariableTrend** | $53,265 | $2,663 | 9 | 9 |
| **BlueLightning** | -$5,250 | -$262 | 0 | 6 |
| **NQPivots** | $5,938 | $297 | 5 | 0 |
| **MomentumNQ** | -$270 | -$14 | 0 | 1 |

## Portfolio combos (Tom3 + each candidate subset, 1×each)

| Combo | Net | MaxDD | Ret/DD | Worst day | Worst week | Worst month | DD overlap days |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Tom3+VariableTrend+BlueLightning+NQPivots** | $1,085,931 | -$56,493 | 19.22 | -$23,325 | -$43,528 | -$44,455 | 934 |
| **Tom3+VariableTrend+BlueLightning+NQPivots+MomentumNQ** | $1,082,054 | -$57,845 | 18.71 | -$23,325 | -$43,799 | -$42,691 | 864 |
| **Tom3+VariableTrend+NQPivots** | $952,021 | -$56,348 | 16.90 | -$23,325 | -$42,778 | -$44,075 | 1106 |
| **Tom3+VariableTrend+NQPivots+MomentumNQ** | $948,144 | -$57,699 | 16.43 | -$23,325 | -$43,049 | -$42,311 | 1030 |
| **Tom3+VariableTrend+BlueLightning** | $998,579 | -$66,224 | 15.08 | -$23,325 | -$43,487 | -$37,504 | 1084 |
| **Tom3+VariableTrend** | $864,669 | -$58,524 | 14.77 | -$23,325 | -$42,737 | -$41,751 | 1273 |
| **Tom3+VariableTrend+BlueLightning+MomentumNQ** | $994,702 | -$67,576 | 14.72 | -$23,325 | -$43,758 | -$37,774 | 1011 |
| **Tom3+VariableTrend+MomentumNQ** | $860,792 | -$59,876 | 14.38 | -$23,325 | -$43,008 | -$42,292 | 1193 |
| **Tom3+BlueLightning+NQPivots** | $896,182 | -$64,638 | 13.86 | -$23,325 | -$38,751 | -$41,535 | 1009 |
| **Tom3+BlueLightning+NQPivots+MomentumNQ** | $892,304 | -$65,990 | 13.52 | -$23,325 | -$39,021 | -$42,616 | 937 |
| **Tom3+NQPivots** | $762,272 | -$59,188 | 12.88 | -$23,325 | -$38,001 | -$39,085 | 1192 |
| **Tom3+NQPivots+MomentumNQ** | $758,394 | -$60,540 | 12.53 | -$23,325 | -$38,271 | -$40,166 | 1114 |
| **Tom3+BlueLightning** | $808,830 | -$72,390 | 11.17 | -$23,325 | -$38,710 | -$47,840 | 1167 |
| **Tom3+BlueLightning+MomentumNQ** | $804,953 | -$73,742 | 10.92 | -$23,325 | -$38,980 | -$48,921 | 1092 |
| **Tom3** | $674,920 | -$66,940 | 10.08 | -$23,325 | -$37,960 | -$45,390 | 1368 |
| **Tom3+MomentumNQ** | $671,043 | -$68,292 | 9.83 | -$23,325 | -$38,230 | -$46,471 | 1285 |

## Per-strategy yearly P&L

| Strategy | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tom3** | $16,320 | $95,085 | $18,875 | $146,925 | $22,320 | $95,215 | $126,535 | $153,645 |
| **VariableTrend** | -$9,156 | $18,143 | $54,714 | $78,370 | $6,579 | $13,316 | $9,447 | $18,335 |
| **BlueLightning** | $9,200 | $18,900 | $17,420 | $44,845 | $2,510 | $36,930 | -$6,815 | $10,920 |
| **NQPivots** | -$5,126 | $27,763 | $7,900 | $24,277 | $17,151 | -$7,856 | $17,836 | $5,406 |
| **MomentumNQ** | -$541 | -$5,126 | -$2,182 | -$5,999 | $1,635 | $116 | $3,001 | $5,218 |

## How to read this

- **Ret/DD**: net / |MaxDD|. Higher = better risk-adjusted return.
- **Worst day**: single biggest losing day across the period. For prop-firm survival this matters more than MaxDD.
- **DD overlap days**: number of days when EVERY strategy in the combo was simultaneously below its peak. Lower = better diversification of drawdown timing.
- **Tom3 worst-20 cushion**: if a candidate's `sum` is negative, it lost money on the days Tom3 needed help most — that's a red flag the average correlation misses.
- **Pairwise correlation < 0.15** is the usual rule of thumb for meaningful diversification; < 0.30 is acceptable.
