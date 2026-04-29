const state = {
  health: null,
  runs: [],
  totals: {},
  selectedRunId: null,
  selectedRun: null,
  agents: [],
  phases: [],
  skills: [],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

async function api(path, options = {}) {
  const init = { headers: { "Content-Type": "application/json" }, ...options };
  if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

function logActivity(message) {
  const box = $("#activityLog");
  const item = document.createElement("div");
  item.className = "event-item";
  item.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong><span>${escapeHtml(message)}</span>`;
  box.prepend(item);
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function badge(status) {
  return `<span class="badge ${escapeHtml(status || "")}">${escapeHtml(status || "unknown")}</span>`;
}

function showSection(id) {
  $$(".section").forEach((el) => el.classList.toggle("active-section", el.id === id));
  $$(".nav button").forEach((btn) => btn.classList.toggle("active", btn.dataset.section === id));
}

async function loadHealth() {
  state.health = await api("/api/health");
  $("#healthBadge").textContent = "API online";
  $("#healthBadge").className = "badge completed";
}

async function loadRuns() {
  const data = await api("/api/runs");
  state.runs = data.runs || [];
  state.totals = data.totals || {};
  renderMetrics();
  renderRuns();
  renderGatesFromRuns();
}

async function loadAgents() {
  const data = await api("/api/agents");
  state.agents = data.agents || [];
  state.phases = data.phases || [];
  renderAgents();
}

async function loadSkills() {
  const data = await api("/api/skills");
  state.skills = data.skills || [];
  renderSkills();
}

async function loadMemoryStats() {
  try {
    const stats = await api("/api/memory/stats");
    $("#memoryStats").textContent = `${stats.total_memories || 0} memories · ${stats.candidates || 0} candidates`;
  } catch (err) {
    $("#memoryStats").textContent = "memoria sin inicializar";
  }
}

function renderMetrics() {
  const items = [
    ["Total", state.totals.total || 0],
    ["Esperando aprobación", state.totals.waiting_approval || 0],
    ["Corriendo", state.totals.running || 0],
    ["Completados", state.totals.completed || 0],
  ];
  $("#metrics").innerHTML = items.map(([label, value]) => `
    <article class="metric"><strong>${value}</strong><span>${label}</span></article>
  `).join("");
  $("#runCount").textContent = `${state.runs.length} runs`;
}

function renderRuns() {
  const box = $("#runsList");
  if (!state.runs.length) {
    box.innerHTML = `<article class="run-card"><strong>No hay runs todavía.</strong><p class="muted">Lanzá el primero desde el panel.</p></article>`;
    return;
  }
  box.innerHTML = state.runs.map((run) => `
    <article class="run-card" data-run-id="${escapeHtml(run.run_id)}">
      <div class="card-top">
        <div>
          <div class="card-title">${escapeHtml(run.project_id)}</div>
          <div class="code">${escapeHtml(run.run_id)}</div>
        </div>
        ${badge(run.status)}
      </div>
      <p class="muted">Fase: ${escapeHtml(run.current_phase || "sin fase")} · Eventos: ${run.events_count || 0}</p>
      <div class="card-meta">
        <span>${run.completed_count || 0} fases hechas</span>
        <span>${run.artifacts_count || 0} artifacts</span>
        <span>${run.slots_count || 0} slots</span>
      </div>
    </article>
  `).join("");
  $$(".run-card[data-run-id]").forEach((card) => card.addEventListener("click", () => selectRun(card.dataset.runId)));
}

function phaseLabel(id) {
  return String(id || "").replaceAll("_", " ");
}

function renderTimeline(runData) {
  const workflow = runData.state?.workflow || {};
  const completed = new Set(workflow.completed_phases || []);
  const pending = workflow.pending_phases || [];
  const current = workflow.current_phase || runData.run?.current_phase || "";
  const ordered = [...completed, ...pending].filter(Boolean);
  const unique = [...new Set(ordered.length ? ordered : state.phases.map((p) => p.id).filter(Boolean))];
  $("#timeline").innerHTML = unique.map((phase) => {
    const klass = completed.has(phase) ? "done" : (phase === current ? "current" : "");
    return `<div class="phase ${klass}"><strong>${escapeHtml(phaseLabel(phase))}</strong><small>${klass || "pending"}</small></div>`;
  }).join("") || `<p class="muted">Sin timeline disponible.</p>`;
}

function renderEvents(events = []) {
  $("#eventsList").innerHTML = events.length ? events.slice().reverse().map((event) => `
    <article class="event-item">
      <strong>${escapeHtml(event.type || "event")}</strong>
      <span>${escapeHtml(event.summary || JSON.stringify(event))}</span>
    </article>
  `).join("") : `<p class="muted">Sin eventos todavía.</p>`;
}

function renderRunDetail(data) {
  state.selectedRun = data;
  const run = data.run || {};
  $("#runTitle").textContent = `${run.project_id || "run"} · ${run.run_id || ""}`;
  $("#runStatus").textContent = run.status || "unknown";
  $("#runStatus").className = `badge ${run.status || ""}`;
  $("#selectedRunHint").textContent = `Run activo: ${run.run_id || ""} (${run.current_phase || "sin fase"})`;
  renderTimeline(data);
  renderEvents(data.events || []);
  $("#stateViewer").textContent = pretty(data.state?.shared_state || data.state || {});
  renderArtifacts(data.state?.artifacts || {});
  renderGates(data.state?.approvals || {}, run.run_id);
}

async function selectRun(runId) {
  state.selectedRunId = runId;
  const data = await api(`/api/runs/${encodeURIComponent(runId)}`);
  renderRunDetail(data);
  showSection("run-detail");
  logActivity(`Run seleccionado: ${runId}`);
}

function renderGatesFromRuns() {
  const pending = state.runs.filter((run) => run.pending_approval);
  $("#pendingGateCount").textContent = `${pending.length} pendientes`;
  if (!pending.length && !state.selectedRun) {
    $("#gatesList").innerHTML = `<article class="gate-card"><strong>Sin gates pendientes.</strong><p class="muted">Cuando un workflow frene en PRD/spec/release aparece acá.</p></article>`;
  }
}

function renderGates(approvals = {}, runId = state.selectedRunId) {
  const entries = Object.entries(approvals).filter(([, approval]) => approval && approval.status === "pending");
  $("#pendingGateCount").textContent = `${entries.length} pendientes`;
  $("#gatesList").innerHTML = entries.length ? entries.map(([id, approval]) => `
    <article class="gate-card">
      <div class="card-top">
        <div><strong>${escapeHtml(id)}</strong><p class="muted">Solicitado por ${escapeHtml(approval.requested_by || "runtime")}</p></div>
        ${badge("waiting_approval")}
      </div>
      <pre class="code">${escapeHtml(pretty(approval.artifact_versions || {}))}</pre>
      <div class="quick-actions">
        <button class="primary small gate-action" data-action="approve" data-run-id="${escapeHtml(runId)}">Aprobar</button>
        <button class="ghost small gate-action" data-action="request_changes" data-run-id="${escapeHtml(runId)}">Pedir cambios</button>
      </div>
    </article>
  `).join("") : `<article class="gate-card"><strong>No hay aprobaciones pendientes para este run.</strong></article>`;
  $$(".gate-action").forEach((btn) => btn.addEventListener("click", () => resumeSelected(btn.dataset.action, btn.dataset.runId)));
}

function renderArtifacts(artifacts = {}) {
  const entries = Object.entries(artifacts);
  $("#artifactCount").textContent = `${entries.length} artifacts`;
  $("#artifactList").innerHTML = entries.length ? entries.map(([id, meta]) => `
    <article class="artifact-card" data-artifact-id="${escapeHtml(id)}">
      <div class="card-top"><strong>${escapeHtml(id)}</strong><span class="badge completed">v${meta.version || 1}</span></div>
      <p class="muted">${escapeHtml(meta.summary || meta.kind || "artifact")}</p>
      <div class="card-meta"><span>${escapeHtml(meta.created_by || "")}</span><span>${escapeHtml(meta.status || "")}</span></div>
    </article>
  `).join("") : `<article class="artifact-card"><strong>Sin artifacts todavía.</strong></article>`;
  $$(".artifact-card[data-artifact-id]").forEach((card) => card.addEventListener("click", () => loadArtifact(card.dataset.artifactId)));
}

async function loadArtifact(artifactId) {
  if (!state.selectedRunId) return;
  const data = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/artifacts/${encodeURIComponent(artifactId)}`);
  $("#artifactTitle").textContent = artifactId;
  $("#artifactPreview").textContent = data.content || "";
  showSection("artifacts");
}

function listFrom(value) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== "object") return [];
  return Object.values(value).flat().filter(Boolean);
}

