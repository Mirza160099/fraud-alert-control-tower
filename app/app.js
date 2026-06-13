const state = {
  model: null,
  dashboard: null,
};

const featureLabels = {
  geo_distance_km: "Geographic distance",
  txn_country: "Transaction country",
  synthetic_identity_score: "Synthetic identity score",
  merchant_risk_score: "Merchant risk score",
  channel: "Payment channel",
  txn_hour: "Transaction hour",
  device_risk_score: "Device risk score",
  merchant_profile_risk_score: "Merchant profile risk score",
  transaction_amount_usd: "Transaction amount",
  amount_log1p: "Log-scaled amount",
};

function sigmoid(value) {
  return 1 / (1 + Math.exp(-value));
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function percent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function capacityLabel(value) {
  const percentage = Number(value) * 100;
  return `${percentage % 1 === 0 ? percentage.toFixed(0) : percentage.toFixed(1)}%`;
}

function numberText(value, digits = 3) {
  return Number(value).toFixed(digits);
}

function moneyText(value) {
  const sign = Number(value) < 0 ? "-" : "";
  return `${sign}$${Math.abs(Math.round(Number(value))).toLocaleString("en-US")}`;
}

function signedCount(value) {
  const number = Number(value);
  return `${number > 0 ? "+" : ""}${number}`;
}

function triageLayerName() {
  return "Risk triage engine";
}

function evidenceBasisLabel() {
  return "Held-out test + governance pack";
}

function getNumber(id, fallback = 0) {
  const value = Number(document.getElementById(id).value);
  return Number.isFinite(value) ? value : fallback;
}

function populateSelect(id, values, fallback) {
  const select = document.getElementById(id);
  select.replaceChildren();
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
  select.value = values.includes(fallback) ? fallback : values[0];
}

function preprocess(input, model) {
  const preprocessing = model.preprocessing;
  const transformed = [];

  preprocessing.numeric_features.forEach((feature, index) => {
    let value = Number(input[feature]);
    if (!Number.isFinite(value)) {
      value = preprocessing.numeric_imputer_statistics[index];
    }
    transformed.push(
      (value - preprocessing.numeric_scaler_mean[index]) /
        preprocessing.numeric_scaler_scale[index],
    );
  });

  preprocessing.categorical_features.forEach((feature, index) => {
    const fallback = preprocessing.categorical_imputer_statistics[index];
    const value = input[feature] ?? fallback;
    preprocessing.categorical_categories[index].forEach((category) => {
      transformed.push(value === category ? 1 : 0);
    });
  });

  return transformed;
}

function predictTree(tree, transformed) {
  let node = 0;
  while (tree.children_left[node] !== -1) {
    const featureIndex = tree.feature[node];
    const threshold = tree.threshold[node];
    node =
      transformed[featureIndex] <= threshold
        ? tree.children_left[node]
        : tree.children_right[node];
  }
  return tree.predicted_class_index[node];
}

function predictProbability(input, model = state.model) {
  const transformed = preprocess(input, model);
  const { estimator_weights: weights, trees } = model.risk_ensemble;
  const weightSum = weights.reduce((total, weight) => total + weight, 0);
  let classZeroScore = 0;
  let classOneScore = 0;

  trees.forEach((tree, index) => {
    const predictedClass = predictTree(tree, transformed);
    const weight = weights[index];
    if (predictedClass === 0) {
      classZeroScore += weight;
      classOneScore -= weight;
    } else {
      classZeroScore -= weight;
      classOneScore += weight;
    }
  });

  classZeroScore /= weightSum;
  classOneScore /= weightSum;

  const decision = -classZeroScore + classOneScore;
  return sigmoid(decision);
}

function classifyPriority(probability, threshold) {
  if (probability >= Math.max(0.82, threshold)) {
    return {
      tier: "Critical",
      action: "Immediate review",
      className: "critical",
    };
  }
  if (probability >= threshold) {
    return {
      tier: "High",
      action: "Review as fraud risk",
      className: "high",
    };
  }
  if (probability >= 0.35) {
    return {
      tier: "Medium",
      action: "Monitor closely",
      className: "medium",
    };
  }
  return {
    tier: "Low",
    action: "Likely legitimate",
    className: "low",
  };
}

function readFormInput() {
  const amount = Math.max(0, getNumber("amount", 0));
  const currency = document.getElementById("currency").value;
  const fxRate = state.model.currency_rates_to_usd[currency] ?? 1;
  const amountUsd = amount * fxRate;

  return {
    geo_distance_km: Math.max(0, getNumber("geo_distance_km", 0)),
    txn_country: document.getElementById("txn_country").value,
    synthetic_identity_score: clamp(getNumber("synthetic_identity_score", 0), 0, 1),
    merchant_risk_score: clamp(getNumber("merchant_risk_score", 0), 0, 1),
    channel: document.getElementById("channel").value,
    txn_hour: clamp(Math.round(getNumber("txn_hour", 0)), 0, 23),
    device_risk_score: clamp(getNumber("device_risk_score", 0), 0, 1),
    merchant_profile_risk_score: clamp(
      getNumber("merchant_profile_risk_score", 0),
      0,
      1,
    ),
    transaction_amount_usd: amountUsd,
    amount_log1p: Math.log1p(amountUsd),
  };
}

function formatValue(value) {
  if (typeof value === "number") return value.toFixed(3);
  return String(value);
}

function explainFeature(feature, actual, reference, delta) {
  if (Math.abs(delta) < 0.001) {
    return `${featureLabels[feature] ?? feature} was ${formatValue(actual)} versus a typical value of ${formatValue(reference)}; this had no material effect on the risk score.`;
  }
  const direction = delta >= 0 ? "increased" : "reduced";
  return `${featureLabels[feature] ?? feature} was ${formatValue(actual)} versus a typical value of ${formatValue(reference)}; this ${direction} risk by ${Math.abs(delta).toFixed(3)}.`;
}

function localDeltas(input) {
  const originalProbability = predictProbability(input);
  return state.model.selected_features
    .map((feature) => {
      const reference = state.model.reference_profile[feature];
      const changed = { ...input, [feature]: reference };
      if (feature === "transaction_amount_usd") {
        changed.amount_log1p = Math.log1p(Math.max(0, Number(reference)));
      }
      const perturbedProbability = predictProbability(changed);
      const delta = originalProbability - perturbedProbability;
      return {
        feature,
        actual: input[feature],
        reference,
        delta,
        absoluteDelta: Math.abs(delta),
        text: explainFeature(feature, input[feature], reference, delta),
      };
    })
    .sort((a, b) => b.delta - a.delta || b.absoluteDelta - a.absoluteDelta);
}

function renderReasons(deltas) {
  const reasonList = document.getElementById("reasonList");
  reasonList.replaceChildren();
  const materialPositiveReasons = deltas
    .filter((item) => item.delta > 0.001)
    .slice(0, 3);
  const materialReasons = deltas
    .filter((item) => item.absoluteDelta > 0.001)
    .sort((a, b) => b.absoluteDelta - a.absoluteDelta)
    .slice(0, 3);
  const reasons =
    materialPositiveReasons.length > 0 ? materialPositiveReasons : materialReasons;

  if (reasons.length === 0) {
    const li = document.createElement("li");
    li.textContent =
      "No material risk-increasing driver was detected against the reference profile.";
    reasonList.appendChild(li);
    return;
  }

  reasons.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item.text;
    reasonList.appendChild(li);
  });

  if (reasons.length < 3) {
    const li = document.createElement("li");
    li.textContent = "No additional material risk-increasing driver was detected.";
    reasonList.appendChild(li);
  }
}

