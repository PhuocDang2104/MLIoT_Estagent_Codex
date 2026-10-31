import { panorama } from "./studio-panorama.js";
const $ = (selector) => document.querySelector(selector);
const states = {
  queued: "Đang chờ",
  running: "Đang xử lý",
  completed: "Hoàn tất",
  needs_review: "Cần duyệt",
  waiting_integration: "Chờ kết nối dựng 3D",
  failed: "Cần thử lại",
  rejected: "Đã từ chối",
};
const stepNames = {
  understand: "Phân tích bất động sản",
  scene: "Nhận diện không gian",
  spatial: "Chuẩn bị bố cục",
  spatial_review: "Kiểm tra bố cục",
  build_model: "Dựng nhà 3D",
  mapping: "Liên kết checkpoint",
  semantic: "Tổng hợp thông tin",
  navigation: "Tạo điều hướng",
  narration: "Soạn lời giới thiệu",
  final_review: "Duyệt nội dung",
  voice: "Tạo giọng AI",
  assemble: "Kiểm tra gói tour",
  workflow: "Trạng thái bản nháp",
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
    throw new Error("API chưa sẵn sàng. Kiểm tra kết nối backend của Studio.");
  }
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.error || "Dữ liệu chưa hợp lệ. Kiểm tra lại các trường đã nhập.",
    );
  return data;
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
      "aria-label": "Xem " + asset.name,
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
      "aria-label": "Xóa " + asset.name,
    });
    b.onclick = remove;
    tile.append(b);
  }
  return tile;
}
async function selectFiles(files) {
  for (const file of files) {
    if (
      !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
      file.size > 20 * 1024 * 1024 ||
      selected.length >= 12
    ) {
      notify(
        "Chỉ nhận tối đa 12 ảnh JPEG, PNG, WebP, không quá 20 MB/ảnh.",
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
      if (selected.length >= 12 || selected.some((p) => p.hash === hash)) {
        URL.revokeObjectURL(url);
        continue;
      }
      selected.push({ file, url, hash });
    } catch {
      URL.revokeObjectURL(url);
      notify("Không đọc được ảnh " + file.name, true);
    }
  }
  $("#panoramas").value = "";
  renderSelected();
}
function renderSelected() {
  $("#selected-images").replaceChildren(
    ...selected.map((p) =>
      imageTile({ name: p.file.name }, p.url, () => {
        URL.revokeObjectURL(p.url);
        selected = selected.filter((x) => x !== p);
        renderSelected();
      }),
    ),
  );
}
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
  $("#create-view").hidden = false;
  $("#workspace-view").hidden = true;
  $("#top-status").textContent = "Bản nháp";
  history.pushState({}, "", "/business/create");
  renderProjects();
  notify(
    session?.configured
      ? ""
      : "Chưa kết nối OpenAI. Bạn vẫn có thể lưu dữ liệu; cấu hình key ở backend để bắt đầu tạo tour.",
  );
}
$("#new-project").onclick = () => {
  if (!busy) newProject();
};
$("#create-form").onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  if (!selected.length)
    return notify("Thêm ít nhất một panorama trước khi lưu.", true);
  const form = new FormData(e.target);
  if ($("#music").files.length && !String(form.get("music_credit")).trim())
    return notify("Nhập nguồn và quyền sử dụng nhạc nền.", true);
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
      notify(`Đang lưu dữ liệu ${++index}/${files.length}…`);
      await api(
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
      );
    }
    pendingRequest = null;
    selected.forEach((p) => URL.revokeObjectURL(p.url));
    selected = [];
    renderSelected();
    e.target.reset();
    await loadSession();
    await openProject(result.id);
    notify("Dữ liệu đã lưu. Bạn có thể bắt đầu tạo tour.");
  } catch (error) {
    notify(
      error.message +
        " Dữ liệu đã tải thành công được giữ lại; gửi lại để tiếp tục.",
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
  $("#asset-count").textContent =
    project.assets.filter((a) => a.kind === "panorama").length + " panorama";
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
function renderHistory() {
  $("#history").replaceChildren(
    ...project.generations.map((g, i) => {
      const div = node("div", null, { class: "history-item" }),
        b = node(
          "button",
          `Bản ${project.generations.length - i} · ${states[g.status] || g.status}`,
        );
      b.onclick = () =>
        openGeneration(g.id).catch((e) => notify(e.message, true));
      div.append(b);
      return div;
    }),
  );
  if (!project.generations.length)
    $("#history").append(
      node("p", "Chưa có lần tạo tour.", { class: "muted" }),
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
  if (!generation || !["queued", "running"].includes(generation.status)) return;
  const id = generation.id;
  source = new EventSource(
    `/api/studio/generations/${id}/events?after=${generation.events.at(-1)?.event_id || 0}`,
  );
  source.onmessage = () => {
    if (generation?.id !== id) return;
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(
      () => refreshGeneration(id).catch((e) => notify(e.message, true)),
      150,
    );
  };
  source.addEventListener("settled", () => {
    if (generation?.id !== id) return;
    stopStream();
    clearTimeout(refreshTimer);
    refreshGeneration(id)
      .then(() => renderPreview())
      .catch((e) => notify(e.message, true));
  });
  source.onerror = () => {
    if (generation?.id !== id) return;
    stopStream();
    notify("Kết nối tiến trình bị gián đoạn. Đang khôi phục…");
    setTimeout(() => {
      if (generation?.id === id)
        refreshGeneration(id)
          .then(() => connectStream())
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
      node("h3", "Tour đã xuất bản"),
      node("p", "Đây là phiên bản bất biến đã được phê duyệt."),
      node("a", "Mở tour đã xuất bản ↗", {
        href: `/studio-tour.html?id=${result.id}`,
        target: "_blank",
        rel: "noopener",
      }),
    );
    notify("Đã xuất bản phiên bản đã duyệt.");
  } catch (e) {
    notify(e.message, true);
  } finally {
    busy = false;
    $("#publish").disabled = false;
  }
};
function renderGeneration() {
  const g = generation;
  $("#generate").hidden = !!g;
  $("#generate").disabled = !session.configured;
  $("#retry").hidden = !(
    g?.status === "failed" ||
    (g?.status === "waiting_integration" && session.geometry_configured)
  );
  $("#retry").textContent =
    g?.status === "waiting_integration"
      ? "Tiếp tục dựng 3D ↗"
      : "Thử lại bước đang dở";
  $("#publish").hidden = g?.status !== "completed";
  $("#top-status").textContent = g ? states[g.status] : "Bản nháp";
  $("#generation-status").textContent = g ? states[g.status] : "Chưa bắt đầu";
  $("#empty-stream").hidden = !!g;
  $("#share").hidden = true;
  const latest = new Map();
  for (const event of g?.events || []) latest.set(event.node_id, event);
  $("#activity").replaceChildren(
    ...[...latest.values()].map((event) => {
      const card = node("article", null, {
          class: "activity-card",
          "data-status": event.status,
        }),
        head = node("div", null, { class: "activity-head" });
      head.append(
        node("h3", stepNames[event.node_id] || "Cập nhật tour"),
        node("span", states[event.status] || event.status, {
          class: "state-label",
        }),
      );
      card.append(head, node("p", event.message));
      if (event.node_id === "scene" && g.observations.length)
        for (const o of g.observations)
          card.append(node("p", o.label + " — " + o.summary));
      return card;
    }),
  );
  if (g?.brief) {
    $("#brief").replaceChildren(
      node("p", g.brief.summary, { class: "muted" }),
      ...g.brief.facts.map((f) => {
        const n = node("div", f.text, { class: "fact" });
        n.append(
          node(
            "small",
            {
              verified: "Business cung cấp",
              observed: "Quan sát từ ảnh",
              inferred: "Suy luận, cần xác nhận",
              unknown: "Chưa có bằng chứng",
            }[f.provenance],
          ),
        );
        return n;
      }),
    );
  } else
    $("#brief").replaceChildren(
      node("p", "Thông tin AI phân loại sẽ xuất hiện tại đây.", {
        class: "muted",
      }),
    );
  if (g?.error) notify(g.error, true);
  renderReview();
}
function renderReview() {
  const box = $("#review"),
    editor = $("#script-editor");
  const key =
    generation?.id + ":" + generation?.status + ":" + generation?.review?.kind;
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
        ? "Cùng kiểm tra bố cục"
        : g.review.kind === "final"
          ? "Duyệt nội dung trước khi tạo giọng"
          : "Đã sẵn sàng cho bước dựng 3D",
    ),
    node("p", g.review.message, { class: "muted" }),
  );
  if (g.review.kind === "integration") {
    box.append(
      node(
        "p",
        "Các phân tích và checkpoint đã được lưu. Bản nháp sẽ tiếp tục khi worker dựng mô hình được tích hợp.",
        { class: "muted" },
      ),
    );
    return;
  }
  const form = node("form");
  box.append(form);
  if (g.review.kind === "spatial") {
    form.append(
      node(
        "p",
        "Đây là danh sách checkpoint, chưa phải bản vẽ đo đạc. Chỉ thêm đường đi có thật và nhập hướng mũi tên đã kiểm tra trong panorama.",
        { class: "muted" },
      ),
    );
    for (const room of g.rooms) {
      const row = node("div", null, {
          class: "room-edit",
          "data-checkpoint": room.checkpoint_id,
        }),
        label = node("label", room.checkpoint_id + " · Tên khu"),
        yawLabel = node("label", "Hướng nhìn °");
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
    fieldset.append(node("legend", "Đường nối giữa các checkpoint"), links);
    const add = node("button", "＋ Thêm đường nối hai chiều", {
      type: "button",
    });
    add.onclick = () => {
      const row = node("div", null, { class: "link-row" });
      for (const name of ["source", "target"]) {
        const select = node("select", null, {
          name,
          "aria-label": name === "source" ? "Checkpoint đi" : "Checkpoint đến",
        });
        for (const room of g.rooms)
          select.append(
            node("option", room.label, { value: room.checkpoint_id }),
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
            placeholder: "yaw °",
            "aria-label": name === "forward" ? "Hướng đi °" : "Hướng về °",
          }),
        );
      const remove = node("button", "×", {
        type: "button",
        "aria-label": "Xóa đường nối",
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
      node("h2", "Lời giới thiệu từng khu"),
      node("p", g.script.introduction, { class: "muted" }),
    );
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
        ? "Xác nhận & tiếp tục ↗"
        : "Duyệt & tạo giọng AI ↗",
      { class: "primary", type: "submit" },
    ),
    reject = node("button", "Từ chối bản nháp", { type: "button" });
  form.append(approve, reject);
  reject.onclick = () =>
    action(reject, `/generations/${g.id}/review`, {
      kind: g.review.kind,
      decision: "reject",
    });
  form.onsubmit = (e) => {
    e.preventDefault();
    const payload = { kind: g.review.kind, decision: "approve" };
    if (g.review.kind === "spatial") {
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
      payload.scripts = g.script.segments.map((segment) => ({
        ...segment,
        text: editor
          .querySelector(`[data-segment=${segment.checkpoint_id}]`)
          .value.trim(),
      }));
      if (payload.scripts.some((s) => !s.text))
        return notify("Lời giới thiệu không được để trống.", true);
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
        $("#preview-caption").textContent = asset.name + " · Kéo để xoay 360°.";
      } else {
        box.append(
          node("img", null, { src: assetUrl(asset), alt: asset.name }),
        );
        $("#preview-caption").textContent =
          asset.name + " · Ảnh thường, chưa xác nhận góc phủ 360°.";
      }
      return;
    }
  }
  if (mode === "floorplan") {
    const asset = project.assets.find((a) => a.kind === "floorplan");
    if (asset) {
      box.append(
        node("img", null, {
          src: assetUrl(asset),
          alt: "Bản vẽ do Business cung cấp",
        }),
      );
      $("#preview-caption").textContent =
        "Bản vẽ nguồn do Business cung cấp. Chưa suy đoán kích thước từ ảnh.";
      return;
    }
  }
  if (mode === "model" && generation?.model) {
    const div = node("div");
    div.append(
      node("p", "Mô hình đã được worker xuất thành GLB."),
      node("a", "Tải mô hình 3D ↗", {
        href: assetUrl(generation.model),
        download: "house.glb",
      }),
    );
    box.append(div);
    return;
  }
  if (mode === "tour" && generation?.package) {
    const div = node("div");
    div.append(node("p", "Gói tour đã được kiểm tra. Giọng đọc do AI tạo."));
    for (const audio of generation.package.narration.audio) {
      const player = node("audio", null, {
        controls: "",
        src: assetUrl(audio),
      });
      player.onplay = () => {
        for (const other of div.querySelectorAll("audio"))
          if (other !== player) other.pause();
      };
      div.append(node("p", audio.checkpoint_id), player);
    }
    box.append(div);
    return;
  }
  box.append(
    node(
      "p",
      {
        panorama: "Chưa có panorama.",
        floorplan:
          "Chưa có bản vẽ mặt bằng. Bố cục và kích thước cần được Business xác minh.",
        model: "Mô hình 3D sẽ xuất hiện khi worker dựng nhà hoàn thành.",
        tour: "Bản xem trước tour sẽ có sau khi tạo đủ asset và được duyệt.",
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
  if (!session.configured)
    notify(
      "Chưa kết nối OpenAI. Bạn vẫn có thể lưu dữ liệu; cấu hình key ở backend để bắt đầu tạo tour.",
    );
} catch (e) {
  notify(e.message, true);
  $("#save-project").disabled = true;
}