function renderAgents() {
  const filter = ($("#agentFilter").value || "").toLowerCase();
  const agents = state.agents.filter((agent) => pretty(agent).toLowerCase().includes(filter));
  $("#agentGrid").innerHTML = agents.map((agent) => `
    <article class="agent-card">
      <div class="card-top"><strong>${escapeHtml(agent.id)}</strong><span class="badge">${escapeHtml(agent.model_profile || "model")}</span></div>
      <p>${escapeHtml(agent.role || "")}</p>
      <div class="pill-row">${listFrom(agent.capabilities).slice(0, 6).map((cap) => `<span class="pill">${escapeHtml(cap)}</span>`).join("")}</div>
      <div class="pill-row">${listFrom(agent.base_skills || agent.skills).slice(0, 5).map((skill) => `<span class="pill warn">${escapeHtml(skill)}</span>`).join("")}</div>
    </article>
  `).join("");
}

function renderSkills() {
  const filter = ($("#skillFilter").value || "").toLowerCase();
  const skills = state.skills.filter((skill) => pretty(skill).toLowerCase().includes(filter));
  $("#skillGrid").innerHTML = skills.length ? skills.map((skill) => `
    <article class="skill-card">
      <div class="card-top"><strong>${escapeHtml(skill.name)}</strong>${skill.quarantined ? badge("quarantine") : badge("trusted")}</div>
      <p class="muted">${escapeHtml(skill.description || "Sin descripción")}</p>
      <div class="pill-row">${listFrom(skill.tags).slice(0, 6).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}</div>
    </article>
  `).join("") : `<article class="skill-card"><strong>No se encontraron skills.</strong></article>`;
}

