const $ = (sel) => document.querySelector(sel);

const state = {
  view: "jobs",
  jobs: [],
  companies: [],
  stats: null,
  analyses: [],
  selectedJob: null,
  selectedAnalysis: null,
};

async function get(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

function years(job) {
  if (job.years_min != null && job.years_max != null) return `${job.years_min}–${job.years_max} yrs`;
  if (job.years_min != null) return `${job.years_min}+ yrs`;
  return "years n/a";
}

function optionList(select, values, allLabel) {
  const current = select.value;
  select.innerHTML = "";
  const all = document.createElement("option");
  all.value = "";
  all.textContent = allLabel;
  select.append(all);
  for (const value of values) {
    if (!value) continue;
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    select.append(opt);
  }
  if ([...select.options].some((opt) => opt.value === current)) select.value = current;
}

function renderPulse() {
  const s = state.stats;
  if (!s) return;
  $("#pulse").innerHTML = [
    ["jobs", s.jobs],
    ["companies", s.companies],
    ["crawled", s.crawled],
    ["with ATS", s.with_ats],
  ]
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`)
    .join("");
}

function renderJobs() {
  const q = $("#job-q").value.trim();
  const domain = $("#job-domain").value;
  const rows = state.jobs.filter((job) => {
    const blob = `${job.role} ${job.company} ${job.description} ${job.tech_stack.join(" ")}`.toLowerCase();
    if (q && !blob.includes(q.toLowerCase())) return false;
    if (domain && job.domain !== domain) return false;
    return true;
  });
  $("#job-count").textContent = `${rows.length} / ${state.jobs.length}`;
  const list = $("#job-list");
  list.innerHTML = "";
  if (!rows.length) {
    list.innerHTML = `<li class="meta">No jobs match.</li>`;
    return;
  }
  for (const job of rows) {
    const li = document.createElement("li");
    if (state.selectedJob && state.selectedJob.id === job.id) li.classList.add("on");
    li.innerHTML = `<div class="role">${escapeHtml(job.role)}</div><div class="meta">${escapeHtml(job.company)} · ${escapeHtml(years(job))}</div>`;
    li.addEventListener("click", () => {
      state.selectedJob = job;
      renderJobs();
      renderDetail(job);
    });
    list.append(li);
  }
}

function renderDetail(job) {
  const el = $("#job-detail");
  if (!job) {
    el.className = "detail empty";
    el.textContent = "Select a job.";
    return;
  }
  el.className = "detail";
  const chips = [
    job.domain && `<span class="chip gold">${escapeHtml(job.domain)}</span>`,
    `<span class="chip">${escapeHtml(years(job))}</span>`,
    `<span class="chip">${escapeHtml(job.location || "Bengaluru")}</span>`,
    ...job.tech_stack.map((t) => `<span class="chip">${escapeHtml(t)}</span>`),
  ].filter(Boolean);
  el.innerHTML = `
    <h1>${escapeHtml(job.role)}</h1>
    <p class="sub">${escapeHtml(job.company)} · ${escapeHtml(job.source)}</p>
    <div class="chips">${chips.join("")}</div>
    <p class="jd">${escapeHtml(job.description || "No description stored.")}</p>
    <p><a href="${escapeAttr(job.url)}" target="_blank" rel="noreferrer">Open posting</a></p>
  `;
}

function renderCompanies() {
  const q = $("#co-q").value.trim().toLowerCase();
  const domain = $("#co-domain").value;
  const source = $("#co-source").value;
  const ats = $("#co-ats").value;
  const rows = state.companies.filter((c) => {
    if (q && !`${c.name} ${c.website}`.toLowerCase().includes(q)) return false;
    if (domain && c.domain !== domain) return false;
    if (source && c.source !== source) return false;
    if (ats && c.ats_kind !== ats) return false;
    return true;
  });
  $("#co-count").textContent = `${rows.length} / ${state.companies.length}`;
  $("#co-body").innerHTML = rows
    .map((c) => {
      const href = c.career_url || c.website;
      const link = href
        ? `<a href="${escapeAttr(href)}" target="_blank" rel="noreferrer">${escapeHtml(c.career_url ? "careers" : "site")}</a>`
        : "—";
      return `<tr>
        <td>${escapeHtml(c.name)}</td>
        <td class="muted">${escapeHtml(c.domain || "—")}</td>
        <td class="muted">${escapeHtml(c.ats_kind || "—")}</td>
        <td class="muted">${escapeHtml(c.last_status || "uncrawled")}</td>
        <td>${link}</td>
      </tr>`;
    })
    .join("");
}

function barRows(items, labelKey, valueKey, extra) {
  const max = Math.max(1, ...items.map((item) => Number(item[valueKey] || 0)));
  return items
    .map((item) => {
      const value = Number(item[valueKey] || 0);
      const pct = Math.round((value / max) * 100);
      const more = extra ? extra(item) : value;
      return `<div class="bar"><span>${escapeHtml(item[labelKey])}</span><i style="--p:${pct}%"><em></em></i><b>${more}</b></div>`;
    })
    .join("");
}

function renderCoverage() {
  const s = state.stats;
  if (!s) return;
  $("#coverage-metrics").innerHTML = [
    ["Companies", s.companies],
    ["Jobs", s.jobs],
    ["With careers", s.with_career],
    ["With ATS", s.with_ats],
    ["Crawled", s.crawled],
  ]
    .map(([k, v]) => `<div><span>${k}</span><b>${v}</b></div>`)
    .join("");
  $("#cov-domains").innerHTML = barRows(s.domains, "name", "companies", (row) => `${row.jobs} jobs / ${row.companies}`);
  $("#cov-status").innerHTML = barRows(s.crawl_status, "name", "count");
  $("#cov-sources").innerHTML = barRows(s.sources, "name", "count");
  $("#cov-ats").innerHTML = barRows(s.ats, "name", "count");
}

function renderAnalyses() {
  const list = $("#analysis-list");
  list.innerHTML = "";
  for (const item of state.analyses) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "row" + (state.selectedAnalysis === item.name ? " on" : "");
    btn.innerHTML = `<div class="role">${escapeHtml(item.title)}</div><div class="meta">${escapeHtml(item.description)}</div>`;
    btn.addEventListener("click", () => loadAnalysis(item.name));
    list.append(btn);
  }
}

async function loadAnalysis(name) {
  state.selectedAnalysis = name;
  renderAnalyses();
  const data = await get(`/api/analysis/${encodeURIComponent(name)}`);
  $("#an-title").textContent = data.title;
  $("#an-summary").textContent = data.summary || "";
  const max = Math.max(1, ...data.rows.map((row) => Number(row.value || 0)));
  $("#an-bars").innerHTML = data.rows
    .map((row) => {
      const extra = row.companies != null ? `${row.value} jobs / ${row.companies} cos` : row.value;
      const pct = Math.round((Number(row.value || 0) / max) * 100);
      return `<div class="bar"><span>${escapeHtml(row.label)}</span><i style="--p:${pct}%"><em></em></i><b>${extra}</b></div>`;
    })
    .join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

function show(view) {
  state.view = view;
  document.querySelectorAll(".rail button").forEach((btn) => btn.classList.toggle("on", btn.dataset.view === view));
  document.querySelectorAll(".view").forEach((el) => el.classList.toggle("on", el.id === `view-${view}`));
}

async function boot() {
  const [jobs, companies, stats, analyses] = await Promise.all([
    get("/api/jobs"),
    get("/api/companies"),
    get("/api/stats"),
    get("/api/analysis"),
  ]);
  state.jobs = jobs;
  state.companies = companies;
  state.stats = stats;
  state.analyses = analyses;
  optionList($("#job-domain"), [...new Set(jobs.map((j) => j.domain))].sort(), "All domains");
  optionList($("#co-domain"), [...new Set(companies.map((c) => c.domain))].sort(), "All domains");
  optionList($("#co-ats"), [...new Set(companies.map((c) => c.ats_kind).filter(Boolean))].sort(), "All ATS");
  renderPulse();
  renderJobs();
  renderCompanies();
  renderCoverage();
  renderAnalyses();
  if (jobs[0]) {
    state.selectedJob = jobs[0];
    renderJobs();
    renderDetail(jobs[0]);
  }
}

document.querySelectorAll(".rail button").forEach((btn) => {
  btn.addEventListener("click", () => show(btn.dataset.view));
});
["job-q", "job-domain"].forEach((id) => $(`#${id}`).addEventListener("input", renderJobs));
["co-q", "co-domain", "co-source", "co-ats"].forEach((id) => $(`#${id}`).addEventListener("input", renderCompanies));

boot().catch((err) => {
  $("#job-detail").textContent = `Failed to load data: ${err.message}`;
});
