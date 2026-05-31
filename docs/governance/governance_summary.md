# Governance Summary - Responsible AI and Control Design

## Purpose

This governance summary documents the responsible-AI controls, operational assumptions, and monitoring requirements for the fraud alert prioritization prototype.

The goal is to show that the project is not only technically functional, but also ready to be discussed in a banking risk, model governance, and fraud operations context.

## Governance Position

This model is a decision-support tool. It should assist fraud investigators by prioritizing review queues and explaining risk drivers. It should not independently make final customer-impacting decisions.

Recommended governance classification:

- Prototype / capstone model
- Synthetic-data validation only
- Human-in-the-loop decision support
- Not production-approved

## Key Controls Applied

| Control | How it was handled |
|---|---|
| Leakage prevention | Removed `alert_generated`, IDs, and target fields from model inputs |
| Class imbalance | Used weighted training and fraud-specific metrics |
| Threshold discipline | Selected threshold on validation data and evaluated on held-out test data |
| Explainability | Added global importance and local case explanations |
| Human oversight | App outputs review recommendations, not automatic actions |
| Operational fit | Added queue capacity strategy and investigator control tower |
| Auditability | Saved model metrics, feature list, thresholds, and explanation artifacts |

## Responsible AI Considerations

### Transparency

Each high-risk transaction includes plain-English rationale. The explanation layer compares the transaction to typical reference values and identifies which features increased model risk.

Example:

- Unusually high geographic distance can increase fraud risk.
- P2P channel behavior may contribute to elevated risk compared with the typical reference profile.

### Fairness and Bias Risk

Potential fairness-sensitive fields are not explicitly demographic protected classes, but some features may act as proxies:

- `txn_country`
- `home_country` if used in future versions
- `channel`
- `merchant_category`
- customer profile missingness

Mitigation plan:

1. Monitor performance by country and channel.
2. Review false positives by customer segment and region.
3. Avoid fully automated customer-impacting action.
4. Review whether country features create disproportionate review burden.
5. Document business justification for every retained risk feature.

### Explainability

Explainability controls:

- Global permutation importance identifies broad drivers.
- Local explanations identify transaction-level risk drivers.
- Explanations are displayed in the app alongside prediction and priority tier.

Known explainability limitation:

- Local reference-value sensitivity is not the same as causal explanation. It explains model behavior, not guaranteed real-world fraud causality.

### Privacy and Data Minimization

The prototype avoids using raw IDs as predictive features:

- `transaction_id`
- `customer_id`
- `merchant_id`

This reduces memorization risk and improves generalization.

Production recommendation:

- Keep identifiers for audit and case tracking only, not as model predictors unless transformed into governed behavioral features.

## Model Risk and Limitations

Major limitations:

1. Synthetic data may not represent production fraud patterns.
2. Performance is moderate and should not be oversold.
3. False positives increase under wider review policies.
4. Missing customer joins require upstream data quality review.
5. The model is sensitive to geographic-distance patterns.
6. Fraud tactics change over time, so drift monitoring is required.

## Monitoring Framework

### Daily Monitoring

- Number of scored transactions
- Number of transactions routed to review
- Priority-tier distribution
- Average fraud probability
- Queue size vs investigator capacity

### Weekly Monitoring

- Precision / hit rate
- Recall / fraud capture
- False-positive rate
- False-negative rate
- Model score distribution
- Top reason distribution
- Performance by channel and transaction country

### Monthly Governance Review

- Threshold calibration
- Feature drift
- Segment-level fairness review
- Challenger model performance
- Investigator feedback themes
- Case outcome quality

## Model Change Management

Any model update should document:

- Training data period
- Feature changes
- Model algorithm changes
- Validation performance
- Threshold impact
- Expected queue size impact
- Known limitations
- Approval owner

Suggested promotion path:

1. Prototype
2. Offline backtest
3. Shadow mode
4. Human-reviewed pilot
5. Controlled production release

## Human-in-the-Loop Design

The app should support investigator judgment by showing:

- Fraud probability
- Priority tier
- Top reasons
- Existing alert status
- Backtest outcome only in historical evaluation views

Recommended investigator actions:

- Review `Critical` cases first.
- Use explanations as investigation starting points.
- Record final outcome and reason code.
- Escalate patterns that suggest new fraud typologies.

## Incident and Escalation Scenarios

Escalate to model owner and fraud operations lead if:

- Queue volume spikes unexpectedly.
- Model misses a material fraud pattern.
- A region or channel receives disproportionate false positives.
- Data feed quality changes.
- Feature distributions shift sharply.
- Investigator trust declines due to poor explanations.

## Final Governance Recommendation

This project is suitable as a portfolio-grade prototype because it includes:

- model training
- threshold strategy
- explainability
- operational dashboarding
- governance controls
- human review design

It is not suitable for production without real data validation, formal model risk approval, security review, and live monitoring.
