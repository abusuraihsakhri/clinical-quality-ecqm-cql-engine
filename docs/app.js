const PYODIDE_INDEX = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const PYTHON_FILES = [
  "ecqm_cql_engine/__init__.py",
  "ecqm_cql_engine/models.py",
  "ecqm_cql_engine/engine.py",
];

let pyodide = null;

const byId = (id) => document.getElementById(id);

function setRuntimeStatus(message, state = "") {
  const node = byId("runtimeStatus");
  node.textContent = message;
  node.classList.remove("ready", "error");
  if (state) node.classList.add(state);
}

async function loadEngine() {
  try {
    setRuntimeStatus("Loading Python…");
    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX });
    pyodide.FS.mkdirTree("/home/pyodide/ecqm_cql_engine");

    for (const path of PYTHON_FILES) {
      const response = await fetch("./" + path, { cache: "no-cache" });
      if (!response.ok) {
        throw new Error("Could not load " + path + " (" + response.status + ")");
      }
      const source = await response.text();
      pyodide.FS.writeFile("/home/pyodide/" + path, source);
    }

    await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/home/pyodide")
from ecqm_cql_engine import CQLEquivalentEngine
`);

    byId("analyze").disabled = false;
    setRuntimeStatus("Python ready", "ready");
  } catch (error) {
    console.error(error);
    setRuntimeStatus("Runtime failed", "error");
    byId("analyze").disabled = true;
    byId("resultHint").textContent = "Python runtime failed to load. Check the network connection and reload the page.";
  }
}

function maybePush(list, item, requiredKey) {
  if (item[requiredKey]) list.push(item);
}

function buildPatientPayload() {
  const observations = [];
  for (const suffix of ["", "2"]) {
    const code = byId("observationCode" + suffix).value.trim();
    if (!code) continue;
    const rawValue = byId("observationValue" + suffix).value.trim();
    let value = rawValue;
    if (rawValue !== "" && Number.isFinite(Number(rawValue))) value = Number(rawValue);
    observations.push({
      code,
      value,
      date: byId("observationDate" + suffix).value || "2026-06-01",
    });
  }

  const patient = {
    patient_id: byId("patientId").value.trim() || "PT-DEMO-01",
    birth_date: byId("birthDate").value,
    gender: byId("gender").value,
    encounters: [],
    conditions: [],
    observations,
    procedures: [],
    medications: [],
  };

  maybePush(patient.encounters, {
    encounter_type: "ambulatory",
    code: byId("encounterCode").value.trim(),
    code_system: "CPT",
    period_start: byId("encounterDate").value || "2026-06-01",
  }, "code");

  maybePush(patient.conditions, {
    code: byId("conditionCode").value.trim(),
    code_system: "ICD-10-CM",
    onset_date: byId("conditionDate").value || "2020-01-01",
    clinical_status: "active",
  }, "code");

  maybePush(patient.procedures, {
    code: byId("procedureCode").value.trim(),
    code_system: "CPT",
    performed_date: byId("procedureDate").value || "2026-06-01",
  }, "code");

  maybePush(patient.medications, {
    code: byId("medicationCode").value.trim(),
    code_system: "RxNorm",
    authored_date: byId("medicationDate").value || "2026-06-01",
  }, "code");

  return patient;
}

function addMetric(container, label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const definition = document.createElement("dd");
  term.textContent = label;
  definition.textContent = String(value);
  wrapper.append(term, definition);
  container.append(wrapper);
}

function renderResult(score) {
  const patientResult = score.patient_evaluations[0];
  const status = patientResult.in_numerator
    ? "Numerator met"
    : patientResult.is_gap_in_care
      ? "Gap in care"
      : patientResult.in_denominator_exclusion
        ? "Excluded"
        : patientResult.in_initial_population
          ? "In denominator"
          : "Not in population";

  byId("resultEmpty").hidden = true;
  byId("resultContent").hidden = false;
  byId("resultStatus").textContent = status;
  byId("resultMeasure").textContent = score.measure_id + " · " + score.measure_title;
  byId("resultRate").textContent = score.performance_rate_pct.toFixed(1) + "%";

  const metrics = byId("populationGrid");
  metrics.replaceChildren();
  addMetric(metrics, "Initial population", patientResult.in_initial_population ? "Yes" : "No");
  addMetric(metrics, "Denominator", patientResult.in_denominator ? "Yes" : "No");
  addMetric(metrics, "Numerator", patientResult.in_numerator ? "Yes" : "No");
  addMetric(metrics, "Care gap", patientResult.is_gap_in_care ? "Yes" : "No");

  const rationale = byId("rationaleList");
  rationale.replaceChildren();
  for (const text of patientResult.rationale) {
    const item = document.createElement("li");
    item.textContent = text;
    rationale.append(item);
  }
}

function renderError(error) {
  byId("resultEmpty").hidden = false;
  byId("resultContent").hidden = true;
  const empty = byId("resultEmpty");
  empty.replaceChildren();
  const strong = document.createElement("strong");
  const span = document.createElement("span");
  strong.textContent = "Evaluation failed";
  span.textContent = error instanceof Error ? error.message : String(error);
  empty.append(strong, span);
}

async function evaluatePatient(event) {
  event.preventDefault();
  if (!pyodide) return;

  const button = byId("analyze");
  button.disabled = true;
  button.textContent = "Analyzing…";

  try {
    const payload = {
      measure: byId("measure").value,
      patient: buildPatientPayload(),
    };
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const jsonResult = await pyodide.runPythonAsync(`
import json
from ecqm_cql_engine import CQLEquivalentEngine, MeasurementPeriod, parse_patient_dict

