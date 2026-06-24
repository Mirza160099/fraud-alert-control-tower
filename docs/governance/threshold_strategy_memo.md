# Threshold Strategy Memo - Fraud Alert Review Capacity

## Executive Summary

The fraud model should not be evaluated only as a binary classifier. In fraud operations, the central question is:

> Given limited investigator capacity, which transactions should be reviewed first?

For this prototype, the recommended operating policy is to use the `risk_triage_engine` decision-support layer with a threshold of `0.7977`, selected from validation data under a target review capacity of approximately `5%`.

## Business Objective

The threshold strategy balances:

- Fraud capture: catching more fraudulent transactions.
- Hit rate: reducing wasted investigator reviews.
- Queue size: keeping review volume within staffing capacity.
- Transparency: explaining why a transaction entered the queue.

## Recommended Operating Threshold

| Item | Value |
|---|---:|
| Triage layer | `risk_triage_engine` |
| Recommended threshold | `0.7977` |
| Target review capacity | 5% |
| Test review count after threshold | 74 |
| Test queue rate after threshold | 7.4% |
| Test hit rate | 13.5% |
| Test fraud capture | 25.0% |
| Test F1 | 17.5% |

The threshold was selected on validation data, then applied to the test set. Because score distributions can differ between validation and test, the actual test queue rate was `7.4%` rather than exactly `5%`. This is realistic and should be monitored in production.

## Exact Top-K Queue Alternative

If leadership needs a strict staffing cap, the system can review the exact top `5%` highest-risk transactions instead of applying a fixed probability threshold.

Exact top-5% test result:

| Metric | Value |
|---|---:|
| Review count | 50 |
| Hit rate | 18.0% |
| Fraud capture | 22.5% |
| F1 | 20.0% |
| True positives | 9 |
| False positives | 41 |

Recommendation:

- Use fixed thresholding for stable operational policy.
- Use exact top-K ranking when staffing is capped and the team must review a fixed number of cases.

## Alert Economics Sensitivity

The model is not only a statistical threshold. It also changes investigation cost and potential fraud-loss avoidance.

Compared with the existing alert benchmark:

| Item | Existing alert | Risk triage policy | Change |
|---|---:|---:|---:|
| Reviewed cases | 22 | 74 | +52 |
| Fraud cases caught | 8 | 10 | +2 |
| False positives | 14 | 64 | +50 |

Break-even assumptions:

| Assumption | Value |
|---|---:|
| Review cost per case | £8 |
| Additional review spend | 52 x £8 = £416 |
| Additional fraud cases caught | 2 |
| Break-even avoided loss per extra captured fraud | £208 |

This sensitivity is not a production ROI claim. It demonstrates the operating question a bank would ask: are the additional reviews justified by the incremental fraud caught, and how should that trade-off change by staffing level, fraud-loss severity, and customer-friction risk?

Recommendation from the economics:

- Use the model as a prioritization overlay or top-K pilot first.
- Do not position it as a full replacement for the incumbent alert rule until real-data validation proves the extra review load is justified.
- If avoided loss per additional fraud case is below £208, tighten the queue to a smaller top-K operating point.

## Capacity Sensitivity

For the risk triage policy:

| Target capacity | Validation threshold | Test reviews | Test hit rate | Test fraud capture |
|---:|---:|---:|---:|---:|
| 1% | 0.8118 | 10 | 50.0% | 12.5% |
| 2% | 0.8087 | 23 | 21.7% | 12.5% |
| 5% | 0.7977 | 74 | 13.5% | 25.0% |
| 10% | 0.5742 | 102 | 12.7% | 32.5% |
| 15% | 0.5571 | 164 | 9.8% | 40.0% |

Interpretation:

- Lower capacity thresholds create smaller queues and higher precision.
- Higher capacity thresholds capture more fraud but create more false positives.
- The best threshold depends on the cost of missed fraud, review cost, and staffing availability.

## Existing Alert Benchmark

Existing alert performance:

| Metric | Existing alert |
|---|---:|
| Precision / hit rate | 36.4% |
| Recall / fraud capture | 20.0% |
| True positives | 8 |
| False positives | 14 |
| False negatives | 32 |

Risk triage policy at selected threshold:

| Metric | Risk triage policy |
|---|---:|
| Precision / hit rate | 13.5% |
| Recall / fraud capture | 25.0% |
| True positives | 10 |
| False positives | 64 |
| False negatives | 30 |

Business trade-off:

- The existing alert rule is more precise.
- The risk triage policy captures more fraud.
- The model should be positioned as a prioritization layer, not a replacement rule without further validation.

## Recommended Queue Policy

1. Score all eligible transactions.
2. Assign priority tier:
   - `Critical`: probability at or above `max(0.820, threshold)`
   - `High`: probability from the review threshold up to the Critical band
   - `Medium`: probability from `0.350` up to the review threshold
   - `Low`: probability below `0.350`
3. Route `Critical` and `High` first.
4. Use exact top-K selection when investigator capacity is fixed.
5. Track actual queue volume daily.
6. Recalibrate threshold if queue volume deviates materially from staffing assumptions.

## KPI Monitoring

Track these KPIs weekly:

- Review queue count
- Hit rate / precision
- Fraud capture / recall
- False-positive volume
- False-negative volume
- Average case age
- Investigator throughput
- Priority-tier distribution
- Segment-level performance by country, channel, and merchant category

## Escalation Rules

Threshold review should be triggered if:

- Queue volume exceeds staffing capacity for three consecutive business days.
- Hit rate falls below the accepted operating band.
- Fraud loss or missed fraud increases materially.
- New country, channel, merchant, or attack pattern emerges.
- Model score distribution shifts materially from training distribution.

## Final Recommendation

Use `0.7977` as the prototype threshold for the demo and portfolio app.

For an interview, frame the threshold as a business-control decision:

> I did not simply choose the threshold with the highest accuracy. I tested review-capacity scenarios and selected a policy that lets fraud leadership trade off missed fraud against investigator workload.
