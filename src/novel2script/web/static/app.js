const sampleText = `Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.`;

const state = {
  output: "",
  format: "yaml"
};

const elements = {
  title: document.querySelector("#titleInput"),
  format: document.querySelector("#formatSelect"),
  provider: document.querySelector("#providerSelect"),
  model: document.querySelector("#modelInput"),
  validate: document.querySelector("#validateInput"),
  manuscript: document.querySelector("#manuscriptInput"),
  output: document.querySelector("#outputBox"),
  convert: document.querySelector("#convertButton"),
  sample: document.querySelector("#sampleButton"),
  file: document.querySelector("#fileInput"),
  fileButton: document.querySelector("#fileButton"),
  copy: document.querySelector("#copyButton"),
  download: document.querySelector("#downloadButton"),
  serverStatus: document.querySelector("#serverStatus"),
  chapterCount: document.querySelector("#chapterCount"),
  sceneCount: document.querySelector("#sceneCount"),
  characterCount: document.querySelector("#characterCount"),
  coverageScore: document.querySelector("#coverageScore"),
  verdict: document.querySelector("#verdict"),
  logline: document.querySelector("#loglineText"),
  scenesList: document.querySelector("#scenesList")
};

elements.manuscript.value = sampleText;
elements.output.textContent = "转换结果会显示在这里。";
setOutputActions(false);

async function checkServer() {
  try {
    const response = await fetch("/api/health");
    elements.serverStatus.textContent = response.ok ? "Ready" : "Offline";
  } catch {
    elements.serverStatus.textContent = "Offline";
  }
}

async function convertManuscript() {
  setWorking(true);
  elements.output.classList.remove("is-error");
  elements.output.textContent = "Converting...";

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: elements.manuscript.value,
        title: elements.title.value,
        format: elements.format.value,
        provider: elements.provider.value,
        model: elements.model.value,
        validate: elements.validate.checked
      })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Conversion failed.");
    }

    state.output = payload.output;
    state.format = payload.format;
    elements.output.textContent = payload.output;
    renderSummary(payload.summary);
    setOutputActions(true);
  } catch (error) {
    state.output = "";
    elements.output.classList.add("is-error");
    elements.output.textContent = error instanceof Error ? error.message : String(error);
    setOutputActions(false);
  } finally {
    setWorking(false);
  }
}

function renderSummary(summary) {
  elements.chapterCount.textContent = summary.chapter_count ?? 0;
  elements.sceneCount.textContent = summary.scene_count ?? 0;
  elements.characterCount.textContent = summary.character_count ?? 0;
  elements.coverageScore.textContent = summary.coverage_score ?? 0;
  elements.verdict.textContent = summary.verdict || "draft";
  elements.logline.textContent = summary.logline || "";

  elements.scenesList.replaceChildren(
    ...(summary.scenes || []).map((scene) => {
      const item = document.createElement("li");
      item.textContent = `${scene.id} · ${scene.title} · ${scene.location}`;
      return item;
    })
  );
}

async function loadFile() {
  const [file] = elements.file.files;
  if (!file) {
    return;
  }
  elements.manuscript.value = await file.text();
  if (!elements.title.value) {
    elements.title.value = file.name.replace(/\.[^.]+$/, "");
  }
}

async function copyOutput() {
  if (!state.output) {
    return;
  }
  await navigator.clipboard.writeText(state.output);
}

function downloadOutput() {
  if (!state.output) {
    return;
  }
  const extension = state.format === "fountain" ? "fountain" : "yaml";
  const blob = new Blob([state.output], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `novel2script-draft.${extension}`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function setWorking(isWorking) {
  elements.convert.disabled = isWorking;
  elements.convert.textContent = isWorking ? "转换中" : "转换";
  elements.fileButton.disabled = isWorking;
  elements.sample.disabled = isWorking;
}

function setOutputActions(isEnabled) {
  elements.copy.disabled = !isEnabled;
  elements.download.disabled = !isEnabled;
}

elements.sample.addEventListener("click", () => {
  elements.manuscript.value = sampleText;
});
elements.fileButton.addEventListener("click", () => {
  elements.file.click();
});
elements.file.addEventListener("change", loadFile);
elements.convert.addEventListener("click", convertManuscript);
elements.copy.addEventListener("click", copyOutput);
elements.download.addEventListener("click", downloadOutput);

checkServer();