function strongestRiskDriver(deltas) {
  const strongestPositive = deltas.find((item) => item.delta > 0.001);
  const strongestOverall = deltas
    .slice()
    .sort((a, b) => b.absoluteDelta - a.absoluteDelta)[0];
  const driver = strongestPositive ?? strongestOverall;
  return driver && driver.absoluteDelta > 0.001 ? driver : null;
}

function topRiskDriver(deltas) {
  const driver = strongestRiskDriver(deltas);
  return driver ? featureLabels[driver.feature] ?? driver.feature : "the strongest driver";
}

function recommendedActions(priority, deltas) {
  const driver = topRiskDriver(deltas);

  if (priority.tier === "Low") {
    return [
      "Allow or monitor without manual review unless a new risk signal appears.",
      "Keep the score and explanation in the audit trail for later pattern analysis.",
      "Re-score if the customer changes device, country, channel, or transaction amount suddenly.",
    ];
  }

  if (priority.tier === "Medium") {
    return [
      "Monitor closely and check whether similar activity repeats across the same customer, device, or merchant.",
      `Review ${driver} before escalation, because it is the strongest local driver in this score.`,
      "Move to investigator review if velocity, geography, device risk, or merchant risk increases.",
    ];
  }

  if (priority.tier === "High") {
    return [
      "Route to investigator review before taking any customer-impacting action.",
      `Validate ${driver} against customer history, merchant profile, and recent account activity.`,
      "Use step-up verification or customer contact if the evidence remains suspicious after review.",
    ];
  }

  return [
    "Escalate for immediate investigator review because the score is above the critical band.",
    "Apply step-up authentication or a temporary hold while the evidence is checked.",
    `Validate ${driver}, device risk, geography, merchant context, and customer history before final action.`,
  ];
}

