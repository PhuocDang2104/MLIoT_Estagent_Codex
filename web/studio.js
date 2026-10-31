import { panorama } from "./studio-panorama.js";
import { houseModel, planPreview } from "./studio-model.js";
const $ = (selector) => document.querySelector(selector);
const states = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  needs_review: "Review needed",
  waiting_integration: "Waiting for 3D service",
  failed: "Retry needed",
  rejected: "Rejected",
};
const stepNames = {
  edit: "Apply edits",
  understand: "Understand property",
  scene: "Identify spaces",
  spatial: "Prepare layout",
  spatial_review: "Review layout",
  build_model: "Build 3D house",
  mapping: "Link checkpoints",
  semantic: "Summarize information",
  navigation: "Create navigation",
  narration: "Write introduction",
  final_review: "Review content",
  voice: "Generate AI voice",
  assemble: "Validate tour package",
  workflow: "Draft status",
};
let session,
  project,
  generation,
  source,
  selected = [],
  mode = "panorama",
  activeAsset,
  disposePreview = () => {},
  reviewKey = "",
  busy = false,
  pendingRequest = null;
const expandedActivities = new Map();
// Keep successful files for a retry of the same idempotent project creation.
const uploadedFiles = new Map();
let sampleAbort, selectionEpoch = 0, sampleLoading = false;
const sampleName = "Seoul sample apartment";
const sampleDescription = "Explore this Seoul apartment using eight supplied panoramas. Recreate the visible spaces, materials and furnishings. No measured dimensions are supplied; clarify uncertain dimensions and connections before modeling.";
function cancelSample() {
  sampleAbort?.abort();
  sampleAbort = null;
  selectionEpoch++;
  sampleLoading = false;
  $("#save-project").disabled = busy;
  $("#load-sample").disabled = busy;
}
function clearSelection() {
  cancelSample();
  selected.forEach(p => URL.revokeObjectURL(p.url));
  selected = [];
  pendingRequest = null;
  $("#panorama-confirmed").checked = false;
  renderSelected();
}
async function loadSample() {
  if (busy || project) return;
  clearSelection();
  const epoch = selectionEpoch;
  const controller = sampleAbort = new AbortController();
  sampleLoading = true;
  $("#save-project").disabled = true;
  $("#load-sample").disabled = true;
  $("#sample-status").textContent = "Loading the eight Seoul sample panoramas…";
  try {
    const base = "/api/demos/seoul-apartment/assets/";
    const response = await fetch(base + "house/manifest.json", { signal: controller.signal });
    if (!response.ok) throw Error("Sample unavailable");
    const manifest = await response.json();
    const captures = manifest.captures;
    if (!Array.isArray(captures) || captures.length !== 8 ||
        new Set(captures.map(c => c.image)).size !== 8 ||
        captures.some(c => !/^house\/panos\/[0-9]{8}\.jpg$/.test(c.image))) throw Error("Invalid sample manifest");
    const files = await Promise.all(captures.map(async capture => {
      const image = await fetch(base + capture.image, { signal: controller.signal });
      if (!image.ok) throw Error("Sample image unavailable");
      const blob = await image.blob();
      if (!blob.size || blob.size > 20 * 1024 * 1024) throw Error("Invalid sample image size");
      return new File([blob], capture.image.split("/").pop(), { type: "image/jpeg" });
    }));
    if (epoch !== selectionEpoch) return;
    await selectFiles(files, { sample: true, epoch });
    if (epoch !== selectionEpoch) return;
    if (selected.length !== 8) throw Error("Could not read all sample images");
    $("#panorama-confirmed").checked = true;
    const form = $("#create-form");
    if (!form.elements.name.value) form.elements.name.value = sampleName;
    if (!form.elements.description.value) form.elements.description.value = sampleDescription;
    $("#sample-status").textContent = "8 Seoul sample panoramas selected. Remove any image or choose your own. Nothing is uploaded until you save.";
  } catch (error) {
    if (epoch !== selectionEpoch || error.name === "AbortError") return;
    controller.abort();
    selected.forEach(p => URL.revokeObjectURL(p.url));
    selected = [];
    renderSelected();
    $("#sample-status").textContent = "The Seoul sample could not load. Try again or upload your own images.";
  } finally {
    if (epoch === selectionEpoch) {
      sampleLoading = false;
      $("#save-project").disabled = busy;
      $("#load-sample").disabled = busy;
    }
  }
}
let editKey = "", editProposal = null, editRequest = null, applyRequest = null;
setInterval(() => {
  const clock = document.querySelector('[data-model-clock]');
  if (clock?.dataset.modelClock) clock.textContent=`${clock.dataset.phase} · ${Math.max(0,Math.floor((Date.now()-Number(clock.dataset.modelClock))/1000))}s`;
}, 1000);
function node(tag, text, attrs = {}) {
  const n = document.createElement(tag);
  if (text !== null && text !== undefined) n.textContent = text;
  for (const [key, value] of Object.entries(attrs)) n.setAttribute(key, value);
  return n;
}
function notify(text, error = false) {
  $("#notice").hidden = !text;
  $("#notice").textContent = text;
  $("#notice").classList.toggle("error", error);
}
function requestId() {
  return crypto.randomUUID();
}
async function api(path, options = {}) {
  const response = await fetch("/api/studio" + path, {
    credentials: "same-origin",
    ...options,
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("The API is unavailable. Check the Studio backend connection.");
  }
  if (!response.ok) {
    const error = new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.error || "Invalid input. Please check the fields you entered.",
    );
    error.status = response.status;
    error.code = data.code;
    error.retryAfter = Math.ceil(Number(data.retry_after ?? response.headers.get('Retry-After')));
    throw error;
  }
  return data;
}
async function uploadWithRetry(operation, saved, total) {
  for (let attempt = 0; ; attempt++) {
    try { return await operation(); }
    catch (error) {
      if (attempt >= 2 || error.status !== 429 ||
          !['rate_limited', 'concurrency_limited'].includes(error.code) ||
          !(error.retryAfter > 0 && error.retryAfter <= 120)) throw error;
      const deadline = Date.now() + error.retryAfter * 1000 + 250;
      while (Date.now() < deadline) {
        const remaining = Math.ceil((deadline - Date.now()) / 1000);
        notify(`Upload paused · resuming in ${remaining}s. Saved ${saved}/${total} files.`);
        await new Promise(resolve => setTimeout(resolve, Math.min(1000, deadline - Date.now())));
      }
    }
  }
}
function post(path, data) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
function assetUrl(asset) {
  return `/api/studio/projects/${project.id}/assets/${asset.id || asset.asset_id}`;
}
function stopStream() {
  source?.close();
  source = null;
}
function imageTile(asset, url, remove) {
  const tile = node("div", null, { class: "image-tile" }),
    button = node("button", null, {
      type: "button",
      "aria-label": "View " + asset.name,
    }),
    image = node("img", null, { src: url, alt: asset.name });
  button.append(image);
  button.onclick = () => {
    if (project) {
      activeAsset = asset;
      mode = asset.kind === "floorplan" ? "floorplan" : "panorama";
      renderPreview();
    } else {
      const d = $("#image-dialog");
      d.querySelector("img").src = url;
      d.querySelector("p").textContent = asset.name;
      d.showModal();
    }
  };
  tile.append(button, node("p", asset.name));
  if (remove) {
    const b = node("button", "×", {
      class: "remove",
      type: "button",
      "aria-label": "Remove " + asset.name,
    });
    b.onclick = remove;
    tile.append(b);
  }
  return tile;
}
async function selectFiles(files, { sample = false, epoch } = {}) {
  if (busy || !files.length) return;
  if (!sample) {
    if (sampleLoading || selected.some(p => p.sample)) {
      clearSelection();
      const form = $("#create-form");
      if (form.elements.name.value === sampleName) form.elements.name.value = "";
      if (form.elements.description.value === sampleDescription) form.elements.description.value = "";
    }
    cancelSample();
    epoch = selectionEpoch;
    pendingRequest = null;
    $("#sample-status").textContent = "Your images are selected. Use the Seoul sample at any time.";
  }
  for (const file of files) {
    if (epoch !== selectionEpoch) return;
    if (
      !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
      file.size > 20 * 1024 * 1024 ||
      selected.length >= 12
    ) {
      notify(
        "Select up to 12 JPEG, PNG or WebP images, no larger than 20 MB each.",
        true,
      );
      continue;
    }
    const bytes = await file.arrayBuffer(),
      hash = Array.from(
        new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
      ).join(",");
    if (selected.some((p) => p.hash === hash)) continue;
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      if (epoch !== selectionEpoch || selected.length >= 12 || selected.some((p) => p.hash === hash)) {
        URL.revokeObjectURL(url);
        continue;
      }
      selected.push({ file, url, hash, sample });
    } catch {
      URL.revokeObjectURL(url);
      notify("Could not read image " + file.name, true);
    }
  }
  $("#panoramas").value = "";
  renderSelected();
}
function renderSelected() {
  $("#selected-images").replaceChildren(
    ...selected.map((p) =>
      imageTile({ name: p.file.name }, p.url, () => {
        if (busy) return;
        cancelSample();
        pendingRequest = null;
        URL.revokeObjectURL(p.url);
        selected = selected.filter((x) => x !== p);
        if (!selected.length) $("#panorama-confirmed").checked = false;
        $("#sample-status").textContent = `${selected.length} images selected. Nothing is uploaded until you save.`;
        renderSelected();
      }),
    ),
  );
}
$("#load-sample").onclick = loadSample;
$("#clear-images").onclick = () => {
  if (busy) return;
  clearSelection();
  $("#sample-status").textContent = "Selection cleared. Upload your own images or use the Seoul sample.";
};
window.addEventListener("pagehide", () => {
  cancelSample();
});
$("#panoramas").onchange = (e) => selectFiles([...e.target.files]);
for (const type of ["dragover", "dragenter"])
  $("#dropzone").addEventListener(type, (e) => {
    e.preventDefault();
    $("#dropzone").classList.add("dragging");
  });