async function resumeSelected(action, runId = state.selectedRunId) {
  if (!runId) return logActivity("No hay run seleccionado para aprobar.");
  const notes = action === "approve" ? "Approved from Command Center" : "Changes requested from Command Center";
  const data = await api(`/api/runs/${encodeURIComponent(runId)}/resume`, { method: "POST", body: { action, notes } });
  renderRunDetail({ run: data.run, state: data.state, events: [] });
  await loadRuns();
  logActivity(`${action} enviado para ${runId}`);
}

async function launchRun(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const task = String(form.get("task") || "").trim();
  if (!task) return logActivity("Escribí una tarea antes de lanzar el run.");
  const body = {
    project_id: String(form.get("project_id") || "default"),
    task,
    execution_mode: String(form.get("execution_mode") || "interactive"),
    allow_deploy: form.get("allow_deploy") === "on",
    auto_approve_gates: ["discovery_gate"],
  };
  logActivity("Lanzando workflow…");
  const data = await api("/api/runs", { method: "POST", body });
  await loadRuns();
  renderRunDetail({ run: data.run, state: data.state, events: [] });
  state.selectedRunId = data.run.run_id;
  showSection(data.status === "waiting_approval" ? "gates" : "run-detail");
  logActivity(`Workflow creado: ${data.run.run_id}`);
}