function renderActions(priority, deltas) {
  const actionList = document.getElementById("actionList");
  actionList.replaceChildren();

  recommendedActions(priority, deltas).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    actionList.appendChild(li);
  });
}

function briefCopy(priority, driverName) {
  if (priority.tier === "Low") {
    return {
      focus: "Normal monitoring",
      focusDetail: "No manual review is needed unless a new behavior pattern appears.",
      control: "Audit trail only",
      controlDetail: "Record the score and explanation so future changes can be compared.",
      evidence: "Watch for change",
      evidenceDetail: "Re-check only if device, country, channel, amount, or merchant behavior shifts.",
    };
  }

  if (priority.tier === "Medium") {
    return {
      focus: "Pattern check",
      focusDetail: `Check whether ${driverName} is repeated across recent activity.`,
      control: "Soft friction",
      controlDetail: "Monitor or request low-friction verification before escalating to a full review.",
      evidence: "Two-signal rule",
      evidenceDetail: "Escalate only if another signal supports the risk, such as device, geography, or merchant history.",
    };
  }

  if (priority.tier === "High") {
    return {
      focus: "Investigator review",
      focusDetail: `Validate ${driverName} against customer history before any customer-impacting action.`,
      control: "Step-up verification",
      controlDetail: "Use customer contact, authentication, or case review before blocking the transaction.",
      evidence: "Customer context",
      evidenceDetail: "Compare location, device, amount, merchant, and recent account activity.",
    };
  }

  return {
    focus: "Immediate escalation",
    focusDetail: `Treat ${driverName} as the first investigation lead, not the only evidence.`,
    control: "Temporary hold",
    controlDetail: "Apply a short hold or step-up authentication while an investigator validates the case.",
    evidence: "Full case review",
    evidenceDetail: "Confirm multiple independent signals before a final fraud decision.",
  };
}

function renderInvestigatorBrief(input, probability, priority, deltas) {
  const driver = strongestRiskDriver(deltas);
  const driverName = driver
    ? featureLabels[driver.feature] ?? driver.feature
    : "No material driver";
  const signalDetail = driver
    ? `${formatValue(driver.actual)} vs typical ${formatValue(driver.reference)}; local score impact ${driver.delta >= 0 ? "+" : ""}${driver.delta.toFixed(3)}.`
    : "The transaction is close to the reference profile.";
  const copy = briefCopy(priority, driverName);

  document.getElementById("briefTier").textContent = `${priority.tier} priority`;
  document.getElementById("briefTier").className = priority.className;
  document.getElementById("briefSignal").textContent = driverName;
  document.getElementById("briefSignalDetail").textContent = signalDetail;
  document.getElementById("briefFocus").textContent = copy.focus;
  document.getElementById("briefFocusDetail").textContent = copy.focusDetail;
  document.getElementById("briefControl").textContent = copy.control;
  document.getElementById("briefControlDetail").textContent = copy.controlDetail;
  document.getElementById("briefEvidence").textContent = copy.evidence;
  document.getElementById("briefEvidenceDetail").textContent =
    probability >= 0.35
      ? copy.evidenceDetail
      : `${copy.evidenceDetail} Current amount in USD is ${formatValue(input.transaction_amount_usd)}.`;
}