for (const type of ["drop", "dragleave"])
  $("#dropzone").addEventListener(type, (e) => {
    e.preventDefault();
    $("#dropzone").classList.remove("dragging");
  });
$("#dropzone").addEventListener("drop", (e) =>
  selectFiles([...e.dataTransfer.files]),
);
$("#close-dialog").onclick = () => $("#image-dialog").close();

function renderProjects() {
  $("#projects").replaceChildren(
    ...session.projects.map((p) => {
      const b = node("button", p.name, {
        type: "button",
        class: project?.id === p.id ? "active" : "",
      });
      b.onclick = () => openProject(p.id).catch((e) => notify(e.message, true));
      return b;
    }),
  );
}
async function loadSession() {
  session = await api("/session");
  renderProjects();
}
function newProject() {
  stopStream();
  disposePreview();
  project = null;
  generation = null;
  activeAsset = null;
  reviewKey = "";
  pendingRequest = null;
  uploadedFiles.clear();
  editKey = "";
  editProposal = editRequest = applyRequest = null;
  $("#create-view").hidden = false;
  $("#workspace-view").hidden = true;
  $("#top-status").textContent = "Draft";
  $("#top-status").dataset.status = "draft";
  if (location.pathname !== "/business/create") history.pushState({}, "", "/business/create");
  renderProjects();
  notify(session?.configured ? "" : "OpenAI is not connected. You can still save a draft.");
  if (!selected.length) void loadSample();
}

