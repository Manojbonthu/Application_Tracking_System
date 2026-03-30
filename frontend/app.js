// ===== CONFIG =====
const API_BASE = "http://localhost:8000/api";

// ===== STATE =====
let state = {
  uploadedFiles: [],
  resumeIds: [],
  currentJobId: null,
  allCandidates: [],
  currentFilter: 0,
  uploadMode: "single",       // "single" | "folder"
  detectedFolderName: null,   // auto-detected from webkitdirectory
};

// ===== LOCAL STORAGE: Resume Sessions =====
function getSessions() {
  try { return JSON.parse(localStorage.getItem("ats_sessions") || "[]"); }
  catch { return []; }
}
function saveSessions(s) { localStorage.setItem("ats_sessions", JSON.stringify(s)); }

function addSession(label, resumeIds, fileNames, folderName) {
  const sessions = getSessions();
  sessions.unshift({ id: Date.now(), label, resumeIds, fileNames, folderName: folderName || null, uploadedAt: new Date().toISOString() });
  saveSessions(sessions);
  renderSidebarHistory();
}

async function deleteSession(id) {
  const sessions = getSessions();
  const session = sessions.find(s => s.id === id);
  if (!session) return;

  // Delete from backend
  try {
    if (session.folderName) {
      // Delete whole folder from backend
      await fetch(`${API_BASE}/folder/${encodeURIComponent(session.folderName)}`, { method: "DELETE" });
    } else {
      // Delete individual resumes
      for (const rid of session.resumeIds) {
        await fetch(`${API_BASE}/resume/${rid}`, { method: "DELETE" });
      }
    }
  } catch (e) {
    console.warn("[Delete] Backend delete failed:", e);
  }

  saveSessions(sessions.filter(s => s.id !== id));
  renderSidebarHistory();
  toast("Resumes deleted from storage and database.", "info");
}

function reuseSession(id) {
  const session = getSessions().find(s => s.id === id);
  if (!session) return;
  state.resumeIds = session.resumeIds;
  document.getElementById("resume-ids-display").innerHTML =
    `✅ <strong>${session.resumeIds.length}</strong> resumes loaded from "<em>${session.label}</em>" — ready to analyze.`;
  setStep(2);
  navigate("panel-analyze");
  toast(`"${session.label}" loaded — ${session.resumeIds.length} resumes ready.`, "success");
}

function renderSidebarHistory() {
  const container = document.getElementById("sidebar-resume-history");
  if (!container) return;
  const sessions = getSessions();
  if (sessions.length === 0) {
    container.innerHTML = `<div class="sidebar-empty">No uploads yet.</div>`;
    return;
  }
  container.innerHTML = sessions.map(s => `
    <div class="sidebar-session">
      <div class="sidebar-session-info" onclick="reuseSession(${s.id})">
        <div class="sidebar-session-label">${s.fileNames.length === 1 ? "📄" : "📁"} ${s.label}</div>
        <div class="sidebar-session-meta">${s.resumeIds.length} resume(s) · ${new Date(s.uploadedAt).toLocaleDateString()}</div>
      </div>
      <button class="sidebar-session-delete" onclick="event.stopPropagation();deleteSession(${s.id})" title="Delete from storage">🗑</button>
    </div>
  `).join("");
}

// ===== NAVIGATION =====
function navigate(panelId) {
  document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById(panelId).classList.add("active");
  document.querySelector(`[data-panel="${panelId}"]`)?.classList.add("active");
  if (panelId === "panel-history") loadJobHistory();
}