async function memorySearch(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const projectId = encodeURIComponent(String(form.get("project_id") || ""));
  const q = encodeURIComponent(String(form.get("q") || ""));
  if (!q) return;
  const [results, tree, candidates] = await Promise.all([
    api(`/api/memory/search?q=${q}&project_id=${projectId}`),
    api(`/api/memory/projects/${projectId || "default"}/tree`).catch(() => ({})),
    api(`/api/memory/candidates?project_id=${projectId}`).catch(() => ({ candidates: [] })),
  ]);
  $("#memoryResults").innerHTML = (results.items || []).map((item) => `
    <article class="memory-card"><strong>${escapeHtml(item.title || item.kind)}</strong><p>${escapeHtml(item.content || "")}</p><span class="badge">score ${item.score}</span></article>
  `).join("") || `<p class="muted">Sin resultados.</p>`;
  renderMemoryTree(tree);
  renderMemoryCandidates(candidates.candidates || []);
}

function renderMemoryTree(tree) {
  const project = tree.project;
  if (!project) {
    $("#memoryTree").innerHTML = `<p class="muted">Proyecto sin árbol de memoria.</p>`;
    return;
  }
  $("#memoryTree").innerHTML = `<strong>${escapeHtml(project.name || project.slug)}</strong><ul>${(tree.features || []).map((feature) => `
    <li>${escapeHtml(feature.name)} <span class="muted">${feature.memory_count} items</span>
      <ul>${(feature.topics || []).map((topic) => `<li>${escapeHtml(topic.name)} · ${topic.memory_count}</li>`).join("")}</ul>
    </li>`).join("")}</ul>`;
}

function renderMemoryCandidates(candidates) {
  $("#memoryCandidates").innerHTML = candidates.length ? candidates.map((candidate) => `
    <article class="memory-card"><strong>${escapeHtml(candidate.title || candidate.kind)}</strong><p>${escapeHtml(candidate.content || "")}</p></article>
  `).join("") : `<p class="muted">Sin candidates pendientes.</p>`;
}

async function loadDesignSystem() {
  const project = state.selectedRun?.run?.project_id || "synto";
  const data = await api(`/api/design-system/${encodeURIComponent(project)}`);
  $("#designSystemViewer").textContent = data.content || pretty(data);
  logActivity(`Design system cargado para ${project}`);
}

// ── LLM Providers ──────────────────────────────────────────────────────────

state.providers = [];
state.allModels = [];
state.profiles = {};

async function loadProviders() {
  const data = await api("/api/llm/providers");
  state.providers = data.providers || [];
  renderProviders();
}

async function loadAllModels() {
  const data = await api("/api/llm/models");
  state.allModels = data.models || [];
  renderAllModels();
}

async function loadProfiles() {
  const data = await api("/api/llm/profiles");
  state.profiles = data.profiles || {};
  renderProfiles();
}

function renderProviders() {
  const tierIcons = { free: "🆓", economy: "💰", balanced: "⚖️", premium: "💎" };
  $("#providersList").innerHTML = state.providers.map((p) => {
    const statusIcon = p.configured ? "✅" : "❌";
    const authLabel = p.auth_type === "oauth" ? "OAuth" : p.auth_type === "api_key" ? "API Key" : p.auth_type === "none" ? "Sin auth" : p.auth_type;
    const models = p.models || [];
    const freeCount = models.filter((m) => m.tier === "free").length;
    return `
      <article class="provider-card" data-provider="${p.id}">
        <div class="provider-header">
          <div>
            <h3>${statusIcon} ${escapeHtml(p.name)}</h3>
            <span class="muted">${escapeHtml(authLabel)} · ${models.length} modelos (${freeCount} gratis)</span>
          </div>
          <div class="provider-actions">
            ${p.signup_url ? `<a href="${escapeHtml(p.signup_url)}" target="_blank" class="ghost small">Crear cuenta</a>` : ""}
            <button class="ghost small" onclick="testProvider('${escapeHtml(p.id)}')">Test</button>
            <button class="ghost small" onclick="editProvider('${escapeHtml(p.id)}')">Editar</button>
          </div>
        </div>
        <div class="provider-config">
          ${p.auth_type === "api_key" ? `
            <label>API Key
              <input type="password" value="${escapeHtml(p.api_key_masked || "")}" data-provider="${p.id}" data-field="api_key" placeholder="sk-..." />
            </label>
          ` : ""}
          ${p.auth_type === "oauth" ? `
            <label>Auth file path
              <input type="text" value="${escapeHtml(p.auth_file || "")}" data-provider="${p.id}" data-field="auth_file" placeholder="~/.local/share/opencode/auth.json" />
            </label>
            <p class="muted">Synto lee el access token de OpenCode auth.json automáticamente.</p>
          ` : ""}
          ${p.auth_type === "none" ? `
            <p class="muted">Sin autenticación requerida. Asegurate de que el servicio esté corriendo.</p>
          ` : ""}
        </div>
        <details>
          <summary class="muted">${models.length} modelos</summary>
          <table class="mini-table">
            <thead><tr><th>Modelo</th><th>Contexto</th><th>Tier</th><th>Capabilities</th></tr></thead>
            <tbody>${models.map((m) => `
              <tr>
                <td><code>${escapeHtml(m.id)}</code></td>
                <td>${(m.context_window / 1024).toFixed(0)}K</td>
                <td>${tierIcons[m.tier] || m.tier} ${m.tier}</td>
                <td>${(m.capabilities || []).join(", ")}</td>
              </tr>
            `).join("")}</tbody>
          </table>
        </details>
      </article>
    `;
  }).join("");
}