_payload = json.loads(payload_json)
_patient = parse_patient_dict(_payload["patient"])
_score = CQLEquivalentEngine.evaluate_population_cohort(
    _payload["measure"], [_patient], MeasurementPeriod()
)
json.dumps(_score.to_dict())
`);
    renderResult(JSON.parse(jsonResult));
  } catch (error) {
    console.error(error);
    renderError(error);
  } finally {
    button.disabled = false;
    button.textContent = "Analyze";
  }
}

function loadExample() {
  const measure = byId("measure").value;
  const defaults = {
    CMS130v11: { gender: "female", condition: "", obs: "", value: "", obs2: "", value2: "", proc: "45378", procDate: "2024-01-01", med: "" },
    CMS122v11: { gender: "male", condition: "E11.9", obs: "4548-4", value: "7.2", obs2: "", value2: "", proc: "", procDate: "2026-06-01", med: "metformin" },
    CMS125v11: { gender: "female", condition: "", obs: "", value: "", obs2: "", value2: "", proc: "77067", procDate: "2025-08-10", med: "" },
    CMS165v11: { gender: "male", condition: "I10", obs: "8480-6", value: "128", obs2: "8462-4", value2: "82", proc: "", procDate: "2026-06-01", med: "amlodipine" },
    CMS68v12: { gender: "female", condition: "", obs: "", value: "", obs2: "", value2: "", proc: "", procDate: "2026-06-01", med: "atorvastatin" },
  }[measure];

  byId("patientId").value = "PT-DEMO-01";
  byId("birthDate").value = measure === "CMS125v11" ? "1965-05-12" : "1960-01-01";
  byId("gender").value = defaults.gender;
  byId("encounterCode").value = "99213";
  byId("encounterDate").value = "2026-06-01";
  byId("conditionCode").value = defaults.condition;
  byId("conditionDate").value = "2020-01-01";
  byId("observationCode").value = defaults.obs;
  byId("observationValue").value = defaults.value;
  byId("observationDate").value = "2026-06-01";
  byId("observationCode2").value = defaults.obs2;
  byId("observationValue2").value = defaults.value2;
  byId("observationDate2").value = "2026-06-01";
  byId("procedureCode").value = defaults.proc;
  byId("procedureDate").value = defaults.procDate;
  byId("medicationCode").value = defaults.med;
  byId("medicationDate").value = "2026-06-01";

  byId("resultHint").textContent = "Run an evaluation to see population status and rationale.";
}

function clearClinicalData() {
  for (const id of ["conditionCode", "observationCode", "observationValue", "observationCode2", "observationValue2", "procedureCode", "medicationCode"]) {
    byId(id).value = "";
  }
}

function toggleTheme() {
  const root = document.documentElement;
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("theme", next);
  byId("themeToggle").setAttribute("aria-label", "Switch to " + (next === "dark" ? "light" : "dark") + " theme");
}

function initializeTheme() {
  const saved = localStorage.getItem("theme");
  const preferredDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = saved || (preferredDark ? "dark" : "light");
}

document.addEventListener("DOMContentLoaded", () => {
  initializeTheme();
  byId("patientForm").addEventListener("submit", evaluatePatient);
  byId("themeToggle").addEventListener("click", toggleTheme);
  byId("loadExample").addEventListener("click", loadExample);
  byId("clearForm").addEventListener("click", clearClinicalData);
  byId("measure").addEventListener("change", loadExample);
  loadExample();
  loadEngine();
});