// ===== TOAST =====
function toast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ===== UPLOAD MODE =====
function setUploadMode(mode) {
  state.uploadMode = mode;
  const fileInput = document.getElementById("file-input");
  const btnSingle = document.getElementById("btn-mode-single");
  const btnFolder = document.getElementById("btn-mode-folder");
  const modeLabel = document.getElementById("upload-mode-label");

  if (mode === "folder") {
    fileInput.setAttribute("webkitdirectory", "true");
    fileInput.removeAttribute("multiple");
    btnSingle.classList.remove("active");
    btnFolder.classList.add("active");
    modeLabel.textContent = "Folder mode — select an entire folder of resumes";
  } else {
    fileInput.removeAttribute("webkitdirectory");
    fileInput.setAttribute("multiple", "true");
    btnSingle.classList.add("active");
    btnFolder.classList.remove("active");
    modeLabel.textContent = "Single / multi file mode — select one or more PDF/TXT files";
  }
  fileInput.value = "";
  state.detectedFolderName = null;
}

// ===== FILE HANDLING =====
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");

dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag-over"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles(Array.from(e.dataTransfer.files));
});
fileInput.addEventListener("change", () => {
  const files = Array.from(fileInput.files);
  // Auto-detect folder name from webkitdirectory paths (e.g. "FolderName/file.pdf")
  if (state.uploadMode === "folder" && files.length > 0) {
    const firstPath = files[0].webkitRelativePath || "";
    const parts = firstPath.split("/");
    state.detectedFolderName = parts.length > 1 ? parts[0] : null;
  } else {
    state.detectedFolderName = null;
  }
  handleFiles(files);
});

function handleFiles(files) {
  const valid = files.filter(f => f.name.endsWith(".pdf") || f.name.endsWith(".txt"));
  if (valid.length !== files.length) toast("Some files skipped — only PDF and TXT supported.", "error");
  const existing = new Set(state.uploadedFiles.map(f => f.name));
  state.uploadedFiles.push(...valid.filter(f => !existing.has(f.name)));
  renderFileList();
  updateUploadCount();
}

function renderFileList() {
  const list = document.getElementById("file-list");
  const bar = document.getElementById("upload-action-bar");
  if (state.uploadedFiles.length === 0) {
    list.innerHTML = "";
    bar.style.display = "none";
    return;
  }
  bar.style.display = "flex";
  list.innerHTML = state.uploadedFiles.map((f, i) => `
    <div class="file-item">
      <span class="file-icon">📄</span>
      <span class="file-name">${f.name}</span>
      <span class="file-size">${(f.size / 1024).toFixed(1)} KB</span>
      <button class="file-remove" onclick="removeFile(${i})">✕</button>
    </div>`).join("");
}

function removeFile(index) {
  state.uploadedFiles.splice(index, 1);
  renderFileList();
  updateUploadCount();
}

function updateUploadCount() {
  const el = document.getElementById("upload-count");
  el.textContent = state.uploadedFiles.length > 0
    ? `${state.uploadedFiles.length} file(s) selected${state.detectedFolderName ? ` — folder: "${state.detectedFolderName}"` : ""}`
    : "";
}

function clearFiles() {
  state.uploadedFiles = [];
  state.detectedFolderName = null;
  document.getElementById("file-input").value = "";
  renderFileList();
  updateUploadCount();
}

// ===== UPLOAD AGAIN (Clear and Reset) =====
function resetUploadFlow() {
  clearFiles();
  state.resumeIds = [];
  document.getElementById("resume-ids-display").innerHTML =
    `⚠️ No resumes loaded yet. <a href="#" onclick="navigate('panel-upload')" style="color:var(--accent);text-decoration:underline">Upload resumes first →</a>`;
  setStep(1);
  navigate("panel-upload");
  toast("Ready for new uploads!", "info");
}

