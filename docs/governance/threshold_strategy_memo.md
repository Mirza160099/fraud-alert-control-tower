# Threshold Strategy Memo - Fraud Alert Review Capacity

## Executive Summary

The fraud model should not be evaluated only as a binary classifier. In fraud operations, the central question is:

> Given limited investigator capacity, which transactions should be reviewed first?

For this prototype, the recommended operating policy is to use the `adaboost_weighted` champion model with a threshold of `0.7795`, selected from validation data under a target review capacity of approximately `5%`.

## Business Objective

The threshold strategy balances:

- Fraud capture: catching more fraudulent transactions.
- Hit rate: reducing wasted investigator reviews.
- Queue size: keeping review volume within staffing capacity.
- Transparency: explaining why a transaction entered the queue.

## Recommended Operating Threshold

| Item | Value |
|---|---:|
| Champion model | `adaboost_weighted` |
| Recommended threshold | `0.7795` |
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
| Hit rate | 20.0% |
| Fraud capture | 25.0% |
| F1 | 22.2% |
| True positives | 10 |
| False positives | 40 |

Recommendation:

- Use fixed thresholding for stable operational policy.
- Use exact top-K ranking when staffing is capped and the team must review a fixed number of cases.

## Capacity Sensitivity

For the champion model:

| Target capacity | Validation threshold | Test reviews | Test hit rate | Test fraud capture |
|---:|---:|---:|---:|---:|
| 1% | 0.8415 | 10 | 20.0% | 5.0% |
| 2% | 0.8151 | 16 | 25.0% | 10.0% |
| 5% | 0.7795 | 74 | 13.5% | 25.0% |
| 10% | 0.5274 | 148 | 10.8% | 40.0% |
| 15% | 0.5179 | 224 | 8.5% | 47.5% |

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

Champion model at selected threshold:

| Metric | Champion model |
|---|---:|
| Precision / hit rate | 13.5% |
| Recall / fraud capture | 25.0% |
| True positives | 10 |
| False positives | 64 |
| False negatives | 30 |

Business trade-off:

- The existing alert rule is more precise.
- The champion model captures more fraud.
- The model should be positioned as a prioritization layer or challenger queue strategy, not a replacement rule without further validation.

## Recommended Queue Policy

1. Score all eligible transactions.
2. Assign priority tier:
   - `Critical`: probability at or above `max(0.80, threshold)`
   - `High`: probability at or above `max(0.60, threshold)`
   - `Standard Review`: probability at or above threshold
   - `Monitor`: below threshold
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

Use `0.7795` as the prototype threshold for the demo and portfolio app.

For an interview, frame the threshold as a business-control decision:

> I did not simply choose the threshold with the highest accuracy. I tested review-capacity scenarios and selected a policy that lets fraud leadership trade off missed fraud against investigator workload.
