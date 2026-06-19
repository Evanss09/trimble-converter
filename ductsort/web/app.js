// Trimble Converter dashboard logic (multi-file). Drives idle/processing/
// done/error and talks to the Python Api (window.pywebview.api).
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const screens = ["idle", "processing", "done", "error"];
  const show = (id) => screens.forEach((s) => ($(s).hidden = s !== id));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const api = () => (window.pywebview && window.pywebview.api) || null;
  const nfmt = (n) => Number(n).toLocaleString("en-US");

  const state = { files: [], folder: null, cancelled: false };

  const FILE_SVG =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1bd198" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>';

  const units = () => (document.querySelector('input[name="units"]:checked') || {}).value || "auto";
  const valid = () => state.files.filter((f) => !f.error);

  function refreshGenerate() {
    const out = $("opt-excel").checked || $("opt-pdf").checked;
    $("generate").disabled = !(valid().length && out);
  }

  async function chooseFiles() {
    const a = api(); if (!a) return;
    const paths = await a.choose_files();
    if (!paths || !paths.length) return;
    const res = await a.peek_files(paths);
    const info = (res && res.files) || [];
    state.files = paths.map((p, i) => Object.assign({ path: p }, info[i] || { file: p }));
    renderFileList();
    refreshGenerate();
  }

  function renderFileList() {
    const el = $("filelist");
    el.innerHTML = "";
    el.hidden = state.files.length === 0;
    state.files.forEach((f) => {
      const row = document.createElement("div");
      row.className = "frow";
      const chip = document.createElement("span");
      if (f.error) { chip.className = "tchip err"; chip.textContent = "unreadable"; }
      else { chip.className = "tchip " + f.trade; chip.textContent = f.label; }
      const name = document.createElement("span");
      name.className = "fname"; name.textContent = f.file;
      const meta = document.createElement("span");
      meta.className = "fmeta"; meta.textContent = f.error ? "" : nfmt(f.line_count) + " lines";
      row.appendChild(chip); row.appendChild(name); row.appendChild(meta);
      el.appendChild(row);
    });
  }

  function setStep(n, cls, txt) {
    const el = document.querySelector('.step[data-step="' + n + '"]');
    if (!el) return;
    el.classList.remove("done", "active");
    if (cls) el.classList.add(cls);
    if (txt) el.querySelector(".step-txt").textContent = txt;
  }
  const setBar = (p) => { $("bar-fill").style.width = p + "%"; $("p-pct").textContent = p + "%"; };

  function resetSteps() {
    setStep(1, "", "Parse exports"); setStep(2, "", "Detect trade & units");
    setStep(3, "", "Group & combine"); setStep(4, "", "Build Excel workbook");
    setStep(5, "", "Render PDF report"); setBar(0);
  }

  function showError(msg) {
    $("err-text").textContent = msg || "Something went wrong.";
    $("foot-status").textContent = "Error";
    show("error");
  }

  async function generate() {
    const a = api();
    const files = valid();
    if (!a || !files.length) return;
    const wantExcel = $("opt-excel").checked, wantPdf = $("opt-pdf").checked;
    state.cancelled = false;

    resetSteps();
    const lines = files.reduce((s, f) => s + (f.line_count || 0), 0);
    $("p-name").textContent = files.length === 1 ? files[0].file : files.length + " files";
    $("p-meta").textContent = nfmt(lines) + " line items";
    $("foot-status").textContent = "Working…";
    show("processing");
    await sleep(60);

    const counts = {};
    files.forEach((f) => { counts[f.label] = (counts[f.label] || 0) + 1; });
    const detected = Object.keys(counts).map((k) => counts[k] + " " + k).join(", ");
    setStep(1, "done", "Parsed " + files.length + " export(s) — " + nfmt(lines) + " line items");
    setStep(2, "done", "Detected " + detected + (units() === "auto" ? "" : " · units forced"));
    setStep(3, "active"); setBar(40);

    let res;
    try {
      res = await a.generate(files.map((f) => f.path), wantExcel, wantPdf, units());
    } catch (e) { showError(String(e)); return; }
    if (state.cancelled) return;
    if (!res || !res.ok) { showError(res && res.error); return; }

    setStep(3, "done"); setBar(72);
    if (res.files.some((f) => f.desc.indexOf("Excel") === 0)) { setStep(4, "active"); await sleep(180); setStep(4, "done"); }
    else setStep(4, "done", "Excel — skipped");
    setBar(90);
    if (res.files.some((f) => f.desc.indexOf("PDF") === 0)) { setStep(5, "active"); await sleep(180); setStep(5, "done"); }
    else setStep(5, "done", "PDF — skipped");
    setBar(100);
    await sleep(240);
    renderDone(res);
    show("done");
  }

  function renderDone(res) {
    state.folder = res.folder;
    const tcount = res.segments.length;
    $("done-sub").textContent =
      (res.multi ? "Combined" : (res.title || "Take-off")) + " · " +
      tcount + (tcount > 1 ? " trades" : " trade") + " · " + res.seconds + "s";

    const wrap = $("segments");
    wrap.innerHTML = "";
    res.segments.forEach((seg) => {
      const block = document.createElement("div");
      block.className = "segblock";
      const head = document.createElement("div");
      head.className = "seghead";
      const chip = document.createElement("span");
      chip.className = "tchip " + seg.trade; chip.textContent = seg.label;
      head.appendChild(chip);
      if (seg.sources && seg.sources.length > 1) {
        const s = document.createElement("span");
        s.className = "segsrc"; s.textContent = seg.sources.length + " sources";
        head.appendChild(s);
      }
      block.appendChild(head);
      const grid = document.createElement("div");
      grid.className = "chips";
      seg.cards.forEach((c) => {
        const t = document.createElement("div");
        t.className = "chip";
        const n = document.createElement("div"); n.className = "chip-val"; n.textContent = c.value;
        const l = document.createElement("div"); l.className = "chip-lbl"; l.textContent = c.label;
        t.appendChild(n); t.appendChild(l); grid.appendChild(t);
      });
      block.appendChild(grid);
      wrap.appendChild(block);
    });

    const fw = $("files");
    fw.innerHTML = "";
    res.files.forEach((f) => fileRow(fw, f.name, f.desc + " · " + f.size, f.path));
    $("foot-status").textContent = "Done · saved to " + folderName(res.folder);
  }

  function fileRow(parent, name, meta, path) {
    const row = document.createElement("div");
    row.className = "filerow";
    const icon = document.createElement("div");
    icon.className = "fc-icon"; icon.innerHTML = FILE_SVG;
    const body = document.createElement("div");
    body.className = "fc-body";
    const n = document.createElement("div"); n.className = "fr-name"; n.textContent = name;
    const m = document.createElement("div"); m.className = "fr-meta"; m.textContent = meta;
    body.appendChild(n); body.appendChild(m);
    const btn = document.createElement("button");
    btn.className = "btn-ghost sm"; btn.textContent = "Open";
    btn.addEventListener("click", () => { const a = api(); if (a) a.open_path(path); });
    row.appendChild(icon); row.appendChild(body); row.appendChild(btn);
    parent.appendChild(row);
  }

  function folderName(p) {
    if (!p) return "folder";
    const parts = p.replace(/[\\/]+$/, "").split(/[\\/]/);
    return parts[parts.length - 1] || p;
  }

  function reset() {
    state.files = []; state.folder = null; state.cancelled = false;
    $("filelist").hidden = true; $("filelist").innerHTML = "";
    $("foot-status").textContent = "Trimble Converter";
    refreshGenerate();
    show("idle");
  }

  function bind() {
    if (window.__bound) return; window.__bound = true;
    $("min").addEventListener("click", () => { const a = api(); if (a) a.win_minimize(); });
    $("max").addEventListener("click", () => { const a = api(); if (a) a.win_maximize(); });
    $("close").addEventListener("click", () => { const a = api(); if (a) a.win_close(); });

    $("choose").addEventListener("click", (e) => { e.stopPropagation(); chooseFiles(); });
    $("drop").addEventListener("click", chooseFiles);
    $("drop").addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); chooseFiles(); } });
    const dz = $("drop");
    dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
    dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
    dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); chooseFiles(); });

    $("opt-excel").addEventListener("change", refreshGenerate);
    $("opt-pdf").addEventListener("change", refreshGenerate);
    $("generate").addEventListener("click", generate);
    $("cancel").addEventListener("click", () => { state.cancelled = true; reset(); });
    $("again").addEventListener("click", reset);
    $("retry").addEventListener("click", reset);
    $("open-folder").addEventListener("click", () => { const a = api(); if (a && state.folder) a.open_folder(state.folder); });
  }

  async function initApi() {
    const a = api();
    if (a && a.info) {
      try { const i = await a.info(); if (i && i.version) $("foot-ver").textContent = "v" + i.version; }
      catch (e) { /* ignore */ }
    }
  }

  if (document.readyState !== "loading") bind();
  else document.addEventListener("DOMContentLoaded", bind);
  if (window.pywebview) initApi();
  else window.addEventListener("pywebviewready", initApi);
})();