$("#new-project").onclick = () => {
  if (!busy) newProject();
};
$("#create-form").onsubmit = async (e) => {
  e.preventDefault();
  if (busy || sampleLoading) return;
  if (!selected.length)
    return notify("Add at least one panorama before saving.", true);
  const form = new FormData(e.target);
  if ($("#music").files.length && !String(form.get("music_credit")).trim())
    return notify("Enter the music source and usage rights.", true);
  busy = true;
  $("#save-project").disabled = true;
  try {
    pendingRequest ??= {
      request_id: requestId(),
      name: form.get("name"),
      description: form.get("description"),
      locale: form.get("locale"),
      voice: form.get("voice"),
      panorama_confirmed: form.get("panorama_confirmed") === "on",
    };
    const result = await post("/projects", pendingRequest);
    if (!uploadedFiles.has(result.id)) uploadedFiles.set(result.id, new Set());
    const saved = uploadedFiles.get(result.id);
    let index = 0;
    const files = [
      ...selected.map((p) => ({ file: p.file, kind: "panorama" })),
      ...[...$("#floorplan").files].map((file) => ({
        file,
        kind: "floorplan",
      })),
      ...[...$("#music").files].map((file) => ({ file, kind: "music" })),
    ];
    for (const item of files) {
      if (saved.has(item.file)) { index++; continue; }
      notify(`Saving file ${++index}/${files.length}…`);
      await uploadWithRetry(() => api(
        `/projects/${result.id}/assets?` +
          new URLSearchParams({
            kind: item.kind,
            name: item.file.name,
            credit: form.get("music_credit") || "",
          }),
        {
          method: "POST",
          headers: {
            "Content-Type": item.file.type || "application/octet-stream",
          },
          body: item.file,
        },
      ), index - 1, files.length);
      saved.add(item.file);
    }
    if (!$("#music").files.length && $("#placeholder-music").checked) {
      const action = { request_id: requestId() };
      await uploadWithRetry(() => post(`/projects/${result.id}/music/placeholder`, action), files.length, files.length);
    }
    uploadedFiles.delete(result.id);
    pendingRequest = null;
    selected.forEach((p) => URL.revokeObjectURL(p.url));
    selected = [];
    renderSelected();
    e.target.reset();
    await loadSession();
    await openProject(result.id);
    notify(
      session.configured
        ? "Source files saved."
        : "Draft saved. Connect OpenAI to generate a tour.",
    );
  } catch (error) {
    notify(
      error.message +
        " Successfully uploaded files are preserved; submit again to continue.",
      true,
    );
  } finally {
    busy = false;
    $("#save-project").disabled = false;
  }
};
$("#create-form").addEventListener("input", () => {
  pendingRequest = null;
});

