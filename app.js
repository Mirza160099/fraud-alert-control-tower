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

function numberText(value, digits = 3) {
  return Number(value).toFixed(digits);
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
  const { estimator_weights: weights, trees } = model.adaboost;
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
  if (probability >= Math.max(0.8, threshold)) return "Critical";
  if (probability >= Math.max(0.6, threshold)) return "High";
  if (probability >= threshold) return "Standard Review";
  return "Monitor";
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

function renderFeatureBars(deltas) {
  const featureBars = document.getElementById("featureBars");
  featureBars.replaceChildren();
  const visible = deltas
    .slice()
    .sort((a, b) => b.absoluteDelta - a.absoluteDelta)
    .slice(0, 6);
  const maxDelta = Math.max(...visible.map((item) => item.absoluteDelta), 0.001);

  visible.forEach((item) => {
    featureBars.appendChild(
      buildBarRow(
        featureLabels[item.feature] ?? item.feature,
        item.absoluteDelta,
        maxDelta,
        `${item.delta >= 0 ? "+" : ""}${item.delta.toFixed(3)}`,
        item.delta < 0,
      ),
    );
  });
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
  const threshold = state.model.threshold;
  const isReview = probability >= threshold;
  const badge = document.getElementById("decisionBadge");
  badge.className = `decision-badge ${
    priority === "Critical" ? "critical" : isReview ? "review" : "monitor"
  }`;

  document.getElementById("decisionText").textContent = isReview
    ? "Review as fraud risk"
    : "Monitor as likely legitimate";
  document.getElementById("probabilityText").textContent = probability.toFixed(3);
  document.getElementById("priorityText").textContent = priority;
}

function scoreCurrentForm() {
  const input = readFormInput();
  const probability = predictProbability(input);
  const priority = classifyPriority(probability, state.model.threshold);
  const deltas = localDeltas(input);

  renderDecision(probability, priority);
  renderReasons(deltas);
  renderFeatureBars(deltas);
}

function loadHighRiskScenario() {
  document.getElementById("amount").value = "240";
  document.getElementById("currency").value = "USD";
  document.getElementById("txn_country").value = "BR";
  document.getElementById("channel").value = "P2P";
  document.getElementById("txn_hour").value = "4";
  document.getElementById("geo_distance_km").value = "4200";
  document.getElementById("device_risk_score").value = "0.72";
  document.getElementById("synthetic_identity_score").value = "0.44";
  document.getElementById("merchant_risk_score").value = "0.58";
  document.getElementById("merchant_profile_risk_score").value = "0.55";
  scoreCurrentForm();
}

function initializeForm(model) {
  const countrySchema = model.feature_schema.txn_country;
  const channelSchema = model.feature_schema.channel;
  populateSelect("txn_country", countrySchema.categories, "BR");
  populateSelect("channel", channelSchema.categories, "P2P");
  populateSelect("currency", Object.keys(model.currency_rates_to_usd), "USD");

  document.getElementById("modelName").textContent = model.model_name.replaceAll("_", " ");
  document.getElementById("thresholdLabel").textContent = `Threshold ${model.threshold.toFixed(3)}`;
  document.getElementById("capacityText").textContent = `${Math.round(model.target_capacity_rate * 100)}%`;

  document.getElementById("transactionForm").addEventListener("submit", (event) => {
    event.preventDefault();
    scoreCurrentForm();
  });
  document.getElementById("transactionForm").addEventListener("input", scoreCurrentForm);
  document.getElementById("transactionForm").addEventListener("change", scoreCurrentForm);
  document.getElementById("loadScenario").addEventListener("click", loadHighRiskScenario);
}

function initializeTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      const tabName = button.dataset.tab;
      document.querySelectorAll(".tab-button").forEach((tabButton) => {
        tabButton.classList.toggle("active", tabButton === button);
      });
      document.querySelectorAll(".tab-view").forEach((view) => {
        view.classList.toggle("active", view.id === `${tabName}View`);
      });
    });
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

  const caseList = document.getElementById("caseList");
  caseList.replaceChildren();

  state.dashboard.top_queue_cases.forEach((caseItem) => {
    const row = document.createElement("article");
    row.className = "case-card";

    const header = document.createElement("div");
    header.className = "case-header";
    header.innerHTML = `
      <div>
        <span class="muted-label">Transaction</span>
        <strong>${caseItem.transaction_id}</strong>
      </div>
      <div class="case-score">${numberText(caseItem.predicted_fraud_probability, 3)}</div>
    `;

    const meta = document.createElement("div");
    meta.className = "case-meta";
    meta.innerHTML = `
      <span>${caseItem.priority_tier}</span>
      <span>${Number(caseItem.actual_fraud_label) === 1 ? "Backtest: true fraud" : "Backtest: false positive"}</span>
      <span>${Number(caseItem.alert_generated) === 1 ? "Old alert: yes" : "Old alert: no"}</span>
    `;

    const reason = document.createElement("p");
    reason.textContent = caseItem.reason_1
      ? `${caseItem.reason_1.charAt(0).toUpperCase()}${caseItem.reason_1.slice(1)}`
      : "";

    row.append(header, meta, reason);
    caseList.appendChild(row);
  });
}

function renderModelComparison() {
  const tbody = document.getElementById("modelComparisonRows");
  tbody.replaceChildren();

  state.dashboard.model_comparison.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.model_name.replaceAll("_", " ")}</td>
      <td>${percent(row.test_precision)}</td>
      <td>${percent(row.test_recall)}</td>
      <td>${numberText(row.test_average_precision_pr_auc, 3)}</td>
      <td>${row.test_review_count}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCapacityThresholds() {
  const tbody = document.getElementById("capacityRows");
  tbody.replaceChildren();
  const rows = state.dashboard.capacity_thresholds.filter(
    (row) => Number(row.target_capacity_rate) === 0.05,
  ).sort((a, b) => Number(b.validation_f1) - Number(a.validation_f1));

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.model_name.replaceAll("_", " ")}</td>
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
  const visible = state.dashboard.global_feature_importance.slice(0, 8);
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

function renderDashboard() {
  renderQueue();
  renderModelComparison();
  renderCapacityThresholds();
  renderGlobalImportance();
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
