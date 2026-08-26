"use strict";

const SAMPLE = {
  program: "Enterprise AI Support Copilot",
  objective: "Launch a governed support copilot that improves answer quality while keeping policy decisions accountable to human owners.",
  target_date: "2026-11-20",
  executive_owner: "VP, Customer Experience",
  assumptions: [
    "Security review capacity remains available through pilot readiness.",
    "The approved knowledge corpus is available before retrieval evaluation."
  ],
  decisions: [
    { decision: "Approve first-market scope and quality gate", owner: "VP, Customer Experience", due: "2026-09-15" },
    { decision: "Select production model provider", owner: "AI Platform Lead", due: "2026-09-30" }
  ],
  risks: [
    { risk: "Policy regressions reach customer-facing responses", severity: "high", owner: "Responsible AI Lead", mitigation: "Block pilot on critical-policy eval failures." },
    { risk: "Retrieval latency misses the support SLA", severity: "medium", owner: "AI Platform Lead", mitigation: "Benchmark p95 latency before integration freeze." }
  ],
  workstreams: [
    {
      id: "WS1", title: "Requirements and policy contract", owner: "Maya Chen", team: "Product + Responsible AI",
      window: "Sep 01–Sep 18", status: "in progress", depends_on: [],
      deliverables: ["Approved use cases", "Policy test set"], risks: []
    },
    {
      id: "WS2", title: "Retrieval and orchestration platform", owner: "Alex Rivera", team: "AI Platform",
      window: "Sep 14–Oct 16", status: "planned", depends_on: ["WS1"],
      deliverables: ["Versioned retrieval API", "Trace instrumentation"], risks: ["Source freshness SLA is not yet agreed"]
    },
    {
      id: "WS3", title: "Quality evaluation", owner: "Priya Shah", team: "ML Quality",
      window: "Oct 05–Oct 30", status: "planned", depends_on: ["WS1", "WS2"],
      deliverables: ["Offline eval report", "Human calibration results"], risks: []
    },
    {
      id: "WS4", title: "Pilot readiness", owner: "Jordan Brooks", team: "Support Operations",
      window: "Nov 02–Nov 20", status: "planned", depends_on: ["WS2", "WS3"],
      deliverables: ["Agent training", "Rollback runbook", "Launch decision"], risks: []
    }
  ]
};

const $ = (selector) => document.querySelector(selector);
const input = $("#programInput");
const compileButton = $("#compileButton");
const approvalToggle = $("#approvalToggle");
const errorBox = $("#errorBox");
const outputEmpty = $("#outputEmpty");
const outputReady = $("#outputReady");
const runState = $("#runState");
let generated = {};
let activeArtifact = "roadmap.md";

function loadSample() {
  input.value = JSON.stringify(SAMPLE, null, 2);
  updateCount();
  errorBox.hidden = true;
  input.focus();
}

function updateCount() {
  $("#charCount").textContent = `${input.value.length.toLocaleString()} chars`;
}

function validateProgram(data) {
  if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Input root must be a JSON object.");
  ["program", "objective", "target_date", "workstreams"].forEach((field) => {
    if (!data[field]) throw new Error(`Missing required field: ${field}`);
  });
  if (!Array.isArray(data.workstreams) || !data.workstreams.length) throw new Error("workstreams must be a non-empty array.");

  const ids = [];
  data.workstreams.forEach((item, index) => {
    if (!item || Array.isArray(item) || typeof item !== "object") throw new Error(`workstreams[${index}] must be an object.`);
    ["id", "title", "owner", "team"].forEach((field) => {
      if (!item[field]) throw new Error(`workstreams[${index}] missing ${field}.`);
    });
    ids.push(item.id);
  });
  if (new Set(ids).size !== ids.length) throw new Error("Workstream IDs must be unique.");
  const known = new Set(ids);
  const graph = {};
  data.workstreams.forEach((item) => {
    const dependencies = item.depends_on || [];
    if (!Array.isArray(dependencies)) throw new Error(`${item.id}.depends_on must be an array.`);
    const unknown = dependencies.filter((id) => !known.has(id));
    if (unknown.length) throw new Error(`${item.id} has unknown dependencies: ${unknown.join(", ")}.`);
    graph[item.id] = dependencies;
  });
  rejectCycles(graph);
}

function rejectCycles(graph) {
  const visiting = new Set();
  const visited = new Set();
  function visit(node) {
    if (visiting.has(node)) throw new Error(`Dependency cycle detected at ${node}.`);
    if (visited.has(node)) return;
    visiting.add(node);
    graph[node].forEach(visit);
    visiting.delete(node);
    visited.add(node);
  }
  Object.keys(graph).forEach(visit);
}

