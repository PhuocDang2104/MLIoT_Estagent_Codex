import { panorama } from "./studio-panorama.js";
import { houseModel } from "./studio-model.js";
const $ = (s) => document.querySelector(s);
const id = new URLSearchParams(location.search).get("id");
let tour,
  room,
  dispose = () => {},
  narration = new Audio(),
  music = new Audio(),
  playing = false,
  itineraryIndex = 0,
  intro = false,
  introPlayed = false,
  playback = 0;
const asset = (id) => `/api/studio-tours/${tour.public_id}/assets/${id}`;
function notice(text) {
  $("#notice").textContent = text;
  $("#notice").hidden = !text;
}
function pause() {
  playback++;
  playing = false;
  narration.pause();
  music.pause();
  $("#play").textContent = "Resume narration";
}
function select(checkpoint, continueItinerary = false) {
  playback++;
  narration.pause();
  narration.currentTime = 0;
  room = tour.rooms.find((r) => r.checkpoint_id === checkpoint);
  if (!room) return;
  intro = false;
  if (!continueItinerary)
    itineraryIndex = (tour.itinerary || []).indexOf(checkpoint);
  $("#room").value = checkpoint;
  $("#room-label").textContent = room.label;
  $("#room-description").textContent = room.summary;
  const script = tour.narration.segments.find(
    (s) => s.checkpoint_id === checkpoint,
  );
  $("#subtitle").textContent = script?.text || "No introduction available.";
  const audio = tour.narration.audio.find(
    (s) => s.checkpoint_id === checkpoint,
  );
  narration.src = audio ? asset(audio.asset_id) : "";
  dispose();
  $('#show-panorama').setAttribute('aria-pressed','true');
  $('#show-model').setAttribute('aria-pressed','false');
  if (room.projection === "equirectangular") {
    dispose = panorama($("#preview"), asset(room.asset_id), room.yaw);
  } else {
    const image = new Image();
    image.src = asset(room.asset_id);
    image.alt = room.label;
    $("#preview").replaceChildren(image);
    dispose = () => {};
  }
  $("#play").disabled = !audio;
  $("#connections").replaceChildren(
    ...(tour.navigation || [])
      .filter((link) => link.source === checkpoint)
      .map((link) => {
        const button = document.createElement("button");
        button.textContent = "→ " + link.label;
        button.onclick = () => {
          introPlayed = true;
          select(link.target);
        };
        return button;
      }),
  );
  if (playing) play();
}
async function play() {
  const token = ++playback;
  playing = true;
  try {
    if (!introPlayed && !intro && itineraryIndex === 0) {
      const audio = tour.narration.audio.find(
        (a) => a.checkpoint_id === "introduction",
      );
      if (audio) {
        intro = true;
        narration.src = asset(audio.asset_id);
        $("#subtitle").textContent = tour.narration.introduction;
      }
    }
    music.loop = true;
    music.volume = Number($("#music-volume").value) * 0.3;
    narration.volume = Number($("#voice-volume").value);
    await music.play();
    if (token !== playback || !playing) return;
    await narration.play();
    if (token !== playback || !playing) return;
    $("#play").textContent = "Playing narration";
  } catch {
    if (token !== playback) return;
    pause();
    notice(
      "Could not play audio. You can still read the introduction and explore the space.",
    );
  }
}
$("#play").onclick = play;
$('#show-panorama').onclick = () => { if(room) { pause(); select(room.checkpoint_id); } };
$('#show-model').onclick = () => {
  if(!tour) return;
  pause(); dispose();
  $('#show-panorama').setAttribute('aria-pressed','false');
  $('#show-model').setAttribute('aria-pressed','true');
  dispose=houseModel($('#preview'),asset(tour.model.asset_id),tour.rooms,checkpoint=>select(checkpoint));
};
$("#pause").onclick = pause;
$("#room").onchange = (e) => {
  introPlayed = true;
  select(e.target.value);
};
$("#music-volume").oninput = () =>
  (music.volume =
    Number($("#music-volume").value) * (narration.paused ? 1 : 0.3));
$("#voice-volume").oninput = () =>
  (narration.volume = Number($("#voice-volume").value));
narration.onended = () => {
  music.volume = Number($("#music-volume").value);
  if (intro) {
    introPlayed = true;
    if (playing) select(room.checkpoint_id, true);
    return;
  }
  const order =
      tour.itinerary || tour.narration.segments.map((s) => s.checkpoint_id),
    next = order[++itineraryIndex];
  if (playing && next) select(next, true);
  else pause();
};
narration.onerror = () => {
  if (narration.getAttribute("src")) {
    pause();
    notice("Could not load narration. Use captions or try again.");
  }
};
music.onerror = () => {
  pause();
  notice("Could not load background music. You can still explore the images.");
};
$("#question-form").onsubmit = async (e) => {
  e.preventDefault();
  pause();
  const question = $("#question").value.trim();
  if (!question) return;
  $("#ask").disabled = true;
  const p = document.createElement("p");
  p.textContent = question;
  $("#chat").append(p);
  try {
    const response = await fetch(
      `/api/studio-tours/${tour.public_id}/questions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          checkpoint_id: room.checkpoint_id,
          request_id: crypto.randomUUID(),
        }),
      },
    );
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.detail || "Could not connect to the assistant.");
    const reply = document.createElement("p");
    reply.className = "muted";
    reply.textContent = data.text;
    $("#chat").append(reply);
    if (data.navigate_to) select(data.navigate_to);
    $("#question").value = "";
  } catch (error) {
    notice(error.message);
  } finally {
    $("#ask").disabled = false;
  }
};
window.addEventListener("pagehide", () => {
  pause();
  dispose();
});
try {
  if (!/^[a-f0-9]{32}$/.test(id || ""))
    throw new Error("Invalid tour link.");
  const response = await fetch("/api/studio-tours/" + id);
  if (!response.ok)
    throw new Error("This tour is unpublished or does not exist.");
  tour = await response.json();
  $("#ask").disabled = false;
  $("#title").textContent = tour.name;
  for (const r of tour.rooms) {
    const option = document.createElement("option");
    option.value = r.checkpoint_id;
    option.textContent = `${r.label} · ${r.checkpoint_id}`;
    $("#room").append(option);
  }
  music.src = asset(tour.music.id);
  $("#music-credit").textContent = "Background music: " + tour.music.credit;
  $("#model-link").href = asset(tour.model.asset_id);
  $("#model-link").setAttribute("download", "house.glb");
  select(tour.rooms[0].checkpoint_id);
} catch (error) {
  notice(error.message);
  $("#title").textContent = "Could not open the tour";
  $("#ask").disabled = true;
}