// ===== UPLOAD =====
async function uploadResumes() {
  if (state.uploadedFiles.length === 0) { toast("Please select resume files first.", "error"); return; }
  const btn = document.getElementById("btn-upload");
  btn.disabled = true;
  btn.textContent = "⏳ Uploading...";

  const formData = new FormData();
  state.uploadedFiles.forEach(f => formData.append("files", f));

  // Send folder_name to backend — auto-detected from webkitdirectory
  const folderName = state.detectedFolderName || null;
  if (folderName) formData.append("folder_name", folderName);

  try {
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Upload failed"); }
    const data = await res.json();
    state.resumeIds = data.resume_ids;

    // Build session label
    const fileNames = state.uploadedFiles.map(f => f.name);
    const label = folderName
      ? `📁 ${folderName}`
      : fileNames.length === 1
        ? fileNames[0].replace(/\.(pdf|txt)$/i, "")
        : `${fileNames.length} resumes`;

    addSession(label, data.resume_ids, fileNames, data.folder_name || folderName);

    toast(`✅ ${data.total_uploaded} resume(s) uploaded!`, "success");
    setStep(2);
    navigate("panel-analyze");
    document.getElementById("resume-ids-display").innerHTML =
      `<div style="display:flex;justify-content:space-between;align-items:center"><div>✅ <strong>${data.total_uploaded}</strong> resumes ready${folderName ? ` from folder "<em>${folderName}</em>"` : ""} — ready to analyze.</div><button class="btn btn-secondary" onclick="resetUploadFlow()" style="padding:8px 16px;font-size:12px">⬆️ Upload Again</button></div>`;
  } catch (err) {
    toast(`Upload failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "⬆️ Upload Resumes";
  }
}

// ===== STEPS =====
function setStep(n) {
  document.querySelectorAll(".step").forEach((s, i) => {
    s.classList.remove("active", "done");
    if (i + 1 < n) s.classList.add("done");
    if (i + 1 === n) s.classList.add("active");
  });
}

// ===== CLEAR ANALYZE FORM =====
function clearAnalyzeForm() {
  document.getElementById("job-title").value = "";
  document.getElementById("role-level").value = "";
  document.getElementById("jd-text").value = "";
  document.getElementById("analyze-status").innerHTML = "";
  toast("Form cleared!", "info");
}

// ===== ANALYZE =====
async function runAnalysis() {
  const jobTitle = document.getElementById("job-title").value.trim();
  const roleLevel = document.getElementById("role-level").value.trim();
  const jdText = document.getElementById("jd-text").value.trim();
  if (!jobTitle) { toast("Please enter a job title.", "error"); return; }
  if (!roleLevel) { toast("Please enter the role level.", "error"); return; }
  if (!jdText || jdText.length < 50) { toast("Please enter a detailed job description (min 50 chars).", "error"); return; }
  if (state.resumeIds.length === 0) { toast("No resumes loaded. Upload or select from sidebar.", "error"); navigate("panel-upload"); return; }

  const btn = document.getElementById("btn-analyze");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner" style="width:18px;height:18px;border-width:2px"></span> Analyzing...`;
  document.getElementById("analyze-status").innerHTML = `<div class="loading"><div class="spinner"></div><p>Running AI pipeline — extracting skills, computing semantic similarity, ranking candidates...</p></div>`;

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_title: jobTitle, jd_text: jdText, resume_ids: state.resumeIds, role_type: roleLevel }),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Analysis failed"); }
    const data = await res.json();
    state.currentJobId = data.job_id;
    toast(`✅ Analysis complete! ${data.total_processed} candidates ranked.`, "success");
    setStep(3);
    document.getElementById("analyze-status").innerHTML = `
      <div style="text-align:center;padding:20px;color:var(--accent2)">
        ✅ Analysis complete — ${data.total_processed} candidates processed.
        <button class="btn btn-primary" style="margin-left:12px" onclick="loadResults()">View Results →</button>
      </div>`;
    await loadResults();
  } catch (err) {
    toast(`Analysis failed: ${err.message}`, "error");
    document.getElementById("analyze-status").innerHTML = `<div style="color:var(--red);padding:20px">❌ Error: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🚀 Run AI Analysis";
  }
}

// ===== RESULTS =====
async function loadResults(limit = 0) {
  if (!state.currentJobId) return;
  navigate("panel-results");
  const container = document.getElementById("results-container");
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading results...</p></div>`;
  const url = limit > 0 ? `${API_BASE}/results/${state.currentJobId}?limit=${limit}` : `${API_BASE}/results/${state.currentJobId}`;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Could not load results");
    const data = await res.json();
    state.allCandidates = data.candidates;
    document.getElementById("results-job-title").textContent = data.job_title || "Results";
    document.getElementById("results-total").textContent = data.total_candidates;
    document.getElementById("results-total2").textContent = data.total_candidates;
    if (data.candidates.length > 0) {
      const scores = data.candidates.map(c => c.final_score);
      document.getElementById("stat-avg").textContent = (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1)+"%";
      document.getElementById("stat-top").textContent = Math.max(...scores).toFixed(1)+"%";
      document.getElementById("stat-high").textContent = scores.filter(s=>s>=65).length;
    }
    renderCandidates(data.candidates);
  } catch (err) {
    container.innerHTML = `<div style="color:var(--red);padding:20px">❌ ${err.message}</div>`;
  }
}