function renderFeatureBars(deltas) {
  const riskBars = document.getElementById("riskFeatureBars");
  const protectiveBars = document.getElementById("protectiveFeatureBars");
  riskBars.replaceChildren();
  protectiveBars.replaceChildren();

  const material = deltas
    .slice()
    .filter((item) => item.absoluteDelta > 0.001);
  const riskDrivers = material
    .filter((item) => item.delta > 0)
    .sort((a, b) => b.delta - a.delta)
    .slice(0, 5);
  const protectiveSignals = material
    .filter((item) => item.delta < 0)
    .sort((a, b) => b.absoluteDelta - a.absoluteDelta)
    .slice(0, 5);

  document.getElementById("riskDriverCount").textContent =
    `${riskDrivers.length} ${riskDrivers.length === 1 ? "signal" : "signals"}`;
  document.getElementById("protectiveSignalCount").textContent =
    `${protectiveSignals.length} ${protectiveSignals.length === 1 ? "signal" : "signals"}`;

  const maxRiskDelta = Math.max(
    ...riskDrivers.map((item) => item.absoluteDelta),
    0.001,
  );
  const maxProtectiveDelta = Math.max(
    ...protectiveSignals.map((item) => item.absoluteDelta),
    0.001,
  );

  riskDrivers.forEach((item) => {
    riskBars.appendChild(
      buildBarRow(
        featureLabels[item.feature] ?? item.feature,
        item.absoluteDelta,
        maxRiskDelta,
        `+${item.delta.toFixed(3)}`,
      ),
    );
  });

  protectiveSignals.forEach((item) => {
    protectiveBars.appendChild(
      buildBarRow(
        featureLabels[item.feature] ?? item.feature,
        item.absoluteDelta,
        maxProtectiveDelta,
        item.delta.toFixed(3),
        true,
      ),
    );
  });

  if (riskDrivers.length === 0) {
    riskBars.appendChild(
      buildEmptyFeatureState("No material risk-increasing signal detected."),
    );
  }

  if (protectiveSignals.length === 0) {
    protectiveBars.appendChild(
      buildEmptyFeatureState("No material protective signal detected."),
    );
  }
}

function buildEmptyFeatureState(text) {
  const empty = document.createElement("p");
  empty.className = "feature-empty";
  empty.textContent = text;
  return empty;
}

function buildBarRow(nameText, value, maxValue, valueText, negative = false) {
  const row = document.createElement("div");
  row.className = "feature-row";

  const name = document.createElement("div");
  name.className = "feature-name";
  name.textContent = nameText;

  const track = document.createElement("div");
  track.className = "bar-track";
  const fill = document.createElement("div");
  fill.className = `bar-fill${negative ? " negative" : ""}`;
  fill.style.width = `${Math.max(4, (Math.abs(value) / Math.max(maxValue, 0.001)) * 100)}%`;
  track.appendChild(fill);

  const label = document.createElement("div");
  label.className = "delta-value";
  label.textContent = valueText;

  row.append(name, track, label);
  return row;
}

function renderDecision(probability, priority) {
  const badge = document.getElementById("decisionBadge");
  badge.className = `decision-badge ${priority.className}`;

  document.getElementById("decisionText").textContent = `${priority.tier} fraud risk`;
  document.getElementById("probabilityText").textContent = probability.toFixed(3);
  document.getElementById("priorityText").textContent = priority.action;
  document.getElementById("liveRiskTier").textContent = priority.tier;
  document.getElementById("liveRiskTier").className = priority.className;
  document.getElementById("liveProbability").textContent = probability.toFixed(3);
  document.getElementById("liveAction").textContent = priority.action;
}

function scoreCurrentForm() {
  const input = readFormInput();
  const probability = predictProbability(input);
  const priority = classifyPriority(probability, state.model.threshold);
  const deltas = localDeltas(input);

  renderDecision(probability, priority);
  renderReasons(deltas);
  renderActions(priority, deltas);
  renderInvestigatorBrief(input, probability, priority, deltas);
  renderFeatureBars(deltas);
}

function initializeForm(model) {
  const countrySchema = model.feature_schema.txn_country;
  const channelSchema = model.feature_schema.channel;
  populateSelect("txn_country", countrySchema.categories, "US");
  populateSelect("channel", channelSchema.categories, "Card Present");
  populateSelect("currency", Object.keys(model.currency_rates_to_usd), "USD");

  document.getElementById("modelName").textContent = triageLayerName();
  document.getElementById("liveModelName").textContent = evidenceBasisLabel();
  document.getElementById("thresholdLabel").textContent = `Threshold ${model.threshold.toFixed(3)}`;
  document.getElementById("capacityText").textContent = `${Math.round(model.target_capacity_rate * 100)}%`;

  document.getElementById("transactionForm").addEventListener("submit", (event) => {
    event.preventDefault();
    scoreCurrentForm();
  });
  document.getElementById("transactionForm").addEventListener("input", () => {
    scoreCurrentForm();
  });
  document.getElementById("transactionForm").addEventListener("change", () => {
    scoreCurrentForm();
  });
  scoreCurrentForm();
}