async function openProject(id) {
  cancelSample();
  stopStream();
  disposePreview();
  project = await api("/projects/" + id);
  generation = null;
  activeAsset = project.assets.find((a) => a.kind === "panorama");
  reviewKey = "";
  $("#create-view").hidden = true;
  $("#workspace-view").hidden = false;
  $("#project-name").textContent = project.name;
  $("#project-description").textContent = project.description;
  history.replaceState({}, "", `/business/projects/${id}/generate`);
  renderProjects();
  renderAssets();
  renderHistory();
  if (project.generations.length)
    await openGeneration(project.generations[0].id);
  else {
    renderGeneration();
    renderPreview();
  }
}
function renderAssets() {
  renderMusic();
  $("#asset-count").textContent =
    project.assets.filter((a) => a.kind === "panorama").length + " images";
  $("#assets").replaceChildren(
    ...project.assets
      .filter((a) => ["panorama", "floorplan"].includes(a.kind))
      .map((a) =>
        imageTile(
          a,
          assetUrl(a),
          project.generations.length
            ? null
            : async () => {
                try {
                  await api(`/projects/${project.id}/assets/${a.id}`, {
                    method: "DELETE",
                  });
                  await openProject(project.id);
                } catch (e) {
                  notify(e.message, true);
                }
              },
        ),
      ),
  );
}
function renderMusic() {
  const track = project.assets.find((a) => a.kind === "music");
  const panel = $("#current-music");
  panel.replaceChildren();
  if (track) {
    panel.append(node("strong", track.name), node("audio", null, {
      controls: "", preload: "none", src: assetUrl(track), "aria-label": "Preview background music",
    }), node("p", track.credit, { class: "muted" }));
  } else panel.append(node("p", "No music yet. Choose the sample track or upload a WAV before publishing."));
  $("#music-options").hidden = !!project.published.length;
}
async function saveMusic(placeholder) {
  if (busy || !project) return;
  const file = $("#replacement-music").files[0];
  const credit = $("#replacement-credit").value.trim();
  if (!placeholder && (!file || !credit)) return notify("Choose a WAV and enter its source and usage rights.", true);
  busy = true;
  $("#save-music").disabled = $("#use-placeholder").disabled = true;
  try {
    if (placeholder) await post(`/projects/${project.id}/music/placeholder`, { request_id: requestId() });
    else await api(`/projects/${project.id}/assets?` + new URLSearchParams({kind:"music",name:file.name,credit}),
      {method:"POST",headers:{"Content-Type":"audio/wav"},body:file});
    project = await api("/projects/" + project.id);
    renderMusic();
    notify("Music saved. You do not need to regenerate the tour.");
  } catch (error) { notify(error.message, true); }
  finally { busy = false; $("#save-music").disabled = $("#use-placeholder").disabled = false; }
}
$("#use-placeholder").onclick = () => saveMusic(true);
$("#save-music").onclick = () => saveMusic(false);
function renderHistory() {
  $("#history-count").textContent = project.generations.length;
  $("#history").replaceChildren(
    ...project.generations.map((g, i) => {
      const div = node("div", null, { class: "history-item" }),
        b = node(
          "button",
          `Version ${project.generations.length - i} · ${states[g.status] || g.status}`,
        );
      b.onclick = () =>
        openGeneration(g.id).catch((e) => notify(e.message, true));
      div.append(b);
      return div;
    }),
  );
  if (!project.generations.length)
    $("#history").append(
      node("p", "No tour generations yet.", { class: "muted" }),
    );
}
async function openGeneration(id) {
  stopStream();
  generation = await api("/generations/" + id);
  reviewKey = "";
  renderGeneration();
  renderPreview();
  connectStream();
}
let refreshTimer;
async function refreshGeneration(id) {
  const value = await api("/generations/" + id);
  if (generation?.id !== id) return;
  generation = value;
  project.generations = project.generations.map((g) =>
    g.id === id ? { ...g, status: value.status } : g,
  );
  renderGeneration();
  renderHistory();
}
function connectStream() {
  stopStream();
  if (!generation || !["queued", "running"].includes(generation.status)) return;
  const id = generation.id;
  source = new EventSource(
    `/api/studio/generations/${id}/events?after=${generation.events.at(-1)?.event_id || 0}`,
  );
  const stream = source;
  source.onmessage = () => {
    if (source !== stream || generation?.id !== id) return;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(
      () => refreshGeneration(id).catch((e) => notify(e.message, true)),
      150,
    );
  };
  source.addEventListener("settled", () => {
    if (source !== stream || generation?.id !== id) return;
    stopStream();
    clearTimeout(refreshTimer);
    refreshGeneration(id)
      .then(() => renderPreview())
      .catch((e) => notify(e.message, true));
  });
  source.onerror = () => {
    if (source !== stream || generation?.id !== id) return;
    stopStream();
    setTimeout(() => {
      if (generation?.id === id)
        refreshGeneration(id)
          .then(() => {
            if(generation?.id !== id) return;
            if(['queued','running'].includes(generation.status)) connectStream();
            else renderPreview();
          })
          .catch((e) => notify(e.message, true));
    }, 2000);
  };
}
async function action(button, path, data) {
  if (busy) return;
  busy = true;
  button.disabled = true;
  try {
    const result = await post(path, { request_id: requestId(), ...data });
    generation = await api("/generations/" + (result.id || generation.id));
    project = await api("/projects/" + project.id);
    renderGeneration();
    renderAssets();
    renderHistory();
    connectStream();
    notify("");
  } catch (e) {
    notify(e.message, true);
  } finally {
    busy = false;
    button.disabled = false;
  }
}
$("#generate").onclick = () =>
  action($("#generate"), `/projects/${project.id}/generations`, {});
$("#retry").onclick = () =>
  action($("#retry"), `/generations/${generation.id}/retry`, {});