function allRisks(data) {
  const risks = [...(data.risks || [])];
  data.workstreams.forEach((workstream) => {
    (workstream.risks || []).forEach((risk) => risks.push({
      risk: typeof risk === "string" ? risk : (risk.risk || "Unspecified risk"),
      owner: workstream.owner,
      severity: typeof risk === "object" && risk.severity ? risk.severity : "medium",
      mitigation: typeof risk === "object" && risk.mitigation ? risk.mitigation : "Owner to define mitigation before execution."
    }));
  });
  return risks;
}

function compileArtifacts(data, approved) {
  const started = performance.now();
  const status = approved ? "APPROVED FOR PLANNING" : "DRAFT — HUMAN REVIEW REQUIRED";
  const risks = allRisks(data);
  const blocked = data.workstreams.filter((item) => (item.status || "planned").toLowerCase() === "blocked");
  const artifacts = {
    "roadmap.md": roadmap(data, status),
    "dependencies.mmd": dependencies(data),
    "raid-log.md": raidLog(data, status, risks),
    "executive-brief.md": executiveBrief(data, status, risks, blocked)
  };
  const metrics = {
    workstreams: data.workstreams.length,
    dependencies: data.workstreams.reduce((sum, item) => sum + (item.depends_on || []).length, 0),
    blocked_workstreams: blocked.length,
    open_risks: risks.length,
    human_review: !approved,
    latency_ms: Number((performance.now() - started).toFixed(2)),
    estimated_model_cost_usd: 0
  };
  artifacts["run-metrics.json"] = JSON.stringify(metrics, null, 2) + "\n";
  artifacts["trace.jsonl"] = JSON.stringify({
    timestamp: new Date().toISOString(), event: "artifact_generation_completed", program: data.program,
    output_count: 4, review_status: status, metrics
  }) + "\n";
  return { artifacts, metrics, status };
}

function roadmap(data, status) {
  const rows = data.workstreams.map((item) =>
    `| ${item.id} | ${item.title} | ${item.owner} / ${item.team} | ${item.window || "TBD"} | ${(item.depends_on || []).join(", ") || "None"} | ${item.status || "planned"} | ${(item.deliverables || []).join("; ") || "TBD"} |`
  ).join("\n");
  return `# Roadmap: ${data.program}\n\n> **${status}**\n\n**Objective:** ${data.objective}  \n**Target date:** ${data.target_date}  \n**Executive owner:** ${data.executive_owner || "TBD"}\n\n| ID | Workstream | Owner / team | Window | Depends on | Status | Exit criteria |\n|---|---|---|---|---|---|---|\n${rows}\n\n## Operating cadence\n\n- Weekly dependency and RAID review\n- Biweekly executive decision review\n- Launch-readiness gate before production exposure\n- Human approval required for scope, sequencing, and risk acceptance\n`;
}

function dependencies(data) {
  const nodes = data.workstreams.map((item) => `  ${item.id}["${item.id}: ${item.title.replaceAll('"', "'")}"]`);
  const edges = data.workstreams.flatMap((item) => (item.depends_on || []).map((dependency) => `  ${dependency} --> ${item.id}`));
  return ["flowchart LR", ...nodes, ...edges].join("\n") + "\n";
}

function raidLog(data, status, risks) {
  const riskRows = risks.length ? risks.map((risk, index) =>
    `| R${String(index + 1).padStart(2, "0")} | ${risk.risk || "Unspecified"} | ${risk.severity || "medium"} | ${risk.owner || "TBD"} | ${risk.mitigation || "TBD"} | Open |`
  ).join("\n") : "| — | No risks supplied; validate in review | — | Program lead | Run risk workshop | Open |";
  const assumptions = data.assumptions || ["Resourcing remains available through target date."];
  const assumptionRows = assumptions.map((text, index) => `| A${String(index + 1).padStart(2, "0")} | ${text} | Program lead | Validate |`).join("\n");
  const decisions = data.decisions || [];
  const decisionRows = decisions.length ? decisions.map((item, index) =>
    `| D${String(index + 1).padStart(2, "0")} | ${item.decision || "TBD"} | ${item.owner || "TBD"} | ${item.due || "TBD"} | Open |`
  ).join("\n") : "| D01 | Approve roadmap and risk posture | Executive owner | Before kickoff | Open |";
  return `# RAID Log: ${data.program}\n\n> **${status}**\n\n## Risks\n\n| ID | Risk | Severity | Owner | Mitigation | Status |\n|---|---|---|---|---|---|\n${riskRows}\n\n## Assumptions\n\n| ID | Assumption | Owner | Validation |\n|---|---|---|---|\n${assumptionRows}\n\n## Decisions\n\n| ID | Decision | Owner | Due | Status |\n|---|---|---|---|---|\n${decisionRows}\n`;
}

