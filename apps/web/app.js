"use strict";
const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const dateText = (value) =>
  new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
const localDate = () => {
  const d = new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
};
const categoryLabel = (value) =>
  ({
    ppe_noncompliance: "PPE",
    fall: "Access & falls",
    electrical: "Electrical",
    fire: "Fire",
    chemical: "Chemical",
    other: "General",
  })[value] || value;
const scrollBehavior = () =>
  matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
const statusLabel = (value) =>
  ({ open: "Open", in_progress: "In progress", closed: "Closed" })[value] ||
  value;
const ago = (days) => new Date(Date.now() - days * 86400000).toISOString();
function sampleData() {
  const rows = [
    [
      "s1",
      "A worker slipped on a wet access platform and suffered a fracture. The area has been isolated for review.",
      "Access platform",
      "fall",
      "medium",
      55,
      0,
    ],
    [
      "s2",
      "An exposed electrical wire was found beside the loading area. No contact or injury was reported.",
      "Loading bay",
      "electrical",
      "medium",
      55,
      1,
    ],
    [
      "s3",
      "An operator was observed without a hardhat at the designated PPE entry point. The supervisor was notified.",
      "North entry",
      "ppe_noncompliance",
      "low",
      25,
      1,
    ],
    [
      "s4",
      "Smoke and severe burns were reported near a maintenance station. The site emergency procedure was activated.",
      "Maintenance zone",
      "fire",
      "high",
      85,
      2,
    ],
  ];
  return {
    id: "sample",
    observations: rows.map(
      ([id, text, location, category, severity, risk_score, days]) => ({
        id,
        text,
        location,
        created_at: ago(days),
        assessment: {
          category,
          severity,
          risk_score,
          model_source: "rules",
          rule_version: "2026-11-09.1",
          reasons: [
            "Synthetic example. Review actual site conditions with the responsible person.",
          ],
          score_breakdown: {
            severity_points: risk_score,
            recurrence_points: 0,
            related_observations_7d: 0,
          },
          suggested_action:
            "Review controls and document the follow-up inspection",
          runbook_markdown:
            "Example response reference. Use the applicable site procedure and a competent-person review.",
        },
      }),
    ),
    actions: [
      {
        id: "a1",
        observation_id: "s1",
        title: "Inspect the access platform and verify housekeeping controls",
        owner: "Site supervisor",
        due_date: localDate(),
        status: "in_progress",
        closure_note: "",
        revision: 1,
        history: [
          { status: "open", at: ago(1) },
          { status: "in_progress", at: ago(0) },
        ],
        created_at: ago(1),
      },
      {
        id: "a2",
        observation_id: "s2",
        title: "Arrange a competent-person review of the electrical controls",
        owner: "Maintenance lead",
        due_date: new Date(Date.now() - 86400000).toISOString().slice(0, 10),
        status: "open",
        closure_note: "",
        revision: 1,
        history: [],
        created_at: ago(1),
      },
      {
        id: "a3",
        observation_id: "s3",
        title: "Verify PPE availability at the entry point",
        owner: "Shift coordinator",
        due_date: localDate(),
        status: "closed",
        closure_note:
          "Entry-point equipment checked and inspection recorded in the site log.",
        revision: 2,
        history: [{ status: "closed", at: ago(0) }],
        created_at: ago(1),
      },
    ],
  };
}
let demo = true,
  data = sampleData(),
  selected = "s1",
  view = "overview",
  toastTimer,
  loading = true;