$("#publish").onclick = async () => {
  if (busy) return;
  busy = true;
  $("#publish").disabled = true;
  try {
    const result = await post(`/generations/${generation.id}/publish`, {
      request_id: requestId(),
    });
    const box = $("#share");
    box.hidden = false;
    box.replaceChildren(
      node("h3", "Published tour"),
      node("p", "Ready to share."),
      node("a", "Open tour ↗", {
        href: `/studio-tour.html?id=${result.id}`,
        target: "_blank",
        rel: "noopener",
      }),
    );
    project.published = [
      ...(project.published || []),
      { id: result.id, generation: generation.id },
    ];
    renderStages();
    renderMusic();
    notify("The approved version has been published.");
  } catch (e) {
    notify(e.message, true);
  } finally {
    busy = false;
    $("#publish").disabled = false;
  }
};
function renderStages() {
  const g = generation;
  const published =
    !!g && project.published?.some((p) => p.generation === g.id);
  const completed = new Set(
    (g?.events || [])
      .filter(
        (e) =>
          e.status === "completed" &&
          e.node_id in stepNames &&
          e.node_id !== "workflow",
      )
      .map((e) => e.node_id),
  );
  if (
    (g?.observations.length || 0) <
    project.assets.filter((a) => a.kind === "panorama").length
  )
    completed.delete("scene");
  // A completed TTS call is one segment, not the whole voice milestone.
  if (!g?.package) completed.delete("voice");
  const contentNodes = [
    "semantic",
    "navigation",
    "narration",
    "final_review",
    "voice",
  ];
  const current =
    published || g?.package
      ? 3
      : g?.events.some((e) => contentNodes.includes(e.node_id))
        ? 2
        : 1;
  document.querySelectorAll("[data-stage]").forEach((item, index) => {
    item.dataset.state =
      index < current || published
        ? "done"
        : index === current
          ? "current"
          : "pending";
    if (index === current && !published)
      item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  $("#stage-summary").textContent = g
    ? `${completed.size}/12 steps complete`
    : "Source files saved";
  if (published) $("#top-status").textContent = "Published";
}
function renderGeneration() {
  const g = generation;
  $("#generate").hidden = !!g;
  $("#generate").disabled = !session.configured;
  $("#retry").hidden = !(
    g?.status === "failed" ||
    (g?.status === "waiting_integration" && session.geometry_configured)
  );
  $("#retry").textContent =
    g?.status === "waiting_integration" ? "Continue 3D build ↗" : "Retry";
  $("#publish").hidden = g?.status !== "completed";
  $("#top-status").textContent = g ? states[g.status] : "Draft";
  $("#top-status").dataset.status = g?.status || "draft";
  $("#generation-status").textContent = g ? states[g.status] : "Not started";
  $("#empty-stream").hidden = !!g;
  $("#share").hidden = true;
  const latest = new Map();
  for (const event of g?.events || []) latest.set(event.node_id, event);
  const modelingProgress = g?.events?.findLast((e) => e.event_type === "model_progress")?.progress;
  const oldSummary = $(".thinking-summary");
  const summaryScroll = oldSummary ? {top:oldSummary.scrollTop,atBottom:oldSummary.scrollTop+oldSummary.clientHeight>=oldSummary.scrollHeight-30} : {top:0,atBottom:true};
  $("#activity").replaceChildren(
    ...[...latest.values()]
      .filter(
        (event) =>
          event.node_id !== "workflow" ||
          (["failed", "rejected"].includes(event.status) && event.status === g.status),
      )
      .map((event) => {
        const status =
          event.node_id === "scene" &&
          event.status === "completed" &&
          g.observations.length <
            project.assets.filter((a) => a.kind === "panorama").length
            ? "running"
            : event.status;
        const key = `${g.id}:${event.node_id}`;
        const card = node("details", null, {
            class: "activity-card",
            "data-status": status,
            "data-node": event.node_id,
          }),
          summary = node("summary"),
          head = node("div", null, { class: "activity-head" }),
          body = node("div", null, { class: "activity-body" });
        card.open = expandedActivities.has(key)
          ? expandedActivities.get(key)
          : ["running", "failed"].includes(status);
        summary.addEventListener("click", () =>
          expandedActivities.set(key, !card.open),
        );
        head.append(node("h3", stepNames[event.node_id] || "Update tour"));
        summary.append(
          node(
            "span",
            status === "completed"
              ? "✓"
              : ["needs_review", "waiting_integration"].includes(status)
                ? "!"
                : "·",
            { class: "activity-icon", "aria-hidden": "true" },
          ),
          head,
          node(
            "span",
            event.node_id === "scene" && status === "completed"
              ? `${g.observations.length} images`
              : states[status] || status,
            {
              class: "state-label",
            },
          ),
        );
        body.append(
          node(
            "p",
            status === "waiting_integration"
              ? "Layout saved. The 3D service is not ready."
              : event.message,
          ),
        );
        if (event.node_id === "spatial" && modelingProgress) {
          const detail = node("section", null, {class:"model-thinking", "aria-label":"Model reasoning progress"});
          const phases = {connecting:"Connecting",thinking:"Analyzing layout",writing_plan:"Drafting the 3D plan",validating:"Validating the plan"};
          detail.append(node("strong", `${modelingProgress.model} · ${modelingProgress.effort}`),
            node("p", `${phases[modelingProgress.phase] || "Processing"} · ${modelingProgress.elapsed_seconds}s`, {class:"muted", "data-model-clock":status==='running'?modelingProgress.started_at || '':'',"data-phase":phases[modelingProgress.phase] || "Processing"}),
            node("p", "Public reasoning summary from the model. The draft below has not been verified.", {class:"muted"}));
          const text = node("div", modelingProgress.reasoning_summary || "Waiting for the first model summary…", {class:"thinking-summary"});
          detail.append(text);
          const preview=modelingProgress.plan_preview || {};
          if (preview.summary) detail.append(node("p", preview.summary, {class:"plan-summary"}));
          if (modelingProgress.output_characters) detail.append(node("p", `${preview.spaces?.length || 0} spaces · ${preview.captures || 0} checkpoints · ${preview.fixtures || 0} fixtures being described`, {class:"muted"}));
          body.append(detail);
        }
        if (event.node_id === "scene" && g.observations.length) {
          const observations = node("div", null, { class: "observation-list" });
          for (const o of g.observations) {
            const item = node("div", null, { class: "observation-item" });
            item.append(node("strong", o.label), node("p", o.summary));
            observations.append(item);
          }
          body.append(observations);
        }
        card.append(summary, body);
        return card;
      }),
  );
  const newSummary = $(".thinking-summary");
  if (newSummary) newSummary.scrollTop=summaryScroll.atBottom?newSummary.scrollHeight:summaryScroll.top;
  $("#brief-panel").hidden = !g?.brief;
  $("#fact-count").textContent = g?.brief?.facts.length || "";
  if (g?.brief) {
    $("#brief").replaceChildren(
      node("p", g.brief.summary, { class: "muted" }),
      ...g.brief.facts.map((f) => {
        const n = node("div", f.text, { class: "fact" });
        n.append(
          node(
            "small",
            {
              verified: "Provided by you",
              observed: "From images",
              inferred: "Needs confirmation",
              unknown: "Unknown",
            }[f.provenance],
          ),
        );
        return n;
      }),
    );
  } else
    $("#brief").replaceChildren(
      node("p", "Information classified by AI will appear here.", {
        class: "muted",
      }),
    );
  if (g?.error) notify(g.error, true);
  renderStages();
  renderReview();
  renderEditPanel();
}

function renderEditPanel() {
  const g = generation;
  $("#edit-panel").hidden = !g?.rooms?.length || !["completed", "needs_review", "waiting_integration"].includes(g.status);
  const key = g?.id + ":" + g?.revision;
  if (key === editKey) return;
  editKey = key;
  editProposal = null;
  editRequest = null;
  applyRequest = null;
  $("#edit-proposal").hidden = true;
  if (!g?.rooms?.length) return;
  api(`/generations/${g.id}/edits`).then((items) => {
    if (editKey !== key) return;
    editProposal = items.find((x) => x.status === "pending" && x.revision === g.revision && x.plan);
    showEditProposal();
  }).catch((e) => notify(e.message, true));
}

function showEditProposal() {
  const box = $("#edit-proposal"), proposal = editProposal;
  box.replaceChildren();
  box.hidden = !proposal;
  if (!proposal) return;
  box.append(node("p", proposal.plan.reply));
  const changes = node("ul");
  for (const room of proposal.plan.rooms) {
    const values = [room.label, room.summary, room.yaw !== null ? `${room.yaw}°` : null].filter((x) => x !== null);
    changes.append(node("li", `${room.checkpoint_id}: ${values.join(" · ")}`));
  }
  for (const segment of proposal.plan.scripts) changes.append(node("li", `${segment.checkpoint_id}: ${segment.text}`));
  if (proposal.plan.introduction) changes.append(node("li", proposal.plan.introduction));
  if (proposal.plan.order) changes.append(node("li", "Order: " + proposal.plan.order.join(" → ")));
  if (proposal.plan.connections) changes.append(node("li", "Connections updated; the layout needs another review."));
  box.append(changes);
  if (!proposal.can_apply) return;
  const apply = node("button", "Apply · Create new version", { type: "button", class: "primary", id: "apply-edit" });
  apply.onclick = async () => {
    if (busy) return;
    busy = true; apply.disabled = true;
    applyRequest ||= { request_id: requestId(), revision: proposal.revision };
    const gid = generation.id, pid = project.id;
    try {
      const result = await post(`/generations/${gid}/edits/${proposal.id}/apply`, applyRequest);
      if (generation?.id !== gid || project?.id !== pid) return;
      project = await api("/projects/" + pid);
      await openGeneration(result.id);
      renderHistory();
      $("#edit-text").value = "";
    } catch (e) { notify(e.message, true); }
    finally { busy = false; apply.disabled = false; }
  };
  box.append(apply, node("p", "Review the new version before publishing.", { class: "muted" }));
}

$("#edit-form").onsubmit = async (event) => {
  event.preventDefault();
  if (busy || !generation) return;
  const text = $("#edit-text").value.trim();
  if (!text) return;
  busy = true;
  $("#propose-edit").disabled = true;
  if (!editRequest || editRequest.text !== text) editRequest = { request_id: requestId(), revision: generation.revision, text };
  const gid = generation.id;
  try {
    const proposal = await post(`/generations/${gid}/edits`, editRequest);
    if (generation?.id !== gid) return;
    editProposal = proposal; applyRequest = null; editRequest = null;
    showEditProposal(); notify("");
  } catch (e) { notify(e.message, true); }
  finally { busy = false; $("#propose-edit").disabled = false; }
};
function renderReview() {
  const box = $("#review"),
    editor = $("#script-editor");
  const key =
    generation?.id + ":" + generation?.status + ":" + generation?.review?.kind + ":" + generation?.plan_attempts;
  if (key === reviewKey) return;
  reviewKey = key;
  box.replaceChildren();
  editor.replaceChildren();
  box.hidden = true;
  editor.hidden = true;
  const g = generation;
  if (!g?.review) return;
  box.hidden = false;
  box.append(
    node(
      "h2",
      g.review.kind === "spatial"
        ? "Review spaces"
        : g.review.kind === "final"
          ? "Review content"
          : "Waiting for 3D build",
    ),
    node(
      "p",
      g.review.kind === "spatial"
        ? "Confirm the actual spaces and connections."
        : g.review.kind === "final"
          ? "Review the introduction before generating voice."
          : "Layout saved. Continue when the 3D service is ready.",
      { class: "muted" },
    ),
  );
  if (g.review.kind === "integration") {
    return;
  }
  const form = node("form");
  box.append(form);
  if (g.review.kind === "spatial") {
    const plan = g.modeling_plan;
    if (plan) {
      const preview = node('div'); planPreview(preview,plan); form.append(preview);
      form.append(node('p',plan.summary));
      for (const text of [...plan.assumptions,...plan.questions]) form.append(node('p',text,{class:'muted'}));
      const answer = node('textarea',null,{rows:'3',maxlength:'3000','aria-label':'Clarify layout',placeholder:'Add dimensions, shared spaces or connecting doorways…'});
      const revise = node('button',`Update layout (${g.plan_attempts}/3)`,{type:'button'});
      revise.disabled = g.plan_attempts >= 3;
      revise.onclick = () => {
        if(!answer.value.trim()) return notify('Enter the layout clarification.',true);
        action(revise,`/generations/${g.id}/review`,{kind:'spatial',decision:'revise',clarification:answer.value.trim()});
      };
      form.append(answer,revise);
      if(plan.status==='provisional') {
        const label=node('label',' I accept the estimated layout and dimensions.');
        label.prepend(node('input',null,{type:'checkbox',name:'accept_approximate',required:''})); form.append(label);
      }
    }
    form.append(
      node("span", "Estimated · Confirmation needed", { class: "review-flag" }),
    );
    for (const room of g.rooms) {
      const row = node("div", null, {
          class: "room-edit",
          "data-checkpoint": room.checkpoint_id,
        }),
        label = node("label", room.checkpoint_id + " · Space"),
        yawLabel = node("label", "Viewing direction °");
      label.append(
        node("input", null, {
          name: "label",
          required: "",
          maxlength: "100",
          value: room.label,
        }),
      );
      yawLabel.append(
        node("input", null, {
          name: "yaw",
          type: "number",
          required: "",
          min: "-180",
          max: "180",
          value: room.yaw,
        }),
      );
      row.append(label, yawLabel);
      form.append(row);
    }
    const fieldset = node("fieldset"),
      links = node("div", null, { id: "connections" });
    fieldset.append(node("legend", "Two-way connections"), links);
    const add = node("button", "＋ Connect two spaces", {
      type: "button",
    });
    add.onclick = () => {
      const row = node("div", null, { class: "link-row" });
      for (const name of ["source", "target"]) {
        const select = node("select", null, {
          name,
          "aria-label": name === "source" ? "From checkpoint" : "To checkpoint",
        });
        for (const room of g.rooms)
          select.append(
            node("option", `${room.checkpoint_id} · ${room.label}`, { value: room.checkpoint_id }),
          );
        if (name === "target" && g.rooms.length > 1) select.selectedIndex = 1;
        row.append(select);
      }
      for (const name of ["forward", "back"])
        row.append(
          node("input", null, {
            name,
            type: "number",
            required: "",
            min: "-180",
            max: "180",
            placeholder: name === "forward" ? "Forward °" : "Reverse °",
            "aria-label": name === "forward" ? "Forward heading °" : "Reverse heading °",
          }),
        );
      const remove = node("button", "×", {
        type: "button",
        "aria-label": "Remove connection",
      });
      remove.onclick = () => row.remove();
      row.append(remove);
      links.append(row);
    };
    fieldset.append(add);
    form.append(fieldset);
  }
  if (g.review.kind === "final" && g.script) {
    editor.hidden = false;
    editor.append(
      node("h2", "Introduction"),
    );
    const introduction = node("label", "Tour introduction");
    introduction.append(node("textarea", g.script.introduction, {"data-introduction":"",rows:"3",maxlength:"1800",required:""}));
    editor.append(introduction);
    for (const segment of g.script.segments) {
      const label = node(
        "label",
        g.rooms.find((r) => r.checkpoint_id === segment.checkpoint_id)?.label ||
          segment.checkpoint_id,
      );
      label.append(
        node("textarea", segment.text, {
          "data-segment": segment.checkpoint_id,
          rows: "4",
          maxlength: "1800",
          required: "",
        }),
      );
      editor.append(label);
    }
  }
  const approve = node(
      "button",
      g.review.kind === "spatial"
        ? "Confirm & continue ↗"
        : "Approve & generate voice ↗",
      { class: "primary", type: "submit" },
    ),
    reject = node("button", "Reject", { type: "button" });
  form.append(approve, reject);
  if(g.review.kind==='spatial' && g.modeling_plan?.status==='needs_clarification') approve.disabled=true;
  reject.onclick = () =>
    action(reject, `/generations/${g.id}/review`, {
      kind: g.review.kind,
      decision: "reject",
    });
  form.onsubmit = (e) => {
    e.preventDefault();
    const payload = { kind: g.review.kind, decision: "approve", revision: g.revision };
    if (g.review.kind === "spatial") {
      payload.accept_approximate = !!form.querySelector('[name=accept_approximate]')?.checked;
      payload.rooms = [...form.querySelectorAll("[data-checkpoint]")].map(
        (row) => ({
          checkpoint_id: row.dataset.checkpoint,
          label: row.querySelector("[name=label]").value,
          yaw: Number(row.querySelector("[name=yaw]").value),
        }),
      );
      payload.connections = [...form.querySelectorAll(".link-row")].flatMap(
        (row) => {
          const val = (name) => row.querySelector(`[name=${name}]`).value;
          return [
            {
              source: val("source"),
              target: val("target"),
              yaw: Number(val("forward")),
              pitch: 0,
            },
            {
              source: val("target"),
              target: val("source"),
              yaw: Number(val("back")),
              pitch: 0,
            },
          ];
        },
      );
    } else {
      payload.introduction = editor.querySelector('[data-introduction]').value.trim();
      payload.scripts = g.script.segments.map((segment) => ({
        ...segment,
        text: editor
          .querySelector(`[data-segment=${segment.checkpoint_id}]`)
          .value.trim(),
      }));
      if (!payload.introduction || payload.scripts.some((s) => !s.text))
        return notify("The introduction cannot be empty.", true);
    }
    action(approve, `/generations/${g.id}/review`, payload);
  };
}
function renderPreview() {
  disposePreview();
  disposePreview = () => {};
  const box = $("#preview");
  box.replaceChildren();
  for (const b of document.querySelectorAll("[data-mode]"))
    b.setAttribute("aria-selected", String(b.dataset.mode === mode));
  $("#preview-caption").textContent = "";
  if (!project) return;
  if (mode === "panorama") {
    const asset =
      activeAsset?.kind === "panorama"
        ? activeAsset
        : project.assets.find((a) => a.kind === "panorama");
    if (asset) {
      activeAsset = asset;
      if (asset.projection === "equirectangular") {
        disposePreview = panorama(
          box,
          assetUrl(asset),
          generation?.rooms.find((r) => r.asset_id === asset.id)?.yaw || 0,
        );
        $("#preview-caption").textContent = asset.name + " · Drag to look around in 360°.";
      } else {
        box.append(
          node("img", null, { src: assetUrl(asset), alt: asset.name }),
        );
        $("#preview-caption").textContent = asset.name + " · Standard image";
      }
      return;
    }
  }
  if (mode === "floorplan") {
    if(generation?.modeling_plan) {
      planPreview(box,generation.modeling_plan);
      $('#preview-caption').textContent = generation.modeling_plan.scale==='assumed' ? 'Estimated layout · no measured scale.' : 'Layout built from approved data.';
      return;
    }
    const asset = project.assets.find((a) => a.kind === "floorplan");
    if (asset) {
      box.append(
        node("img", null, {
          src: assetUrl(asset),
          alt: "Floorplan supplied by the owner",
        }),
      );
      $("#preview-caption").textContent = "Your supplied floorplan.";
      return;
    }
  }
  if (mode === "model" && generation?.model) {
    disposePreview = houseModel(box,assetUrl(generation.model),generation.rooms,checkpoint => {
      const room=generation.rooms.find(r=>r.checkpoint_id===checkpoint);
      activeAsset=project.assets.find(a=>a.id===room.asset_id); mode='panorama'; renderPreview();
    });
    $('#preview-caption').append(node('a','Download GLB model ↗',{href:assetUrl(generation.model),download:'house.glb'}));
    return;
  }
  if (mode === "tour" && generation?.package) {
    const div = node("div");
    div.append(node("p", "The introduction voice is AI-generated."));
    for (const audio of generation.package.narration.audio) {
      const player = node("audio", null, {
        controls: "",
        src: assetUrl(audio),
      });
      player.onplay = () => {
        for (const other of div.querySelectorAll("audio"))
          if (other !== player) other.pause();
      };
      div.append(
        node(
          "p",
          audio.checkpoint_id === "introduction"
            ? "Overview"
            : generation.rooms.find(
                (r) => r.checkpoint_id === audio.checkpoint_id,
              )?.label || "Khu tham quan",
        ),
        player,
      );
    }
    box.append(div);
    return;
  }
  box.append(
    node(
      "p",
      {
        panorama: "Select an image to preview.",
        floorplan: "No floorplan yet.",
        model: "The model is not ready yet.",
        tour: "The tour will appear when complete.",
      }[mode],
    ),
  );
}
for (const b of document.querySelectorAll("[data-mode]"))
  b.onclick = () => {
    mode = b.dataset.mode;
    renderPreview();
  };
$("#fullscreen").onclick = () =>
  $("#preview").closest(".panel").requestFullscreen?.();
window.addEventListener("popstate", () => {
  const match = location.pathname.match(/\/projects\/([a-f0-9]{32})\/generate/);
  if (match) openProject(match[1]).catch((e) => notify(e.message, true));
  else newProject();
});
window.addEventListener("pagehide", () => {
  stopStream();
  disposePreview();
  selected.forEach((p) => URL.revokeObjectURL(p.url));
});
try {
  await loadSession();
  const match = location.pathname.match(/\/projects\/([a-f0-9]{32})\/generate/);
  if (match) await openProject(match[1]);
  else newProject();
  if (session && !session.configured)
    notify("The AI assistant is currently unavailable. Your saved draft is preserved.");
} catch (e) {
  notify(e.message, true);
  $("#save-project").disabled = true;
}