function executiveBrief(data, status, risks, blocked) {
  const blockedNames = blocked.map((item) => item.title).join(", ") || "None";
  const decisionText = (data.decisions || []).map((item) => item.decision || "TBD").join("; ") || "Approve scope and risk posture.";
  return `# Executive Brief: ${data.program}\n\n> **${status}**\n\n## Outcome\n\n${data.objective}\n\n## Delivery posture\n\n- Target: **${data.target_date}**\n- Workstreams: **${data.workstreams.length}**\n- Blocked: **${blocked.length}** (${blockedNames})\n- Open risks: **${risks.length}**\n\n## Decisions needed\n\n${decisionText}\n\n## Leadership ask\n\nConfirm sequencing, named owners, and risk acceptance before the plan is used for execution.\n`;
}

function showArtifact(name) {
  activeArtifact = name;
  $("#artifactName").textContent = name;
  $("#artifactPreview").textContent = generated[name];
  document.querySelectorAll("#artifactTabs button").forEach((button) => button.classList.toggle("active", button.dataset.name === name));
}

function render(result) {
  generated = result.artifacts;
  outputEmpty.hidden = true;
  outputReady.hidden = false;
  $("#metricStrip").innerHTML = [
    [result.metrics.workstreams, "workstreams"],
    [result.metrics.dependencies, "dependencies"],
    [result.metrics.open_risks, "open risks"],
    [`${result.metrics.latency_ms} ms`, "browser runtime"]
  ].map(([value, label]) => `<div><strong>${value}</strong><span>${label}</span></div>`).join("");
  const tabs = $("#artifactTabs");
  tabs.innerHTML = "";
  Object.keys(generated).forEach((name) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.name = name;
    button.textContent = name;
    button.addEventListener("click", () => showArtifact(name));
    tabs.appendChild(button);
  });
  showArtifact("roadmap.md");
  runState.dataset.state = "complete";
  runState.innerHTML = `<span></span>${result.status}`;
}

function compile() {
  errorBox.hidden = true;
  try {
    const data = JSON.parse(input.value);
    validateProgram(data);
    render(compileArtifacts(data, approvalToggle.checked));
  } catch (error) {
    errorBox.textContent = error instanceof SyntaxError ? `Invalid JSON: ${error.message}` : error.message;
    errorBox.hidden = false;
    runState.dataset.state = "error";
    runState.innerHTML = "<span></span>Input rejected";
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let crc = 0xffffffff;
  bytes.forEach((byte) => { crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8); });
  return (crc ^ 0xffffffff) >>> 0;
}

function u16(value) { return new Uint8Array([value & 255, (value >>> 8) & 255]); }
function u32(value) { return new Uint8Array([value & 255, (value >>> 8) & 255, (value >>> 16) & 255, (value >>> 24) & 255]); }
function concat(parts) {
  const output = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
  let offset = 0;
  parts.forEach((part) => { output.set(part, offset); offset += part.length; });
  return output;
}

function buildZip(files) {
  const encoder = new TextEncoder();
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  Object.entries(files).forEach(([name, content]) => {
    const nameBytes = encoder.encode(name);
    const data = encoder.encode(content);
    const crc = crc32(data);
    const local = concat([u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(0), u16(0), u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length), u16(0), nameBytes, data]);
    localParts.push(local);
    centralParts.push(concat([u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(0), u16(0), u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(offset), nameBytes]));
    offset += local.length;
  });
  const locals = concat(localParts);
  const central = concat(centralParts);
  const end = concat([u32(0x06054b50), u16(0), u16(0), u16(centralParts.length), u16(centralParts.length), u32(central.length), u32(locals.length), u16(0)]);
  return new Blob([locals, central, end], { type: "application/zip" });
}

$("#sampleButton").addEventListener("click", loadSample);
$("#fileInput").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  input.value = await file.text();
  updateCount();
});
input.addEventListener("input", updateCount);
compileButton.addEventListener("click", compile);
approvalToggle.addEventListener("change", () => { if (!outputReady.hidden) compile(); });
$("#copyButton").addEventListener("click", async () => {
  await navigator.clipboard.writeText(generated[activeArtifact]);
  $("#copyButton").textContent = "Copied";
  setTimeout(() => { $("#copyButton").textContent = "Copy"; }, 1200);
});
$("#downloadButton").addEventListener("click", () => downloadBlob(buildZip(generated), "agentic-program-ops-plan.zip"));
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") compile();
});

loadSample();