function setActiveTab(tabName, updateUrl = false) {
  const allowedTabs = new Set(["score", "queue", "metrics", "governance"]);
  const activeTab = allowedTabs.has(tabName) ? tabName : "score";

  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === activeTab);
  });
  document.querySelectorAll(".tab-view").forEach((view) => {
    view.classList.toggle("active", view.id === `${activeTab}View`);
  });

  if (updateUrl) {
    const url = new URL(window.location.href);
    url.searchParams.set("view", activeTab);
    window.history.replaceState({}, "", url);
  }
}

function initializeTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab, true));
  });
  setActiveTab(new URLSearchParams(window.location.search).get("view") ?? "score");
}

function sentenceText(text) {
  if (!text) return "";
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

function titleCase(text) {
  return String(text).replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function priorityClassName(tier) {
  return String(tier || "medium").toLowerCase();
}

function primaryDriverLabel(reason) {
  if (!reason) return "Primary driver";
  const marker = " was ";
  const driver = reason.includes(marker) ? reason.slice(0, reason.indexOf(marker)) : reason;
  return titleCase(driver);
}

function queueSla(tier) {
  if (tier === "Critical") return "Immediate review";
  if (tier === "High") return "Same-shift review";
  if (tier === "Medium") return "Monitor today";
  return "No manual queue";
}

function queueAction(tier) {
  if (tier === "Critical") {
    return "Assign to an investigator before any customer-impacting decision.";
  }
  if (tier === "High") {
    return "Validate the evidence and use step-up verification if the case remains suspicious.";
  }
  if (tier === "Medium") {
    return "Watch for repeated activity before escalating to manual review.";
  }
  return "Keep in audit trail and rescore if behavior changes.";
}

function evidenceStatus(caseItem) {
  return Number(caseItem.alert_generated) === 1
    ? "Rule signal present"
    : "Previously unflagged";
}

function evidenceCheckText(caseItem) {
  if (Number(caseItem.alert_generated) === 1) {
    return "Use the rule signal, model reason, and customer context together before deciding the case.";
  }
  return "Validate this incremental triage case carefully because no prior rule signal caught it.";
}

function transactionAmountText(caseItem) {
  const amountReason = [caseItem.reason_1, caseItem.reason_2, caseItem.reason_3]
    .filter(Boolean)
    .find((reason) => /^transaction amount was /i.test(reason));
  const match = amountReason?.match(/^transaction amount was ([0-9.]+)/i);
  if (!match) return "Not exported";
  const amount = Number(match[1]);
  if (!Number.isFinite(amount)) return "Not exported";
  return `$${amount.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function backtestOutcomeText(caseItem) {
  return Number(caseItem.actual_fraud_label) === 1
    ? "Confirmed fraud"
    : "Not fraud in backtest";
}

function renderQueueCommand(summary) {
  const champion = state.dashboard.metrics.champion;
  const existing = state.dashboard.metrics.existing_alert_benchmark;

  document.getElementById("queueReviewRate").textContent = percent(
    champion.test_queue_rate,
  );
  document.getElementById("queueThreshold").textContent = numberText(
    champion.threshold,
    3,
  );
  document.getElementById("queueCaptureRate").textContent = percent(
    champion.test_recall_fraud_capture_rate,
  );
  document.getElementById("queueFalsePositiveLoad").textContent = String(
    champion.test_false_positives,
  );

  const laneList = document.getElementById("priorityLaneList");
  laneList.replaceChildren();
  const cases = state.dashboard.top_queue_cases;
  ["Critical", "High", "Medium", "Low"].forEach((tier) => {
    const count = cases.filter((caseItem) => caseItem.priority_tier === tier).length;
    const lane = document.createElement("div");
    lane.className = `priority-lane ${priorityClassName(tier)}${count === 0 ? " empty" : ""}`;
    lane.innerHTML = `
      <div>
        <strong>${tier}</strong>
        <span>${queueSla(tier)}</span>
        <small>${queueAction(tier)}</small>
      </div>
      <div class="lane-count">
        <b>${count}</b>
        <span>${count === 1 ? "case" : "cases"}</span>
      </div>
    `;
    laneList.appendChild(lane);
  });

  const laneNote = document.createElement("p");
  laneNote.className = "lane-note";
  laneNote.textContent = `Lane counts reflect the ${cases.length} visible highest-risk cases. Lower lanes remain defined for live scoring and production queue routing.`;
  laneList.appendChild(laneNote);

  const controlChecks = document.getElementById("queueControlChecks");
  controlChecks.replaceChildren();
  const incrementalFrauds =
    Number(champion.test_true_positives) - Number(existing.true_positives);
  [
    `Threshold ${numberText(champion.threshold, 3)} routes ${percent(champion.test_queue_rate)} of test transactions to review.`,
    `${summary.missed_existing_alerts_in_top_cases} visible top cases are rule-gap cases that need investigator validation.`,
    `${signedCount(incrementalFrauds)} additional fraud cases are captured at this operating point.`,
    `${champion.test_false_positives} backtest false positives require human validation before any customer-impacting action.`,
  ].forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    controlChecks.appendChild(li);
  });
}

function renderQueue() {
  const summary = state.dashboard.queue_summary;
  document.getElementById("queueSize").textContent = String(summary.queue_size);
  document.getElementById("fraudsInQueue").textContent = String(summary.frauds_in_queue);
  document.getElementById("queueHitRate").textContent = percent(summary.queue_hit_rate);
  document.getElementById("missedOldAlerts").textContent = String(
    summary.missed_existing_alerts_in_top_cases,
  );
  renderQueueCommand(summary);

  const caseList = document.getElementById("caseList");
  caseList.replaceChildren();

  state.dashboard.top_queue_cases.forEach((caseItem) => {
    const row = document.createElement("article");
    const tierClass = priorityClassName(caseItem.priority_tier);
    const backtestLabel =
      Number(caseItem.actual_fraud_label) === 1
        ? "Backtest: true fraud"
        : "Backtest: non-fraud";
    const oldAlertLabel = evidenceStatus(caseItem);
    const secondaryReasons = [caseItem.reason_2, caseItem.reason_3]
      .filter(Boolean)
      .map((reason) => `<li>${sentenceText(reason)}</li>`)
      .join("");

    row.className = `case-card ${tierClass}`;
    row.innerHTML = `
      <div class="case-header">
        <div class="case-title">
          <span class="case-rank">#${caseItem.case_rank}</span>
          <div>
            <span class="muted-label">Transaction</span>
            <strong>${caseItem.transaction_id}</strong>
            <small>${String(caseItem.event_ts).replace(" ", " at ")}</small>
          </div>
        </div>
        <div class="case-score ${tierClass}">${numberText(caseItem.predicted_fraud_probability, 3)}</div>
      </div>

      <div class="case-meta">
        <span class="case-tag ${tierClass}">${caseItem.priority_tier}</span>
        <span class="case-tag ${Number(caseItem.actual_fraud_label) === 1 ? "true-fraud" : "non-fraud"}">${backtestLabel}</span>
        <span class="case-tag ${Number(caseItem.alert_generated) === 1 ? "old-alert-hit" : "old-alert-missed"}">${oldAlertLabel}</span>
      </div>

      <div class="case-facts">
        <div>
          <span>Amount</span>
          <strong>${transactionAmountText(caseItem)}</strong>
        </div>
        <div>
          <span>Event time</span>
          <strong>${String(caseItem.event_ts).replace(" ", " at ")}</strong>
        </div>
        <div>
          <span>Backtest outcome</span>
          <strong>${backtestOutcomeText(caseItem)}</strong>
        </div>
        <div>
          <span>Legacy rule</span>
          <strong>${oldAlertLabel}</strong>
        </div>
      </div>

      <div class="case-workflow">
        <div>
          <span>SLA</span>
          <strong>${queueSla(caseItem.priority_tier)}</strong>
          <p>${queueAction(caseItem.priority_tier)}</p>
        </div>
        <div>
          <span>Primary driver</span>
          <strong>${primaryDriverLabel(caseItem.reason_1)}</strong>
          <p>${sentenceText(caseItem.reason_1)}</p>
        </div>
        <div>
          <span>Evidence check</span>
          <strong>${oldAlertLabel}</strong>
          <p>${evidenceCheckText(caseItem)}</p>
        </div>
      </div>

      <ul class="case-secondary">
        ${secondaryReasons}
      </ul>
    `;
    caseList.appendChild(row);
  });
}

function benchmarkReviewCount(existing) {
  return Number(existing.true_positives) + Number(existing.false_positives);
}

function championTrueNegatives(champion, existing) {
  const existingTotal =
    Number(existing.true_positives) +
    Number(existing.false_positives) +
    Number(existing.false_negatives) +
    Number(existing.true_negatives);
  const championKnown =
    Number(champion.test_true_positives) +
    Number(champion.test_false_positives) +
    Number(champion.test_false_negatives);
  return Math.max(0, existingTotal - championKnown);
}

function championComparisonRow() {
  return state.dashboard.model_comparison.find(
    (row) => row.model_name === state.dashboard.metrics.champion.model_name,
  );
}

function renderAnalystMetrics() {
  const champion = state.dashboard.metrics.champion;
  const existing = state.dashboard.metrics.existing_alert_benchmark;
  const championComparison = championComparisonRow();
  const championPrAuc = Number(championComparison?.test_average_precision_pr_auc ?? 0);
  const championTn = championTrueNegatives(champion, existing);
  const championTotal =
    championTn +
    Number(champion.test_true_positives) +
    Number(champion.test_false_positives) +
    Number(champion.test_false_negatives);
  const incrementalFraud =
    Number(champion.test_true_positives) - Number(existing.true_positives);
  const incrementalReviews =
    Number(champion.test_review_count) - benchmarkReviewCount(existing);
  const reviewsPerFraud = 1 / Math.max(Number(champion.test_precision_hit_rate), 0.001);

  document.getElementById("championModelBadge").textContent = "Operating evidence";
  document.getElementById("scorecardPrAuc").textContent = numberText(
    championPrAuc,
    3,
  );
  document.getElementById("scorecardPrAucBench").textContent =
    "Ranking quality on held-out data";
  document.getElementById("scorecardCapture").textContent = percent(
    champion.test_recall_fraud_capture_rate,
  );
  document.getElementById("scorecardCaptureBench").textContent =
    "Fraud cases captured at the review threshold";
  document.getElementById("scorecardHitRate").textContent = percent(
    champion.test_precision_hit_rate,
  );
  document.getElementById("scorecardHitBench").textContent =
    "Share of reviewed cases confirmed as fraud";
  document.getElementById("scorecardReviewRate").textContent = percent(
    champion.test_queue_rate,
  );
  document.getElementById("scorecardReviewCount").textContent =
    `${champion.test_review_count} of ${championTotal.toLocaleString("en-US")} test transactions`;
  document.getElementById("scorecardNarrative").textContent =
    `This operating view translates fraud ranking into a review queue: ${percent(champion.test_queue_rate)} of test transactions are routed to investigators, with capture, precision, and false-positive load shown together.`;

  document.getElementById("championTp").textContent = String(
    champion.test_true_positives,
  );
  document.getElementById("championFp").textContent = String(
    champion.test_false_positives,
  );
  document.getElementById("championFn").textContent = String(
    champion.test_false_negatives,
  );
  document.getElementById("championTn").textContent = String(championTn);
  document.getElementById("oldTp").textContent = String(existing.true_positives);
  document.getElementById("oldFp").textContent = String(existing.false_positives);
  document.getElementById("oldFn").textContent = String(existing.false_negatives);
  document.getElementById("oldTn").textContent = String(existing.true_negatives);

  const takeaways = [
    `Ranking quality is tracked because fraud is rare; the validation score is ${numberText(championPrAuc, 3)} and is used with queue workload rather than alone.`,
    `The triage policy captures ${percent(champion.test_recall_fraud_capture_rate)} of fraud in the test set, adding ${signedCount(incrementalFraud)} caught fraud cases at the selected operating point.`,
    `The hit rate is ${percent(champion.test_precision_hit_rate)}, or about one fraud per ${reviewsPerFraud.toFixed(1)} reviewed cases, so investigator capacity remains part of the decision.`,
    `${signedCount(incrementalReviews)} extra reviews are accepted in exchange for higher capture; that is why the Business Impact panel translates model metrics into operating cost.`,
  ];
  const list = document.getElementById("metricsTakeaways");
  list.replaceChildren();
  takeaways.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  });
}

function renderPilotRecommendation() {
  const champion = state.dashboard.metrics.champion;
  const list = document.getElementById("pilotRecommendationList");
  const recommendations = [
    "Run the triage layer in shadow mode before any customer-impacting action.",
    `Use the ${percent(champion.test_queue_rate)} review policy as the pilot operating point and monitor queue load daily.`,
    "Require investigator approval and case notes before escalation, blocking, or customer contact.",
    "Track fraud capture, false positives, queue size, score drift, and segment-level outcomes during the pilot.",
  ];
  list.replaceChildren();
  recommendations.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  });
}

function renderCapacityThresholds() {
  const tbody = document.getElementById("capacityRows");
  tbody.replaceChildren();
  const champion = state.dashboard.metrics.champion;
  const allowedRates = new Set([0.01, 0.02, 0.05, 0.1, 0.15]);
  const rows = state.dashboard.capacity_thresholds
    .filter(
      (row) =>
        row.model_name === champion.model_name &&
        allowedRates.has(Number(row.target_capacity_rate)),
    )
    .sort((a, b) => Number(a.target_capacity_rate) - Number(b.target_capacity_rate));

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = Number(row.target_capacity_rate) === 0.05 ? "selected-policy-row" : "";
    tr.innerHTML = `
      <td>${capacityLabel(row.target_capacity_rate)} capacity policy</td>
      <td>${numberText(row.validation_threshold, 3)}</td>
      <td>${row.test_review_count}</td>
      <td>${percent(row.test_precision_hit_rate)}</td>
      <td>${percent(row.test_recall_fraud_capture_rate)}</td>
      <td>${percent(row.test_exact_topk_precision_hit_rate)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderGlobalImportance() {
  const bars = document.getElementById("globalFeatureBars");
  bars.replaceChildren();
  const visible = state.dashboard.global_feature_importance
    .filter((row) => Number(row.permutation_importance_mean_pr_auc) >= 0.001)
    .slice(0, 8);
  const maxValue = Math.max(
    ...visible.map((row) => Math.abs(Number(row.permutation_importance_mean_pr_auc))),
    0.001,
  );

  visible.forEach((row) => {
    const value = Number(row.permutation_importance_mean_pr_auc);
    bars.appendChild(
      buildBarRow(
        featureLabels[row.feature] ?? row.feature,
        value,
        maxValue,
        numberText(value, 3),
        value < 0,
      ),
    );
  });
}

function renderBusinessImpact() {
  const reviewCostUsd = 8;
  const avoidedFraudLossUsd = 500;
  const champion = state.dashboard.metrics.champion;
  const existing = state.dashboard.metrics.existing_alert_benchmark;

  const championReviews = Number(champion.test_review_count);
  const existingReviews =
    Number(existing.true_positives) + Number(existing.false_positives);
  const incrementalReviews = championReviews - existingReviews;
  const incrementalFraudCaught =
    Number(champion.test_true_positives) - Number(existing.true_positives);
  const incrementalReviewSpend = incrementalReviews * reviewCostUsd;
  const incrementalAvoidedLoss = incrementalFraudCaught * avoidedFraudLossUsd;
  const netImpact = incrementalAvoidedLoss - incrementalReviewSpend;

  document.getElementById("incrementalFraudCaught").textContent =
    signedCount(incrementalFraudCaught);
  document.getElementById("incrementalReviews").textContent =
    signedCount(incrementalReviews);
  document.getElementById("incrementalReviewSpend").textContent =
    moneyText(incrementalReviewSpend);
  document.getElementById("illustrativeNetImpact").textContent =
    moneyText(netImpact);
  document.getElementById("economicsNote").textContent =
    `Illustrative sensitivity: ${moneyText(reviewCostUsd)} review cost per case and ${moneyText(avoidedFraudLossUsd)} avoided loss per captured fraud. Synthetic data only.`;
}

function renderDashboard() {
  renderQueue();
  renderAnalystMetrics();
  renderPilotRecommendation();
  renderCapacityThresholds();
  renderGlobalImportance();
  renderBusinessImpact();
  document.getElementById("governanceThreshold").textContent =
    state.model.threshold.toFixed(3);
  document.getElementById("governanceCapacity").textContent =
    `${Math.round(state.model.target_capacity_rate * 100)}%`;
}

async function boot() {
  const [modelResponse, dashboardResponse] = await Promise.all([
    fetch("./model.json"),
    fetch("./dashboard-data.json"),
  ]);
  state.model = await modelResponse.json();
  state.dashboard = await dashboardResponse.json();
  initializeTabs();
  initializeForm(state.model);
  renderDashboard();
  scoreCurrentForm();
}

boot();
