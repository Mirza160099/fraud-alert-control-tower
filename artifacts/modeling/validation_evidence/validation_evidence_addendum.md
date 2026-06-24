# Validation Evidence Addendum

This addendum converts the scored synthetic transaction lookup into measured evidence for three reviewer questions: calibration, segment false positives, and SLA readiness.

## Calibration Evidence

| Metric | Value |
|---|---:|
| Brier score | 0.2192 |
| Expected calibration error | 0.4132 |
| Largest calibration gap band | 0.80-1.00 |
| Largest calibration gap | 0.6656 |

Interpretation: the score is useful for ranking and thresholding in the prototype, but it should still be calibrated on real validation data before being described as production odds.

## Fairness / Segment False-Positive Evidence

Highest observed false-positive concentration:

- Country: `BR` at 60.3% across 78 non-fraud transactions.
- Channel: `P2P` at 7.5% across 801 non-fraud transactions.

Interpretation: this is not a legal fairness conclusion. It is an analyst control that identifies where customer friction may concentrate and what segments need monitoring during a pilot.

## SLA / Turnaround Evidence

| Metric | Value |
|---|---:|
| Review queue cases | 390 |
| Cases with SLA policy assigned | 390 |
| SLA policy coverage | 100.0% |
| Measured breach rate | Not available in current synthetic data |

Interpretation: the app assigns urgency to routed cases, but true SLA breach rate requires investigation timestamps. This is listed as a production instrumentation requirement.