function filterResults(limit) {
  document.querySelectorAll(".btn-filter").forEach(b => b.classList.remove("active"));
  document.querySelector(`.btn-filter[data-limit="${limit}"]`)?.classList.add("active");
  state.currentFilter = limit;
  renderCandidates(limit > 0 ? state.allCandidates.slice(0, limit) : state.allCandidates);
}

function renderCandidates(candidates) {
  if (!candidates || candidates.length === 0) {
    document.getElementById("results-container").innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div><h3>No candidates found</h3><p>Try uploading resumes and running the analysis again.</p></div>`;
    document.getElementById("shortlist-section").style.display = "none"; // ✅ hide when no results
    return;
  }
  const recColors = { high: "var(--green)", medium: "var(--yellow)", low: "var(--orange)", reject: "var(--red)" };
  const rows = candidates.map(c => {
    const scoreClass = c.final_score>=80?"score-high":c.final_score>=65?"score-medium":c.final_score>=45?"score-low":"score-reject";
    const rankClass = c.rank===1?"rank-1":c.rank===2?"rank-2":c.rank===3?"rank-3":"rank-other";
    const rec = c.insights?.recommendation_level || "low";
    const topMatched = (c.matched_skills||[]).slice(0,3).map(s=>`<span class="tag tag-green">${s}</span>`).join("");
    const topMissing = (c.missing_skills||[]).slice(0,2).map(s=>`<span class="tag tag-red">${s}</span>`).join("");
    return `<tr>
      <td><span class="rank-badge ${rankClass}">${c.rank}</span></td>
      <td><div style="font-weight:700">${c.candidate_name}</div><div style="font-size:12px;color:var(--text2)">${c.file_name}</div></td>
      <td><div class="score-bar"><div class="score-bar-track"><div class="score-bar-fill ${scoreClass}" style="width:${c.final_score}%"></div></div><span class="score-value" style="color:${recColors[rec]}">${c.final_score}%</span></div></td>
      <td>${topMatched||'<span style="color:var(--text2);font-size:12px">None</span>'}</td>
      <td>${topMissing||'<span style="color:var(--green);font-size:12px">✓ None</span>'}</td>
      <td><div style="display:flex;gap:8px"><a href="${API_BASE}/resume/${c.resume_id}/download" target="_blank" class="btn btn-secondary" style="padding:6px 14px;font-size:12px;text-decoration:none;display:inline-block">📥 Resume</a><button class="btn btn-secondary" style="padding:6px 14px;font-size:12px" onclick="openCandidateModal(${c.resume_id})">Details</button></div></td>
    </tr>`;
  }).join("");
  document.getElementById("results-container").innerHTML = `
    <table class="candidates-table">
      <thead><tr><th>Rank</th><th>Candidate</th><th style="min-width:200px">Match Score</th><th>Matched Skills</th><th>Missing Skills</th><th>Action</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  document.getElementById("shortlist-section").style.display = "flex"; // ✅ show after results render
}

// ===== CANDIDATE MODAL =====
async function openCandidateModal(resumeId) {
  if (!state.currentJobId) return;
  const overlay = document.getElementById("modal-overlay");
  const body = document.getElementById("modal-body");
  overlay.classList.add("open");
  body.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading candidate details...</p></div>`;
  try {
    const res = await fetch(`${API_BASE}/candidate/${resumeId}/job/${state.currentJobId}`);
    if (!res.ok) throw new Error("Could not load candidate");
    const c = await res.json();
    const recClass = { high:"rec-high", medium:"rec-medium", low:"rec-low", reject:"rec-reject" };
    const ins = c.insights || {};
    const strengthItems = (ins.strengths||[]).map(s=>`<div class="insight-item"><span class="insight-icon">✅</span><span>${s}</span></div>`).join("");
    const gapItems = (ins.skill_gaps||[]).map(s=>`<div class="insight-item"><span class="insight-icon">⚠️</span><span>${s}</span></div>`).join("");
    const suggItems = (ins.suggestions||[]).map(s=>`<div class="insight-item"><span class="insight-icon">💡</span><span>${s}</span></div>`).join("");
    const matchedTags = (c.matched_skills||[]).map(s=>`<span class="tag tag-green">${s}</span>`).join("")||"<span style='color:var(--text2)'>None</span>";
    const missingTags = (c.missing_skills||[]).map(s=>`<span class="tag tag-red">${s}</span>`).join("")||"<span style='color:var(--green)'>None ✓</span>";
    const partialTags = (c.partial_skills||[]).map(s=>`<span class="tag tag-yellow">${s}</span>`).join("")||"<span style='color:var(--text2)'>None</span>";
    const allTags = (c.all_skills||[]).map(s=>`<span class="tag tag-blue">${s}</span>`).join("")||"<span style='color:var(--text2)'>Not detected</span>";
    body.innerHTML = `
      <div style="margin-bottom:18px">
        <div class="modal-name">${c.candidate_name}</div>
        <div class="modal-file">📄 ${c.file_name}${c.email?` &nbsp;|&nbsp; ✉️ ${c.email}`:""}${c.phone?` &nbsp;|&nbsp; 📞 ${c.phone}`:""}</div>
        <div style="margin-top:10px"><a href="${API_BASE}/resume/${c.resume_id}/download" target="_blank" class="btn btn-primary" style="padding:8px 16px;font-size:13px;text-decoration:none;display:inline-block">📥 Download Resume</a></div>
      </div>
      <div class="rec-banner ${recClass[ins.recommendation_level]||"rec-low"}">${ins.recommendation||"Review manually"}</div>
      <div class="score-grid">
        <div class="score-box"><div class="label">Final Score</div><div class="value" style="color:${c.final_score>=65?"var(--green)":c.final_score>=45?"var(--yellow)":"var(--red)"}">${c.final_score}%</div></div>
        <div class="score-box"><div class="label">Semantic Match</div><div class="value" style="color:var(--accent2)">${c.semantic_score}%</div></div>
        <div class="score-box"><div class="label">Skill Match</div><div class="value" style="color:var(--accent)">${c.skill_score}%</div></div>
      </div>
      <div style="margin-bottom:18px">
        <div style="font-size:11px;color:var(--text2);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px">Score Formula</div>
        <div style="font-size:12px;color:var(--text2);background:var(--surface2);padding:10px 14px;border-radius:8px;font-family:monospace">
          Final = Semantic(${c.semantic_score}% × 0.40) + Skill(${c.skill_score}% × 0.50) + Exp(${c.experience_score}% × 0.10) = <strong style="color:var(--accent2)">${c.final_score}%</strong>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:18px">
        <div><div style="font-size:11px;font-weight:700;color:var(--green);margin-bottom:6px;text-transform:uppercase">✅ Matched</div>${matchedTags}</div>
        <div><div style="font-size:11px;font-weight:700;color:var(--red);margin-bottom:6px;text-transform:uppercase">❌ Missing</div>${missingTags}</div>
        <div><div style="font-size:11px;font-weight:700;color:var(--yellow);margin-bottom:6px;text-transform:uppercase">🟡 Partial</div>${partialTags}</div>
      </div>
      <div style="margin-bottom:18px"><div style="font-size:11px;font-weight:700;color:var(--accent2);margin-bottom:6px;text-transform:uppercase">🔵 All Extracted Skills</div>${allTags}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div class="insight-section"><h4>💪 Strengths</h4>${strengthItems||"<div style='color:var(--text2);font-size:13px'>None identified</div>"}</div>
        <div class="insight-section"><h4>⚠️ Skill Gaps</h4>${gapItems||"<div style='color:var(--text2);font-size:13px'>No gaps</div>"}</div>
      </div>
      <div class="insight-section" style="margin-top:14px"><h4>💡 Suggestions</h4>${suggItems||"<div style='color:var(--text2);font-size:13px'>No suggestions</div>"}</div>`;
  } catch (err) {
    body.innerHTML = `<div style="color:var(--red);padding:20px">❌ ${err.message}</div>`;
  }
}

function closeModal() { document.getElementById("modal-overlay").classList.remove("open"); }
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target === document.getElementById("modal-overlay")) closeModal();
});

// ===== JOB HISTORY =====
async function loadJobHistory() {
  const container = document.getElementById("history-container");
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading history...</p></div>`;
  try {
    const res = await fetch(`${API_BASE}/jobs`);
    if (!res.ok) throw new Error("Could not load job history");
    const jobs = await res.json();
    if (jobs.length === 0) {
      container.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><h3>No jobs analyzed yet</h3><p>Upload resumes and run an analysis to see results here.</p></div>`;
      return;
    }
    container.innerHTML = jobs.map(j => `
      <div class="job-item">
        <div onclick="loadJobFromHistory(${j.id},'${j.title}')" style="flex:1;cursor:pointer">
          <div class="job-title">${j.title}</div>
          <div class="job-meta">📅 ${new Date(j.created_at).toLocaleString()}</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <span class="job-badge">${j.total_candidates} candidates</span>
          <button class="btn btn-secondary" onclick="event.stopPropagation();deleteJobAnalysis(${j.id})" style="padding:6px 12px;font-size:12px">🗑️</button>
        </div>
      </div>`).join("");
  } catch (err) {
    container.innerHTML = `<div style="color:var(--red);padding:20px">❌ ${err.message}</div>`;
  }
}

async function loadJobFromHistory(jobId, title) {
  state.currentJobId = jobId;
  await loadResults();
  toast(`Loaded: ${title}`, "info");
}

async function deleteJobAnalysis(jobId) {
  if (!confirm("Delete this job analysis? Results will be permanently removed.")) return;
  try {
    const res = await fetch(`${API_BASE}/job/${jobId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    toast("Job analysis deleted successfully.", "success");
    loadJobHistory();
  } catch (err) {
    toast(`Delete failed: ${err.message}`, "error");
  }
}

// ===== INIT =====
document.addEventListener("DOMContentLoaded", () => {
  navigate("panel-upload");
  setStep(1);
  setUploadMode("single");
  renderSidebarHistory();
});

// ===== SEND SHORTLIST EMAILS =====
async function sendShortlistEmails() {
  const selectEl = document.getElementById("shortlist-count");
  const topN = selectEl ? parseInt(selectEl.value) : 10;
  const jobId = state.currentJobId;

  if (!jobId) {
    toast("No analysis found. Please run analysis first.", "error");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/send-shortlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId, top_n: topN }),
    });

    const data = await res.json();
    if (res.ok) {
      toast(`✅ ${data.message}`, "success");
    } else {
      toast(`❌ ${data.detail || "Failed to send emails"}`, "error");
    }
  } catch (err) {
    toast(`❌ Failed: ${err.message}`, "error");
  }
}