const errors = [];
function toast(message) {
  $("toast").textContent = message;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").textContent = ""), 5500);
}
async function api(path = "", options = {}) {
  const response = await fetch("/api/workspace" + path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {}
    const error = new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((e) => e.msg).join("; ")
          : "The service is unavailable. Your form is still here; try again.",
    );
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
async function refresh() {
  data = await api();
  demo = false;
  history.replaceState(null, "", location.pathname);
  if (!data.observations.some((x) => x.id === selected))
    selected = data.observations[0]?.id || null;
  render();
}
async function createWorkspace() {
  await api("", { method: "POST" });
  await refresh();
  toast("Your private workspace is ready. Add the first observation.");
}
function fail(error, target = "global-error") {
  $(target).textContent = error.message;
  errors.push(error.message);
}
function clearError(target = "global-error") {
  $(target).textContent = "";
}
function isOverdue(a) {
  return a.status !== "closed" && a.due_date < localDate();
}
function render() {
  const actionFocus = Boolean(document.activeElement?.closest(".action-row"));
  const formFocus = Boolean(document.activeElement?.closest("#action-form"));
  $("workspace-label").textContent = demo
    ? "Sample workspace / synthetic records"
    : "Personal workspace / saved to database";
  $("mode-banner").innerHTML = demo
    ? '<p>Sample workspace · All records are synthetic. Changes stay in this demo.</p><button class="button small" id="create-workspace">Create my workspace</button>'
    : '<p>Your workspace is saved in the database. Keep this browser’s cookies and export regularly.</p><button class="mode-button" data-view="handover">Export handover ↗</button>';
  $("assess-button").textContent = demo
    ? "Create workspace & assess ↗"
    : "Assess & save observation ↗";
  const open = data.actions.filter((a) => a.status !== "closed"),
    overdue = open.filter(isOverdue),
    closed = data.actions.length - open.length;
  $("stats").innerHTML =
    `<div class="stat"><strong>${data.observations.length}</strong><span>Observations recorded</span></div><div class="stat"><strong>${open.length}</strong><span>Actions to follow up</span></div><div class="stat"><strong class="${overdue.length ? "red" : ""}">${overdue.length}</strong><span>Actions overdue</span></div><div class="stat"><strong>${closed}</strong><span>Actions closed with evidence</span></div>`;
  renderList();
  renderDetail();
  renderActions();
  $("handover-preview").textContent = handover();
  $("toggle-demo").textContent = demo
    ? "Return to my workspace"
    : "Explore sample workspace";
  $("delete-workspace").disabled = demo;
  if (actionFocus || formFocus) {
    const target = formFocus
      ? $("detail-panel")
      : view === "actions"
        ? $("view-title")
        : $("next-actions");
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
  }
}
function renderList() {
  const query = $("search").value.toLowerCase(),
    severity = $("severity-filter").value;
  const rows = data.observations.filter(
    (x) =>
      (severity === "all" || x.assessment.severity === severity) &&
      `${x.text} ${x.location}`.toLowerCase().includes(query),
  );
  $("register-count").textContent =
    `${rows.length} of ${data.observations.length}`;
  $("observation-list").innerHTML = rows.length
    ? rows
        .map(
          (x) =>
            `<button class="observation-row ${x.id === selected ? "selected" : ""}" data-observation="${esc(x.id)}" aria-pressed="${x.id === selected}"><div class="row-top"><span class="pill ${esc(x.assessment.severity)}">${esc(x.assessment.severity)} severity</span><span class="row-meta">${dateText(x.created_at)}</span></div><div class="row-title">${esc(x.text)}</div><div class="row-bottom"><span>${esc(x.location)} · ${esc(categoryLabel(x.assessment.category))}</span><span class="row-priority">${x.assessment.risk_score}/100</span></div></button>`,
        )
        .join("")
    : `<div class="empty"><h3>${data.observations.length ? "No matching observations." : "A clear starting point."}</h3><p>${data.observations.length ? "Change the search or severity filter." : "Capture the first observation. Its assessment and follow-up actions will stay here."}</p></div>`;
}
function renderDetail() {
  const row = data.observations.find((x) => x.id === selected);
  if (!row) {
    $("observation-detail").innerHTML =
      '<p class="muted" style="font-size:14px">Select an observation to see its assessment rationale and add a corrective action.</p>';
    return;
  }
  const a = row.assessment,
    b = a.score_breakdown;
  $("observation-detail").innerHTML =
    `<div class="detail-heading"><span class="pill ${esc(a.severity)}">${esc(a.severity)} severity</span><strong>${a.risk_score}<span class="small-copy"> / 100</span></strong></div><p class="detail-text">${esc(row.text)}</p><div class="detail-facts"><strong>Why this priority?</strong><ul>${a.reasons.map((x) => `<li>${esc(x)}</li>`).join("")}</ul><div>${b.severity_points} severity + ${b.recurrence_points} recurrence points</div><div>${b.related_observations_7d} related observations in the previous 7 days</div><p class="hint" style="margin:10px 0 0">Severity source: ${a.model_source === "distilbert" ? "DistilBERT model" : "Rule-based fallback"} · Category: rules<br>Rules ${esc(a.rule_version)} · Human review required</p></div><details class="runbook"><summary>Response runbook reference</summary><pre>${esc(a.runbook_markdown)}</pre></details><h3 style="font-size:16px;margin-bottom:16px">Give the next step an owner.</h3><form id="action-form"><label for="action-title">Corrective action</label><textarea id="action-title" required minlength="3" maxlength="300" style="min-height:80px">${esc(a.suggested_action)}</textarea><label for="action-owner" style="margin-top:12px">Owner / responsible role</label><input id="action-owner" required minlength="2" maxlength="120" placeholder="e.g. Site supervisor"><label for="action-due" style="margin-top:12px">Due date</label><input id="action-due" type="date" value="${localDate()}" required><button class="button small" type="submit">${demo ? "Try adding a sample action" : "Add corrective action"}</button><div class="error" id="action-error" role="alert"></div></form>`;
}
function actionHTML(action, scope = "next") {
  const observation = data.observations.find(
      (x) => x.id === action.observation_id,
    ),
    closed = action.status === "closed";
  return `<article class="action-row"><div class="row-top"><span class="pill ${isOverdue(action) ? "high" : ""}">${isOverdue(action) ? "Overdue" : esc(statusLabel(action.status))}</span><button class="mode-button" data-action-observation="${esc(action.observation_id)}">View observation ↗</button></div><h3>${esc(action.title)}</h3><div class="row-bottom"><span>${esc(action.owner)} · Due ${esc(action.due_date)}</span><span>${esc(observation?.location || "")}</span></div>${closed ? `<p class="hint" style="margin:12px 0 0">Evidence: ${esc(action.closure_note)}</p>` : ""}<div class="action-controls">${action.status === "open" ? `<button class="button secondary small" data-progress="${esc(action.id)}">Start action</button>` : ""}${!closed ? `<button class="text-button" data-show-close="${esc(action.id)}">Close with evidence</button>` : `<button class="text-button" data-reopen="${esc(action.id)}">Reopen action</button>`}</div><form class="closure-form" data-close-form="${esc(action.id)}" hidden><label style="margin-top:14px" for="evidence-${scope}-${esc(action.id)}">What changed? Where is the evidence?</label><textarea id="evidence-${scope}-${esc(action.id)}" name="evidence" required minlength="8" maxlength="2000" placeholder="Record the completed work and verification…"></textarea><button class="button small" style="margin-top:10px" type="submit">Save closure evidence</button> <button class="text-button" type="button" data-cancel-close="${esc(action.id)}">Cancel</button><div class="error" role="alert"></div></form>${action.history.length ? `<details class="runbook" style="margin-bottom:0"><summary>State history (${action.history.length})</summary>${action.history.map((h) => `<p class="hint">${esc(statusLabel(h.status))} · ${esc(new Date(h.at).toLocaleString())}${h.note ? "<br>" + esc(h.note) : ""}</p>`).join("")}</details>` : ""}</article>`;
}
function renderActions() {
  const open = data.actions
    .filter((x) => x.status !== "closed")
    .sort((a, b) => a.due_date.localeCompare(b.due_date));
  $("next-actions").innerHTML =
    open
      .slice(0, 3)
      .map((a) => actionHTML(a, "next"))
      .join("") ||
    '<div class="empty">No open actions. Review observations and add a follow-up where needed.</div>';
  const filter = $("action-filter").value;
  const actions = data.actions.filter(
    (x) =>
      filter === "all" ||
      (filter === "closed" && x.status === "closed") ||
      (filter === "open" && x.status !== "closed") ||
      (filter === "overdue" && isOverdue(x)),
  );
  $("all-actions").innerHTML =
    actions.map((a) => actionHTML(a, "all")).join("") ||
    '<div class="empty">No actions in this view. Choose another filter or add one from an observation.</div>';
}
function showView(name) {
  if (!["overview", "actions", "handover", "settings"].includes(name)) return;
  view = name;
  document
    .querySelectorAll(".view")
    .forEach((e) => (e.hidden = e.id !== "view-" + name));
  document.querySelectorAll(".rail-link").forEach((e) => {
    e.classList.toggle("active", e.dataset.view === name);
    if (e.dataset.view === name) e.setAttribute("aria-current", "page");
    else e.removeAttribute("aria-current");
  });
  const titles = {
    overview: [
      "Your shift, in focus.",
      "Review the signals. Own the follow-through.",
    ],
    actions: [
      "Follow-through, made visible.",
      "Every action has an owner. Every closure has evidence.",
    ],
    handover: [
      "A clearer next shift.",
      "Take a useful record into the next conversation.",
    ],
    settings: ["Your workspace.", "Storage, exports, privacy and agent tools."],
  };
  $("view-title").textContent = titles[name][0];
  $("view-description").textContent = titles[name][1];
  if (name === "handover") $("handover-preview").textContent = handover();
}
function mdText(text) {
  return String(text ?? "")
    .replace(/([\\`*_{}\[\]<>()#!|])/g, "\\$1")
    .replace(/\r?\n/g, " ");
}
function handover() {
  const open = data.actions.filter((a) => a.status !== "closed"),
    lines = [
      `# SafetyOps shift handover`,
      "",
      `Generated: ${new Date().toISOString()}`,
      demo
        ? "SYNTHETIC SAMPLE — demonstration records only."
        : "Personal workspace export — review before sharing.",
      "",
      `Observations: ${data.observations.length} | Open actions: ${open.length} | Overdue: ${open.filter(isOverdue).length}`,
      "",
      "## Actions requiring follow-up",
      "",
    ];
  for (const a of open) {
    lines.push(
      `- [ ] ${mdText(a.title)}`,
      `  Owner: ${mdText(a.owner)} | Due: ${a.due_date} | State: ${statusLabel(a.status)}`,
    );
  }
  if (!open.length) lines.push("No open actions.");
  lines.push("", "## Observation register", "");
  for (const o of data.observations) {
    const a = o.assessment,
      b = a.score_breakdown;
    lines.push(
      `### ${mdText(o.location)} · ${o.id.slice(0, 8)}`,
      `Recorded: ${o.created_at}`,
      "",
      mdText(o.text),
      "",
      `Category: ${mdText(a.category)} | Severity: ${a.severity} | Priority: ${a.risk_score}/100`,
      `Source: ${mdText(a.model_source)} | Rules: ${mdText(a.rule_version)}`,
      `Score: ${b.severity_points} severity + ${b.recurrence_points} recurrence; ${b.related_observations_7d} related observations.`,
      ...a.reasons.map((r) => "- " + mdText(r)),
      "",
    );
  }
  lines.push("## Closed actions and evidence", "");
  for (const a of data.actions.filter((x) => x.status === "closed"))
    lines.push(
      `- ${mdText(a.title)} — ${mdText(a.owner)}`,
      `  Evidence: ${mdText(a.closure_note)}`,
      ...a.history.map(
        (h) =>
          `  ${h.at}: ${statusLabel(h.status)}${h.note ? " — " + mdText(h.note) : ""}`,
      ),
    );
  lines.push(
    "",
    "Decision support only. Priority is a heuristic, not an accident probability. Review against site conditions and local procedures.",
  );
  return lines.join("\n");
}
function csvCell(value) {
  let s = String(value ?? "");
  if (/^[\s]*[=+\-@\t\r]/.test(s)) s = "'" + s;
  return '"' + s.replace(/"/g, '""') + '"';
}
function exportData(type) {
  let content, mime;
  if (type === "md") {
    content = handover();
    mime = "text/markdown";
  } else if (type === "csv") {
    const fields = [
      "id",
      "observation_id",
      "title",
      "owner",
      "due_date",
      "status",
      "closure_note",
    ];
    content =
      "\uFEFF" +
      [fields, ...data.actions.map((a) => fields.map((k) => a[k]))]
        .map((row) => row.map(csvCell).join(","))
        .join("\r\n");
    mime = "text/csv";
  } else {
    content = JSON.stringify(
      {
        schema_version: 1,
        exported_at: new Date().toISOString(),
        synthetic: demo,
        ...data,
      },
      null,
      2,
    );
    mime = "application/json";
  }
  const url = URL.createObjectURL(
      new Blob([content], { type: mime + ";charset=utf-8" }),
    ),
    link = document.createElement("a");
  link.href = url;
  link.download = `safetyops-${demo ? "sample-" : ""}handover-${localDate()}.${type}`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast("Export downloaded. Review it before sharing.");
}
async function mutateAction(id, status, note = "", target) {
  const row = data.actions.find((a) => a.id === id);
  if (!row) return;
  if (demo) {
    row.status = status;
    row.closure_note = note;
    row.revision++;
    row.history.push({ status, note, at: new Date().toISOString() });
    render();
    toast("Sample action updated. This demonstration is not saved.");
    return;
  }
  try {
    clearError();
    await api("/actions/" + encodeURIComponent(id), {
      method: "PATCH",
      body: JSON.stringify({
        status,
        closure_note: note,
        revision: row.revision,
      }),
    });
    await refresh();
    toast(
      status === "closed" ? "Action closed with evidence." : "Action updated.",
    );
  } catch (error) {
    if (error.status === 409) {
      await refresh().catch(() => {});
      fail(error);
    } else if (target) target.textContent = error.message;
    else fail(error);
  }
}
document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const d = button.dataset;
  if (d.view) {
    showView(d.view);
    return;
  }
  if (d.observation) {
    selected = d.observation;
    renderList();
    renderDetail();
    if (innerWidth < 700) {
      $("detail-panel").tabIndex = -1;
      $("detail-panel").focus({ preventScroll: true });
      $("detail-panel").scrollIntoView({
        behavior: scrollBehavior(),
        block: "start",
      });
    } else {
      Array.from(document.querySelectorAll("[data-observation]"))
        .find((e) => e.dataset.observation === selected)
        ?.focus({ preventScroll: true });
    }
    return;
  }
  if (d.actionObservation) {
    selected = d.actionObservation;
    showView("overview");
    renderList();
    renderDetail();
    $("detail-panel").tabIndex = -1;
    $("detail-panel").focus({ preventScroll: true });
    $("detail-panel").scrollIntoView({
      behavior: scrollBehavior(),
      block: "start",
    });
    return;
  }
  if (d.export) {
    exportData(d.export);
    return;
  }
  if (d.showClose) {
    const form = button.closest(".action-row").querySelector(".closure-form");
    form.hidden = false;
    form.querySelector("textarea").focus();
    return;
  }
  if (d.cancelClose) {
    button.closest("form").hidden = true;
    return;
  }
  if (d.progress || d.reopen) {
    button.disabled = true;
    await mutateAction(
      d.progress || d.reopen,
      d.progress ? "in_progress" : "open",
    );
    button.disabled = false;
    return;
  }
  if (button.id === "create-workspace") {
    if (loading) return;
    button.disabled = true;
    try {
      clearError();
      await createWorkspace();
    } catch (error) {
      fail(error);
    } finally {
      button.disabled = false;
    }
    return;
  }
  if (button.id === "capture-shortcut") {
    showView("overview");
    $("capture-panel").scrollIntoView({
      behavior: scrollBehavior(),
      block: "start",
    });
    $("observation-text").focus();
    return;
  }
  if (button.id === "toggle-demo") {
    if (!demo) {
      demo = true;
      data = sampleData();
      selected = "s1";
      render();
      toast("Showing synthetic sample records. Your workspace is unchanged.");
    } else {
      button.disabled = true;
      try {
        await refresh();
        toast("Returned to your workspace.");
      } catch (error) {
        if (error.status === 401)
          toast(
            "No personal workspace in this browser yet. Capture an observation to create one.",
          );
        else fail(error);
      } finally {
        button.disabled = false;
      }
    }
    return;
  }
  if (button.id === "delete-workspace") {
    $("delete-confirm").hidden = false;
    return;
  }
  if (button.id === "cancel-delete") {
    $("delete-confirm").hidden = true;
    return;
  }
  if (button.id === "confirm-delete") {
    button.disabled = true;
    try {
      await api("", { method: "DELETE" });
      demo = true;
      data = sampleData();
      selected = "s1";
      $("delete-confirm").hidden = true;
      render();
      toast("Workspace and its records deleted.");
    } catch (error) {
      fail(error);
    } finally {
      button.disabled = false;
    }
  }
});
$("observation-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loading) return;
  const button = $("assess-button");
  if (button.disabled) return;
  button.disabled = true;
  button.textContent = "Assessing & saving…";
  clearError("observation-error");
  const text = $("observation-text").value,
    location = $("observation-location").value;
  try {
    if (demo) await createWorkspace();
    const row = await api("/observations", {
      method: "POST",
      body: JSON.stringify({ text, location }),
    });
    selected = row.id;
    await refresh();
    $("observation-text").value = "";
    toast(
      "Observation saved. Review the assessment and assign the next action.",
    );
    $("detail-panel").scrollIntoView({
      behavior: scrollBehavior(),
      block: "start",
    });
  } catch (error) {
    fail(error, "observation-error");
  } finally {
    button.disabled = false;
    button.textContent = demo
      ? "Create workspace & assess ↗"
      : "Assess & save observation ↗";
  }
});
document.addEventListener("submit", async (event) => {
  if (event.target.id === "action-form") {
    event.preventDefault();
    const form = event.target,
      button = form.querySelector("button[type=submit]");
    if (button.disabled) return;
    button.disabled = true;
    const body = {
      observation_id: selected,
      title: $("action-title").value,
      owner: $("action-owner").value,
      due_date: $("action-due").value,
    };
    try {
      if (demo) {
        data.actions.push({
          ...body,
          id: "sample-" + Date.now(),
          status: "open",
          closure_note: "",
          revision: 1,
          history: [{ status: "open", at: new Date().toISOString() }],
          created_at: new Date().toISOString(),
        });
        render();
        toast("Sample action added. This demonstration is not saved.");
      } else {
        await api("/actions", { method: "POST", body: JSON.stringify(body) });
        await refresh();
        toast("Corrective action saved.");
      }
    } catch (error) {
      fail(error, "action-error");
    } finally {
      button.disabled = false;
    }
  } else if (event.target.matches(".closure-form")) {
    event.preventDefault();
    const form = event.target,
      button = form.querySelector("button[type=submit]");
    if (button.disabled) return;
    button.disabled = true;
    await mutateAction(
      form.dataset.closeForm,
      "closed",
      form.elements.evidence.value,
      form.querySelector(".error"),
    );
    button.disabled = false;
  }
});
$("search").addEventListener("input", renderList);
$("severity-filter").addEventListener("change", renderList);
$("action-filter").addEventListener("change", renderActions);
$("today").textContent = new Date().toLocaleDateString(undefined, {
  weekday: "short",
  month: "short",
  day: "numeric",
});
$("assess-button").disabled = true;
$("create-workspace").disabled = true;
render();
$("assess-button").disabled = true;
$("create-workspace").disabled = true;
(async () => {
  try {
    if (location.hash !== "#demo") await refresh();
  } catch (error) {
    if (error.status !== 401)
      fail(
        new Error(
          "Your workspace could not be loaded. Showing synthetic samples. Retry by reloading; your saved records have not been replaced.",
        ),
      );
  } finally {
    loading = false;
    $("assess-button").disabled = false;
    if ($("create-workspace")) $("create-workspace").disabled = false;
  }
})();