function renderAllModels() {
  const tierIcons = { free: "🆓", economy: "💰", balanced: "⚖️", premium: "💎" };
  const filter = ($("#modelFilter")?.value || "").toLowerCase();
  let models = state.allModels;
  if (filter) {
    models = models.filter((m) =>
      m.id.toLowerCase().includes(filter) ||
      m.provider_name.toLowerCase().includes(filter) ||
      m.tier.toLowerCase().includes(filter) ||
      (m.capabilities || []).some((c) => c.toLowerCase().includes(filter))
    );
  }
  $("#modelsTable").innerHTML = `
    <table class="mini-table">
      <thead><tr><th>Modelo</th><th>Proveedor</th><th>Contexto</th><th>Tier</th><th>Capabilities</th></tr></thead>
      <tbody>${models.map((m) => `
        <tr>
          <td><code>${escapeHtml(m.id)}</code></td>
          <td>${escapeHtml(m.provider_name)}</td>
          <td>${(m.context_window / 1024).toFixed(0)}K</td>
          <td>${tierIcons[m.tier] || m.tier} ${m.tier}</td>
          <td>${(m.capabilities || []).join(", ")}</td>
        </tr>
      `).join("") || `<tr><td colspan="5" class="muted">Sin resultados</td></tr>`}</tbody>
    </table>
  `;
}

function renderProfiles() {
  const profiles = state.profiles;
  const agents = profiles.agents || {};
  const profilesData = profiles.profiles || {};
  let html = "";
  // Agent → Profile mapping
  html += `<h4>Agentes → Perfiles</h4>`;
  for (const [agent, profile] of Object.entries(agents)) {
    html += `
      <div class="form-row">
        <label style="min-width: 180px;">${escapeHtml(agent)}</label>
        <input type="text" value="${escapeHtml(profile)}" data-agent-profile="${escapeHtml(agent)}" class="profile-input" />
      </div>
    `;
  }
  // Profile → Model mapping
  html += `<h4 style="margin-top:1rem;">Perfiles → Modelos</h4>`;
  for (const [profile, model] of Object.entries(profilesData)) {
    html += `
      <div class="form-row">
        <label style="min-width: 180px;">${escapeHtml(profile)}</label>
        <input type="text" value="${escapeHtml(model)}" data-profile-model="${escapeHtml(profile)}" class="profile-model-input" />
      </div>
    `;
  }
  if (!Object.keys(agents).length && !Object.keys(profilesData).length) {
    html = `<p class="muted">No hay perfiles configurados. Configurá models.yaml desde la UI o manualmente.</p>`;
  }
  $("#profilesEditor").innerHTML = html;
}

async function testProvider(providerId) {
  try {
    const data = await api(`/api/llm/providers/${encodeURIComponent(providerId)}/test`, { method: "POST" });
    logActivity(`Test ${providerId}: ${data.available ? "✅ Conectado" : "❌ No disponible"} (${data.models_count} modelos)`);
    alert(`${providerId}: ${data.available ? "Conectado" : "No disponible"} — ${data.models_count} modelos`);
  } catch (err) {
    logActivity(`Test ${providerId}: ${err.message}`);
    alert(`Error: ${err.message}`);
  }
}

async function saveProviderConfig(providerId) {
  const card = document.querySelector(`.provider-card[data-provider="${providerId}"]`);
  if (!card) return;
  const payload = {};
  const keyInput = card.querySelector('[data-field="api_key"]');
  const authInput = card.querySelector('[data-field="auth_file"]');
  if (keyInput && keyInput.value && !keyInput.value.includes("***")) {
    payload.api_key = keyInput.value;
  }
  if (authInput) {
    payload.auth_file = authInput.value;
  }
  if (Object.keys(payload).length === 0) {
    logActivity(`No hay cambios para ${providerId}`);
    return;
  }
  try {
    await api(`/api/llm/providers/${encodeURIComponent(providerId)}`, { method: "PUT", body: payload });
    logActivity(`Config guardada para ${providerId}`);
    await loadProviders();
  } catch (err) {
    logActivity(`Error guardando ${providerId}: ${err.message}`);
  }
}

function editProvider(providerId) {
  const card = document.querySelector(`.provider-card[data-provider="${providerId}"]`);
  if (!card) return;
  const keyInput = card.querySelector('[data-field="api_key"]');
  if (keyInput) {
    keyInput.type = keyInput.type === "password" ? "text" : "password";
  }
  // Add save button
  let saveBtn = card.querySelector(".save-config-btn");
  if (!saveBtn) {
    saveBtn = document.createElement("button");
    saveBtn.className = "primary small save-config-btn";
    saveBtn.textContent = "Guardar config";
    saveBtn.addEventListener("click", () => saveProviderConfig(providerId));
    const actions = card.querySelector(".provider-actions");
    actions.appendChild(saveBtn);
  }
}

async function saveProfiles() {
  const payload = { agents: {}, profiles: {} };
  document.querySelectorAll(".profile-input").forEach((input) => {
    payload.agents[input.dataset.agentProfile] = input.value;
  });
  document.querySelectorAll(".profile-model-input").forEach((input) => {
    payload.profiles[input.dataset.profileModel] = input.value;
  });
  try {
    await api("/api/llm/profiles", { method: "PUT", body: payload });
    logActivity("Perfiles guardados");
    await loadProfiles();
  } catch (err) {
    logActivity(`Error guardando perfiles: ${err.message}`);
  }
}

async function refreshLLMData() {
  try {
    await Promise.all([loadProviders(), loadAllModels(), loadProfiles()]);
    logActivity("LLM providers actualizados");
  } catch (err) {
    logActivity(`Error cargando LLM: ${err.message}`);
  }
}

async function refreshAll() {
  try {
    await Promise.all([loadHealth(), loadRuns(), loadAgents(), loadSkills(), loadMemoryStats(), refreshLLMData()]);
    logActivity("Datos actualizados.");
  } catch (err) {
    logActivity(`Error: ${err.message}`);
  }
}

function bindEvents() {
  $$(".nav button").forEach((btn) => btn.addEventListener("click", () => showSection(btn.dataset.section)));
  $("#refreshBtn").addEventListener("click", refreshAll);
  $("#launchForm").addEventListener("submit", launchRun);
  $("#approveBtn").addEventListener("click", () => resumeSelected("approve"));
  $("#changesBtn").addEventListener("click", () => resumeSelected("request_changes"));
  $("#agentFilter").addEventListener("input", renderAgents);
  $("#skillFilter").addEventListener("input", renderSkills);
  $("#memorySearchForm").addEventListener("submit", memorySearch);
  $("#loadDesignBtn").addEventListener("click", loadDesignSystem);
  $("#refreshProvidersBtn").addEventListener("click", refreshLLMData);
  $("#modelFilter").addEventListener("input", renderAllModels);
  $("#saveProfilesBtn").addEventListener("click", saveProfiles);
}

bindEvents();
refreshAll();
