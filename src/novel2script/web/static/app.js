const sampleText = `Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.`;

const maxRequestBytes = 2000000;
const defaultModel = "gpt-4.1-mini";
const localDraftStorageKey = "novel2script:web:local-draft:v1";
const localDraftVersion = 1;
const textEncoder = new TextEncoder();
const crc32Table = buildCrc32Table();

const state = {
  output: "",
  exports: null,
  exportManifest: null,
  selectedOutput: "yaml",
  isWorking: false,
  copyLabelTimer: 0,
  downloadLabelTimer: 0,
  bundleLabelTimer: 0,
  draftSaveTimer: 0,
  previewLabelTimer: 0,
  previewRequestId: 0,
  previewInput: "",
  isPreviewPending: false,
  isPreviewReady: false,
  previewWarningCount: 0,
  remoteConfirmationKey: "",
  remoteConfirmationResolve: null,
  remoteConfirmationInvalidated: false,
  openAiConfirmedFor: "",
  lastConvertedInput: "",
  lastTitle: "",
  lastValidate: true,
  lastProvider: "local",
  lastModel: "",
  lastProviderStatus: null,
  lastSummary: null,
  lastDurationMs: 0
};

const scoreLabels = {
  premise: "前提",
  structure: "结构",
  character: "人物",
  dialogue: "对白",
  visuality: "可拍摄性",
  adaptation_fidelity: "改编保真"
};

const priorityLabels = {
  high: "高",
  medium: "中",
  low: "低"
};

const elements = {
  title: document.querySelector("#titleInput"),
  format: document.querySelector("#formatSelect"),
  provider: document.querySelector("#providerSelect"),
  model: document.querySelector("#modelInput"),
  validate: document.querySelector("#validateInput"),
  manuscript: document.querySelector("#manuscriptInput"),
  chapterPreviewState: document.querySelector("#chapterPreviewState"),
  chapterPreviewList: document.querySelector("#chapterPreviewList"),
  output: document.querySelector("#outputBox"),
  convert: document.querySelector("#convertButton"),
  sample: document.querySelector("#sampleButton"),
  clear: document.querySelector("#clearButton"),
  file: document.querySelector("#fileInput"),
  fileButton: document.querySelector("#fileButton"),
  copy: document.querySelector("#copyButton"),
  download: document.querySelector("#downloadButton"),
  bundle: document.querySelector("#bundleButton"),
  remoteConfirmPanel: document.querySelector("#remoteConfirmPanel"),
  remoteConfirmModel: document.querySelector("#remoteConfirmModel"),
  remoteConfirmTitle: document.querySelector("#remoteConfirmTitle"),
  remoteConfirmSize: document.querySelector("#remoteConfirmSize"),
  remoteConfirmCancel: document.querySelector("#remoteConfirmCancel"),
  remoteConfirmProceed: document.querySelector("#remoteConfirmProceed"),
  outputTabs: Array.from(document.querySelectorAll("[data-output-format]")),
  workflowSteps: Object.fromEntries(
    Array.from(document.querySelectorAll("[data-workflow-step]")).map((step) => [
      step.dataset.workflowStep,
      step
    ])
  ),
  inputStepMeta: document.querySelector("#inputStepMeta"),
  previewStepMeta: document.querySelector("#previewStepMeta"),
  convertStepMeta: document.querySelector("#convertStepMeta"),
  exportStepMeta: document.querySelector("#exportStepMeta"),
  draftStatus: document.querySelector("#draftStatus"),
  serverStatus: document.querySelector("#serverStatus"),
  inputSize: document.querySelector("#inputSize"),
  inputHint: document.querySelector("#inputHint"),
  providerMode: document.querySelector("#providerMode"),
  privacyHint: document.querySelector("#privacyHint"),
  conversionState: document.querySelector("#conversionState"),
  conversionMeta: document.querySelector("#conversionMeta"),
  exportState: document.querySelector("#exportState"),
  exportMeta: document.querySelector("#exportMeta"),
  exportBundleMeta: document.querySelector("#exportBundleMeta"),
  exportManifestList: document.querySelector("#exportManifestList"),
  coverageRatio: document.querySelector("#coverageRatio"),
  chapterCount: document.querySelector("#chapterCount"),
  sceneCount: document.querySelector("#sceneCount"),
  blockCount: document.querySelector("#blockCount"),
  dialogueCount: document.querySelector("#dialogueCount"),
  characterCount: document.querySelector("#characterCount"),
  coverageScore: document.querySelector("#coverageScore"),
  verdict: document.querySelector("#verdict"),
  logline: document.querySelector("#loglineText"),
  revisionFocusArea: document.querySelector("#revisionFocusArea"),
  revisionFocusPriority: document.querySelector("#revisionFocusPriority"),
  revisionFocusScore: document.querySelector("#revisionFocusScore"),
  revisionFocusNote: document.querySelector("#revisionFocusNote"),
  revisionFocusRationale: document.querySelector("#revisionFocusRationale"),
  scoresList: document.querySelector("#scoresList"),
  actionItems: document.querySelector("#actionItems"),
  beatsList: document.querySelector("#beatsList"),
  sceneMapList: document.querySelector("#sceneMapList"),
  scenesList: document.querySelector("#scenesList"),
  storyCharactersList: document.querySelector("#storyCharactersList"),
  storyLocationsList: document.querySelector("#storyLocationsList"),
  storyPropsList: document.querySelector("#storyPropsList"),
  storyQuestionsList: document.querySelector("#storyQuestionsList"),
  strengthsList: document.querySelector("#strengthsList"),
  weaknessesList: document.querySelector("#weaknessesList"),
  qualityList: document.querySelector("#qualityList")
};

initializeWorkbench();

async function checkServer() {
  try {
    const response = await fetch("/api/health");
    elements.serverStatus.textContent = response.ok ? "Ready" : "Offline";
  } catch {
    elements.serverStatus.textContent = "Offline";
  }
}

async function readJsonResponse(response, fallbackMessage) {
  try {
    return await response.json();
  } catch {
    throw new Error(fallbackMessage);
  }
}

async function convertManuscript() {
  if (isCurrentRequestTooLarge()) {
    showRequestSizeError();
    syncConvertAvailability();
    return;
  }

  if (!state.isPreviewReady) {
    showPreflightBlockedConversion();
    return;
  }

  if (!(await confirmRemoteProvider())) {
    return;
  }

  const startedAt = performance.now();
  const payload = conversionPayload();
  const requestModel = normalizedModel();
  setWorking(true);
  setConversionStatus("转换中", "正在生成剧本草稿。", "active");
  elements.output.classList.remove("is-error");
  elements.output.textContent = "转换中...";

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await readJsonResponse(response, "服务返回了无法解析的转换响应。");
    if (!response.ok) {
      throw new Error(result.error || "Conversion failed.");
    }

    state.exports = normalizeExports(result);
    state.exportManifest = normalizeExportManifest(result.export_manifest, state.exports);
    state.selectedOutput = outputSelectionForFormat(result.format);
    state.output = outputForSelection(state.selectedOutput);
    state.lastConvertedInput = payload.text;
    state.lastTitle = payload.title;
    state.lastValidate = payload.validate;
    state.lastProvider = payload.provider;
    state.lastModel = requestModel;
    state.lastProviderStatus = result.provider_status || null;
    state.lastSummary = result.summary;
    state.lastDurationMs = Math.max(0, Math.round(performance.now() - startedAt));
    elements.output.textContent = state.output;
    renderOutputTabs();
    renderExportManifest();
    renderSummary(result.summary);
    renderProviderRunStatus(state.lastProviderStatus);
    updateExportStatus();
    setConversionStatus(
      "已完成",
      `${formatDuration(state.lastDurationMs)} · ${providerStatusSummary(
        state.lastProviderStatus
      )} · ${conversionSummary(result.summary)}`,
      "ready"
    );
    updateConversionFreshness();
  } catch (error) {
    state.output = "";
    state.exports = null;
    state.exportManifest = null;
    renderOutputTabs();
    renderExportManifest();
    state.lastProviderStatus = null;
    elements.output.classList.add("is-error");
    elements.output.textContent = error instanceof Error ? error.message : String(error);
    renderSummary(null);
    renderProviderSelectionStatus();
    updateExportStatus();
    setConversionStatus(
      "转换失败",
      error instanceof Error ? error.message : String(error),
      "error"
    );
  } finally {
    setWorking(false);
  }
}

function renderSummary(summary) {
  const metrics = summary?.adaptation_metrics || {};
  const chapterCoverage = summary?.chapter_coverage || {};
  const coverageRatio = Number(chapterCoverage.coverage_ratio || 0);

  elements.chapterCount.textContent = summary?.chapter_count ?? 0;
  elements.sceneCount.textContent = summary?.scene_count ?? 0;
  elements.blockCount.textContent = metrics.block_count ?? 0;
  elements.dialogueCount.textContent = metrics.dialogue_blocks ?? 0;
  elements.characterCount.textContent = summary?.character_count ?? 0;
  elements.coverageScore.textContent = summary?.coverage_score ?? 0;
  elements.coverageRatio.textContent = `${Math.round(coverageRatio * 100)}%`;
  elements.verdict.textContent = summary?.verdict || "draft";
  elements.logline.textContent = summary?.logline || "完成转换后，这里会显示一句话故事、coverage 分数和下一轮修订入口。";

  renderRevisionFocus(summary?.revision_focus || null);
  renderScores(summary?.scores || []);
  renderActionItems(summary?.action_items || summary?.revision_checklist || []);
  renderBeats(summary?.structure_beats || []);
  renderSceneMap(summary?.scene_map || []);
  renderScenes(summary?.scenes || []);
  renderStoryBible(summary?.story_bible || {});
  renderTextList(elements.strengthsList, summary?.strengths || []);
  renderTextList(
    elements.weaknessesList,
    [...(summary?.weaknesses || []), ...(summary?.structure_diagnostics || [])]
  );
  renderTextList(elements.qualityList, summary?.quality_flags || summary?.revision_checklist || []);
}

function renderRevisionFocus(focus) {
  const hasFocus = Boolean(focus && (focus.area || focus.note || focus.rationale));
  const score =
    focus?.score !== undefined && focus?.score !== null && focus?.score !== ""
      ? focus.score
      : "--";

  elements.revisionFocusArea.textContent = hasFocus
    ? scoreLabels[focus.area] || focus.area || "未命名"
    : "待生成";
  elements.revisionFocusPriority.textContent = hasFocus
    ? priorityLabels[focus.priority] || focus.priority || "中"
    : "中";
  elements.revisionFocusScore.textContent = hasFocus ? score : "--";
  elements.revisionFocusNote.textContent = hasFocus
    ? focus.note || "检查优先修订动作，并把下一轮修订目标写成可执行改稿任务。"
    : "转换后会根据 coverage 和优先修订动作提示下一轮最该处理的问题。";
  elements.revisionFocusRationale.textContent = hasFocus
    ? focus.rationale || "该重点来自当前最低分项或优先修订动作。"
    : "分数理由会显示在这里，便于定位对应的 coverage 维度。";
}

function renderScores(scores) {
  elements.scoresList.replaceChildren(
    ...withEmpty(scores, "转换后显示 premise、structure、character 等分项评分。").map((score) => {
      if (typeof score === "string") {
        return emptyItem(score);
      }

      const item = document.createElement("div");
      item.className = "score-item";

      const head = document.createElement("div");
      head.className = "score-head";

      const label = document.createElement("span");
      label.textContent = scoreLabels[score.area] || score.area || "未命名";

      const value = document.createElement("strong");
      value.textContent = score.score ?? 0;

      const bar = document.createElement("span");
      bar.className = "score-bar";
      bar.style.setProperty("--score", `${Math.max(0, Math.min(Number(score.score || 0), 100))}%`);

      const note = document.createElement("p");
      note.textContent = score.rationale || "";

      head.append(label, value);
      item.append(head, bar, note);
      return item;
    })
  );
}

function renderActionItems(items) {
  elements.actionItems.replaceChildren(
    ...withEmpty(items, "转换后显示按优先级排序的修订动作。").map((item) => {
      const listItem = document.createElement("li");
      if (typeof item === "string") {
        listItem.className = "empty";
        listItem.textContent = item;
        return listItem;
      }

      const badge = document.createElement("span");
      badge.className = `priority priority-${item.priority || "medium"}`;
      badge.textContent = priorityLabels[item.priority] || item.priority || "中";

      const content = document.createElement("p");
      content.textContent = item.note || "";

      listItem.append(badge, content);
      return listItem;
    })
  );
}

function renderBeats(beats) {
  elements.beatsList.replaceChildren(
    ...withEmpty(beats, "转换后显示开场、诱发事件、中点、高潮和结局映射。").map((beat) => {
      const item = document.createElement("li");
      if (typeof beat === "string") {
        item.className = "empty";
        item.textContent = beat;
        return item;
      }

      const title = document.createElement("strong");
      title.textContent = `${beat.label || beat.id} · ${beat.scene_id || "未映射"}`;

      const summary = document.createElement("p");
      summary.textContent = beat.revision_hint || beat.summary || "";

      item.append(title, summary);
      return item;
    })
  );
}

function renderSceneMap(sceneMap) {
  elements.sceneMapList.replaceChildren(
    ...withEmpty(sceneMap, "转换后显示源章节到生成场景的逐章映射。").map((mapping) => {
      const item = document.createElement("li");
      if (typeof mapping === "string") {
        item.className = "empty";
        item.textContent = mapping;
        return item;
      }

      const chapter = document.createElement("span");
      chapter.textContent = `第 ${mapping.chapter_index || "?"} 章`;

      const title = document.createElement("strong");
      title.textContent = mapping.chapter_title || "未命名章节";

      const scene = document.createElement("p");
      scene.textContent = `${mapping.scene_id || "未映射"} · ${
        mapping.scene_title || "未命名场景"
      }`;

      item.append(chapter, title, scene);
      return item;
    })
  );
}

function renderScenes(scenes) {
  elements.scenesList.replaceChildren(
    ...withEmpty(scenes, "转换后显示前 12 场的章节来源、地点和人物。").map((scene) => {
      const item = document.createElement("li");
      if (typeof scene === "string") {
        item.className = "empty";
        item.textContent = scene;
        return item;
      }

      const title = document.createElement("strong");
      title.textContent = `${scene.id} · ${scene.title || "未命名场景"}`;

      const meta = document.createElement("span");
      const characters = (scene.characters || []).join("、") || "人物待补充";
      meta.textContent = `第 ${scene.source_chapter || "?"} 章 · ${scene.location || "待定场景"} · ${characters}`;

      const summary = document.createElement("p");
      summary.textContent = scene.summary || "";

      const counts = scene.block_counts || {};
      const blockMeta = document.createElement("div");
      blockMeta.className = "scene-block-meta";
      blockMeta.textContent = `块 ${counts.total ?? 0} · 动作 ${counts.action ?? 0} · 对白 ${
        counts.dialogue ?? 0
      }`;

      const blockList = document.createElement("ul");
      blockList.className = "scene-block-preview";
      const previewBlocks = Array.isArray(scene.blocks_preview) ? scene.blocks_preview : [];
      for (const block of previewBlocks) {
        const blockItem = document.createElement("li");
        const badge = document.createElement("span");
        badge.className = `block-type ${blockTypeClass(block.type)}`;
        badge.textContent = blockTypeLabel(block.type);

        const text = document.createElement("p");
        const speaker = block.character ? `${block.character}：` : "";
        text.textContent = `${speaker}${block.text || ""}`;

        blockItem.append(badge, text);
        blockList.append(blockItem);
      }

      item.append(title, meta, summary, blockMeta);
      if (previewBlocks.length) {
        item.append(blockList);
      }
      return item;
    })
  );
}

function blockTypeLabel(type) {
  const labels = {
    action: "动作",
    dialogue: "对白",
    voice_over: "旁白",
    transition: "转场"
  };
  return labels[type] || "块";
}

function blockTypeClass(type) {
  const classes = {
    action: "block-type-action",
    dialogue: "block-type-dialogue",
    voice_over: "block-type-voice_over",
    transition: "block-type-transition"
  };
  return classes[type] || "block-type-unknown";
}

function renderStoryBible(storyBible) {
  renderStoryCharacters(storyBible.characters || []);
  renderStoryLocations(storyBible.locations || []);
  renderStoryProps(storyBible.props || []);
  renderTextList(elements.storyQuestionsList, storyBible.open_questions || []);
}

function renderStoryCharacters(characters) {
  elements.storyCharactersList.replaceChildren(
    ...withEmpty(characters, "转换后显示主要人物的首次出场和连续性复核提示。").map((character) => {
      const item = document.createElement("li");
      if (typeof character === "string") {
        item.className = "empty";
        item.textContent = character;
        return item;
      }

      const title = document.createElement("strong");
      title.textContent = `${character.name || "未命名人物"} · ${character.role || "role"}`;

      const meta = document.createElement("span");
      meta.textContent = character.first_seen_scene
        ? `首次出场 ${character.first_seen_scene}`
        : "首次出场待补充";

      const note = document.createElement("p");
      note.textContent = character.continuity_note || "复核目标、关系和称呼是否一致。";

      item.append(title, meta, note);
      return item;
    })
  );
}

function renderStoryLocations(locations) {
  elements.storyLocationsList.replaceChildren(
    ...withEmpty(locations, "转换后显示地点资产和关联场景。").map((location) => {
      const item = document.createElement("li");
      if (typeof location === "string") {
        item.className = "empty";
        item.textContent = location;
        return item;
      }

      const title = document.createElement("strong");
      title.textContent = location.name || "待定地点";

      const meta = document.createElement("span");
      const sceneIds = Array.isArray(location.scene_ids) ? location.scene_ids.join("、") : "";
      meta.textContent = sceneIds ? `关联场景 ${sceneIds}` : "关联场景待补充";

      const note = document.createElement("p");
      note.textContent = location.note || "补充空间特征和可拍摄视觉元素。";

      item.append(title, meta, note);
      return item;
    })
  );
}

function renderStoryProps(props) {
  elements.storyPropsList.replaceChildren(
    ...withEmpty(props, "转换后显示道具、线索和来源章节。").map((prop) => {
      const item = document.createElement("li");
      if (typeof prop === "string") {
        item.className = "empty";
        item.textContent = prop;
        return item;
      }

      const title = document.createElement("strong");
      title.textContent = prop.name || "未命名线索";

      const meta = document.createElement("span");
      const chapters = Array.isArray(prop.source_chapters)
        ? prop.source_chapters.join("、")
        : "";
      meta.textContent = chapters ? `来源章节 ${chapters}` : "来源章节待补充";

      const note = document.createElement("p");
      note.textContent = prop.dramatic_function || "标记出现、推进和回收方式。";

      item.append(title, meta, note);
      return item;
    })
  );
}

function renderTextList(target, items) {
  target.replaceChildren(
    ...withEmpty(items, "转换后显示诊断内容。").map((text) => {
      const item = document.createElement("li");
      item.className = typeof text === "string" && text.startsWith("转换后") ? "empty" : "";
      item.textContent = text;
      return item;
    })
  );
}

function renderChapterPreview(status, chapters, options = {}) {
  const chapterItems = Array.isArray(chapters) ? chapters : [];
  const limit = options.limit ?? 8;
  elements.chapterPreviewState.textContent = status;
  setStatusTone(elements.chapterPreviewList.parentElement, options.tone || "neutral");

  if (!chapterItems.length) {
    const item = document.createElement("li");
    item.className = "empty";
    item.textContent = options.emptyMessage || "尚无章节";
    elements.chapterPreviewList.replaceChildren(item);
    return;
  }

  const rendered = chapterItems.slice(0, limit).map((chapter, index) => {
    const item = document.createElement("li");

    const marker = document.createElement("span");
    const chapterIndex = chapter.index ?? index + 1;
    marker.textContent = `第 ${chapterIndex} 章`;

    item.className = `chapter-preview-item is-${chapter.status || "ready"}`;

    const content = document.createElement("div");
    content.className = "chapter-preview-content";

    const title = document.createElement("strong");
    title.textContent = chapter.title || `章节 ${chapterIndex}`;

    const meta = document.createElement("small");
    const chapterCharacterCount = Number(chapter.character_count || 0);
    const countText = chapterCharacterCount
      ? `${formatNumber(chapterCharacterCount)} 字`
      : "正文待补充";
    const statusText = chapter.status === "short" ? "素材偏短" : "素材就绪";
    meta.textContent = `${countText} · ${statusText}`;

    content.append(title, meta);
    if (chapter.warning) {
      const warning = document.createElement("em");
      warning.textContent = chapter.warning;
      content.append(warning);
    }

    item.append(marker, content);
    return item;
  });

  if (chapterItems.length > limit) {
    const overflow = document.createElement("li");
    overflow.className = "empty";
    overflow.textContent = `还有 ${chapterItems.length - limit} 章未显示`;
    rendered.push(overflow);
  }

  elements.chapterPreviewList.replaceChildren(...rendered);
}

function updateInputStatus() {
  resetProviderRunStatus();
  const text = elements.manuscript.value;
  const characterCount = countCharacters(text);
  elements.inputSize.textContent = `${formatNumber(characterCount)} 字 / 预检中`;

  clearTimeout(state.previewLabelTimer);
  state.isPreviewPending = false;
  state.isPreviewReady = false;
  state.previewWarningCount = 0;
  syncConvertAvailability();
  updateExportStatus();

  if (isCurrentRequestTooLarge()) {
    state.previewInput = "";
    state.previewRequestId += 1;
    showRequestSizeError();
    updateConversionFreshness();
    return;
  }

  if (!characterCount) {
    state.previewInput = "";
    elements.inputHint.textContent = "至少 3 章后开始转换。";
    setStatusTone(elements.inputSize.parentElement, "neutral");
    elements.inputSize.textContent = "0 字 / 0 章";
    renderChapterPreview("等待输入", [], {
      emptyMessage: "尚无章节",
      tone: "neutral"
    });
    syncConvertAvailability();
    updateExportStatus();
    updateConversionFreshness();
    return;
  }

  elements.inputHint.textContent = "正在用后端章节解析器预检。";
  setStatusTone(elements.inputSize.parentElement, "active");
  renderChapterPreview("预检中", [], {
    emptyMessage: "正在解析章节",
    tone: "active"
  });
  state.isPreviewPending = true;
  schedulePreview(text);
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
}

function schedulePreview(text) {
  const requestId = ++state.previewRequestId;
  state.previewInput = text;
  state.isPreviewPending = true;
  state.isPreviewReady = false;
  state.previewWarningCount = 0;
  syncConvertAvailability();
  clearTimeout(state.previewLabelTimer);
  state.previewLabelTimer = window.setTimeout(() => {
    void runPreview(text, requestId);
  }, 260);
}

function isCurrentRequestTooLarge() {
  return currentRequestByteLength() > maxRequestBytes;
}

function currentRequestByteLength() {
  return Math.max(
    requestByteLength({ text: elements.manuscript.value }),
    requestByteLength(conversionPayload())
  );
}

function importedFileRequestByteLength(file) {
  const payload = {
    ...conversionPayload(),
    text: "",
    title: elements.title.value || file.name.replace(/\.[^.]+$/, "")
  };
  return requestByteLength(payload) + file.size;
}

function conversionPayload() {
  return {
    text: elements.manuscript.value,
    title: elements.title.value,
    format: elements.format.value,
    provider: elements.provider.value,
    model: normalizedModel(),
    validate: elements.validate.checked
  };
}

function selectedOutputLabel() {
  const labels = {
    yaml: "YAML",
    fountain: "Fountain",
    markdown: "Revision brief",
    draftJson: "Draft JSON",
    summaryJson: "Summary JSON"
  };
  return labels[state.selectedOutput] || "YAML";
}

function outputForSelection(selection) {
  if (!state.exports) {
    return "";
  }
  return state.exports[selection] || "";
}

function selectOutput(selection) {
  if (!state.exports || !Object.prototype.hasOwnProperty.call(state.exports, selection)) {
    return;
  }
  state.selectedOutput = selection;
  state.output = outputForSelection(selection);
  elements.output.classList.remove("is-error");
  elements.output.textContent = state.output;
  renderOutputTabs();
  renderExportManifest();
  updateExportStatus();
}

function renderOutputTabs() {
  for (const button of elements.outputTabs) {
    const isSelected = button.dataset.outputFormat === state.selectedOutput;
    button.disabled = !state.exports;
    button.classList.toggle("is-selected", Boolean(state.exports) && isSelected);
    button.setAttribute("aria-selected", String(Boolean(state.exports) && isSelected));
  }
}

function renderExportManifest() {
  if (!state.exportManifest || !state.exports) {
    elements.exportBundleMeta.textContent = "等待转换";
    elements.exportManifestList.replaceChildren(emptyExportManifestItem("转换后显示可下载文件。"));
    return;
  }

  const files = state.exportManifest.files || [];
  const bundle = state.exportManifest.bundle || {};
  elements.exportBundleMeta.textContent = `${bundle.file_count ?? files.length} 个文件 · ${formatFileSize(
    Number(bundle.content_bytes || 0)
  )}`;
  elements.exportManifestList.replaceChildren(
    ...files.map((file) => {
      const item = document.createElement("li");
      item.className = file.key === state.selectedOutput ? "is-selected" : "";

      const title = document.createElement("strong");
      title.textContent = file.label || exportLabelForKey(file.key);

      const meta = document.createElement("span");
      meta.textContent = `${file.extension || outputExtension(file.key)} · ${formatFileSize(
        Number(file.byte_size || 0)
      )}`;

      item.append(title, meta);
      return item;
    })
  );
}

function emptyExportManifestItem(text) {
  const item = document.createElement("li");
  item.className = "empty";
  item.textContent = text;
  return item;
}

function requestByteLength(payload) {
  return textEncoder.encode(JSON.stringify(payload)).length;
}

function outputSelectionForFormat(format) {
  return format === "fountain" || format === "markdown" ? format : "yaml";
}

function initializeWorkbench() {
  const restored = restoreLocalDraft();
  if (!restored) {
    elements.manuscript.value = sampleText;
    state.selectedOutput = outputSelectionForFormat(elements.format.value);
    if (localDraftStorage() && elements.draftStatus.textContent === "示例草稿") {
      setDraftStatus("示例草稿", "neutral");
    }
  }

  elements.output.textContent = "转换结果会显示在这里。";
  setOutputActions(false);
  renderSummary(null);
  renderOutputTabs();
  renderExportManifest();
  updateInputStatus();
  updateProviderStatus();
  updateExportStatus();

  if (restored) {
    const hasText = Boolean(elements.manuscript.value.trim());
    setConversionStatus(
      hasText ? "待转换" : "待输入",
      hasText ? "已恢复浏览器本地草稿，等待章节预检。" : "本地草稿为空，等待手稿输入。",
      hasText ? "active" : "neutral"
    );
  }
}

function restoreLocalDraft() {
  const storage = localDraftStorage();
  if (!storage) {
    setDraftStatus("保存不可用", "warn");
    return false;
  }

  let draft;
  try {
    const raw = storage.getItem(localDraftStorageKey);
    if (!raw) {
      return false;
    }
    draft = JSON.parse(raw);
  } catch {
    removeLocalDraft(storage);
    setDraftStatus("草稿已重置", "warn");
    return false;
  }

  if (!isLocalDraft(draft)) {
    removeLocalDraft(storage);
    setDraftStatus("草稿已重置", "warn");
    return false;
  }

  elements.manuscript.value = typeof draft.text === "string" ? draft.text : "";
  elements.title.value = typeof draft.title === "string" ? draft.title : "";
  elements.format.value =
    draft.format === "fountain" || draft.format === "markdown" ? draft.format : "yaml";
  elements.provider.value = draft.provider === "openai" ? "openai" : "local";
  elements.model.value = typeof draft.model === "string" ? draft.model : defaultModel;
  elements.validate.checked = typeof draft.validate === "boolean" ? draft.validate : true;
  state.selectedOutput = outputSelectionForFormat(elements.format.value);
  setDraftStatus("已恢复草稿", "ready");
  return true;
}

function isLocalDraft(value) {
  return (
    typeof value === "object" &&
    value !== null &&
    value.version === localDraftVersion &&
    (typeof value.text === "string" || value.text === undefined)
  );
}

function scheduleLocalDraftSave() {
  clearTimeout(state.draftSaveTimer);
  setDraftStatus("保存中", "active");
  state.draftSaveTimer = window.setTimeout(saveLocalDraft, 240);
}

function saveLocalDraft() {
  const storage = localDraftStorage();
  if (!storage) {
    setDraftStatus("保存不可用", "warn");
    return false;
  }

  const draft = {
    version: localDraftVersion,
    savedAt: new Date().toISOString(),
    text: elements.manuscript.value,
    title: elements.title.value,
    format: elements.format.value,
    provider: elements.provider.value,
    model: elements.model.value,
    validate: elements.validate.checked
  };

  try {
    storage.setItem(localDraftStorageKey, JSON.stringify(draft));
  } catch {
    setDraftStatus("保存失败", "warn");
    return false;
  }

  setDraftStatus("草稿已保存", "ready");
  return true;
}

function localDraftStorage() {
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
}

function removeLocalDraft(storage) {
  try {
    storage.removeItem(localDraftStorageKey);
  } catch {
    return;
  }
}

function setDraftStatus(label, tone) {
  if (!elements.draftStatus) {
    return;
  }
  elements.draftStatus.textContent = label;
  setStatusTone(elements.draftStatus, tone);
}

function showRequestSizeError() {
  state.isPreviewPending = false;
  state.isPreviewReady = false;
  const requestSize = currentRequestByteLength();
  elements.inputSize.textContent = `${formatFileSize(requestSize)} / 上限 ${formatFileSize(
    maxRequestBytes
  )}`;
  elements.inputHint.textContent = "手稿过大，请拆分后再预检或转换。";
  setStatusTone(elements.inputSize.parentElement, "error");
  renderChapterPreview("无法预检", [], {
    emptyMessage: "手稿超过 Web 请求上限",
    tone: "error"
  });
  setConversionStatus("无法转换", "当前手稿超过 Web 请求上限。", "error");
  syncConvertAvailability();
  updateExportStatus();
}

function showFileImportSizeError(file) {
  state.isPreviewPending = false;
  state.isPreviewReady = false;
  const requestSize = importedFileRequestByteLength(file);
  elements.inputSize.textContent = `${formatFileSize(requestSize)} / 上限 ${formatFileSize(
    maxRequestBytes
  )}`;
  elements.inputHint.textContent = "文件过大，未导入。请拆分后再导入或粘贴较小片段。";
  setStatusTone(elements.inputSize.parentElement, "error");
  renderChapterPreview("无法导入", [], {
    emptyMessage: "所选文件超过 Web 请求上限",
    tone: "error"
  });
  setConversionStatus("无法导入", "所选文件会超过 Web 请求上限。", "error");
  syncConvertAvailability();
  updateExportStatus();
}

function showFileImportReadError(file) {
  state.isPreviewPending = false;
  state.isPreviewReady = false;
  elements.inputHint.textContent = "文件读取失败，当前手稿已保留。请重新选择或粘贴文本。";
  setStatusTone(elements.inputSize.parentElement, "warn");
  renderChapterPreview("读取失败", [], {
    emptyMessage: "当前章节预检未更新",
    tone: "warn"
  });
  setConversionStatus("导入失败", `${file.name} 无法读取。`, "warn");
  syncConvertAvailability();
  updateExportStatus();
}

function showPreflightBlockedConversion() {
  const detail = state.isPreviewPending
    ? "等待章节预检完成后再转换。"
    : "至少需要 3 章通过预检后才能转换。";
  setConversionStatus("无法转换", detail, "warn");
  syncConvertAvailability();
}

async function runPreview(text, requestId) {
  try {
    const response = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const preview = await readJsonResponse(response, "服务返回了无法解析的预检响应。");
    if (requestId !== state.previewRequestId || text !== elements.manuscript.value) {
      return;
    }
    if (!response.ok) {
      throw new Error(preview.error || "Preview failed.");
    }
    renderPreview(preview);
  } catch (error) {
    if (requestId !== state.previewRequestId || text !== elements.manuscript.value) {
      return;
    }
    const message = error instanceof Error ? error.message : String(error);
    state.isPreviewPending = false;
    state.isPreviewReady = false;
    state.previewWarningCount = 0;
    const characterCount = countCharacters(text);
    elements.inputSize.textContent = `${formatNumber(characterCount)} 字 / ? 章`;
    elements.inputHint.textContent = `预检失败：${message}`;
    setStatusTone(elements.inputSize.parentElement, "warn");
    renderChapterPreview("预检失败", [], {
      emptyMessage: message,
      tone: "warn"
    });
    setConversionStatus("预检失败", `${message} 请刷新页面或稍后重试。`, "warn");
    syncConvertAvailability();
  }
}

function renderPreview(preview) {
  const characterCount = Number(preview.character_count || 0);
  const chapterCount = Number(preview.chapter_count || 0);
  const warningCount = Number(preview.short_chapter_count || 0);
  const previewTone = preview.ready ? (warningCount ? "warn" : "ready") : "warn";
  state.isPreviewPending = false;
  state.isPreviewReady = Boolean(preview.ready);
  state.previewWarningCount = warningCount;
  elements.inputSize.textContent = `${formatNumber(characterCount)} 字 / ${chapterCount} 章`;
  elements.inputHint.textContent = preview.message || "转换时会再次校验。";
  renderChapterPreview(
    preview.ready && warningCount ? "可转换 / 需补素材" : preview.ready ? "已通过" : "未通过",
    preview.chapters || [],
    {
    emptyMessage: "未检测到章节",
    tone: previewTone
    }
  );

  if (preview.ready) {
    setStatusTone(elements.inputSize.parentElement, previewTone);
  } else if (characterCount) {
    setStatusTone(elements.inputSize.parentElement, "warn");
  } else {
    setStatusTone(elements.inputSize.parentElement, "neutral");
  }
  syncConvertAvailability();
}

function updateProviderStatus() {
  renderProviderSelectionStatus();
  updateConversionFreshness();
}

function renderProviderSelectionStatus() {
  const isOpenAI = elements.provider.value === "openai";
  elements.providerMode.textContent = isOpenAI ? "OpenAI" : "本地";
  elements.privacyHint.textContent = isOpenAI
    ? "转换前会按当前手稿、片名和模型确认远程发送。"
    : "仅在本机转换。";
  setStatusTone(elements.providerMode.parentElement, isOpenAI ? "warn" : "ready");
  if (!isOpenAI) {
    state.openAiConfirmedFor = "";
  }
}

function renderProviderRunStatus(status) {
  if (!status) {
    renderProviderSelectionStatus();
    return;
  }

  if (status.remote) {
    elements.providerMode.textContent = "OpenAI";
    elements.privacyHint.textContent = `已使用 ${status.model || "OpenAI"} 远程增强。`;
    setStatusTone(elements.providerMode.parentElement, "warn");
    return;
  }

  if (status.requested === "openai" && status.reason === "missing_api_key") {
    elements.providerMode.textContent = "本地回退";
    elements.privacyHint.textContent = "OPENAI_API_KEY 未设置，实际使用本地转换。";
    setStatusTone(elements.providerMode.parentElement, "warn");
    return;
  }

  elements.providerMode.textContent = "本地";
  elements.privacyHint.textContent = "已使用本地启发式转换。";
  setStatusTone(elements.providerMode.parentElement, "ready");
}

function resetProviderRunStatus() {
  if (!state.lastProviderStatus) {
    return;
  }
  renderProviderSelectionStatus();
}

async function confirmRemoteProvider() {
  if (elements.provider.value !== "openai") {
    return true;
  }

  const confirmationKey = remoteConfirmationKey();
  if (state.openAiConfirmedFor === confirmationKey) {
    return true;
  }

  const confirmed = await requestRemoteConfirmation(confirmationKey);
  if (!confirmed) {
    if (!state.remoteConfirmationInvalidated) {
      setConversionStatus("已取消", "未确认远程发送，转换没有开始。", "warn");
    }
    state.remoteConfirmationInvalidated = false;
    return false;
  }

  state.openAiConfirmedFor = confirmationKey;
  return true;
}

function requestRemoteConfirmation(confirmationKey) {
  dismissRemoteConfirmation({ quiet: true });
  state.remoteConfirmationKey = confirmationKey;
  state.remoteConfirmationInvalidated = false;
  const confirmation = new Promise((resolve) => {
    state.remoteConfirmationResolve = resolve;
  });
  updateRemoteConfirmationPanel();
  if (elements.remoteConfirmPanel) {
    elements.remoteConfirmPanel.classList.remove("is-hidden");
  }
  setConversionStatus(
    "等待确认",
    "请确认 OpenAI 远程发送后再开始转换；修改手稿、片名、模型或模式会使本次确认失效。",
    "warn"
  );
  syncConvertAvailability();
  elements.remoteConfirmProceed?.focus();
  return confirmation;
}

function updateRemoteConfirmationPanel() {
  if (elements.remoteConfirmModel) {
    elements.remoteConfirmModel.textContent = normalizedModel();
  }
  if (elements.remoteConfirmTitle) {
    elements.remoteConfirmTitle.textContent = elements.title.value.trim() || "未命名";
  }
  if (elements.remoteConfirmSize) {
    elements.remoteConfirmSize.textContent = `${formatNumber(
      countCharacters(elements.manuscript.value)
    )} 字`;
  }
}

function resolveRemoteConfirmation(confirmed) {
  if (!state.remoteConfirmationResolve) {
    return;
  }

  const pendingKey = state.remoteConfirmationKey;
  const resolve = state.remoteConfirmationResolve;
  state.remoteConfirmationResolve = null;
  state.remoteConfirmationKey = "";
  if (elements.remoteConfirmPanel) {
    elements.remoteConfirmPanel.classList.add("is-hidden");
  }
  syncConvertAvailability();

  if (!confirmed) {
    state.remoteConfirmationInvalidated = false;
    resolve(false);
    return;
  }

  if (elements.provider.value !== "openai" || remoteConfirmationKey() !== pendingKey) {
    state.remoteConfirmationInvalidated = true;
    setConversionStatus(
      "确认已失效",
      "手稿、片名、模型或模式已变化，请重新检查后再确认远程发送。",
      "warn"
    );
    resolve(false);
    return;
  }

  resolve(true);
}

function dismissRemoteConfirmation(options = {}) {
  if (!state.remoteConfirmationResolve) {
    return;
  }
  state.remoteConfirmationResolve(false);
  state.remoteConfirmationResolve = null;
  state.remoteConfirmationKey = "";
  state.remoteConfirmationInvalidated = true;
  if (elements.remoteConfirmPanel) {
    elements.remoteConfirmPanel.classList.add("is-hidden");
  }
  syncConvertAvailability();
  if (!options.quiet) {
    setConversionStatus(
      "确认已失效",
      "手稿、片名、模型或模式已变化，请重新检查后再确认远程发送。",
      "warn"
    );
  }
}

function remoteConfirmationKey() {
  const text = elements.manuscript.value;
  return JSON.stringify({
    provider: "openai",
    model: normalizedModel(),
    title: elements.title.value.trim(),
    textLength: text.length,
    textFingerprint: textFingerprint(text)
  });
}

function normalizedModel() {
  return elements.model.value.trim() || defaultModel;
}

function textFingerprint(text) {
  let hash = 2166136261;
  for (const character of text) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

function updateExportStatus() {
  const formatLabel = selectedOutputLabel();
  const validationLabel = elements.validate.checked ? "Schema 校验开启" : "Schema 校验关闭";

  if (state.output) {
    const staleReason = currentOutputStaleReason();
    if (staleReason) {
      elements.exportState.textContent = "需重新转换";
      elements.exportMeta.textContent = `${staleReason.exportDetail} 重新转换后再复制、下载或打包。`;
      setStatusTone(elements.exportState.parentElement, "warn");
      setOutputActions(false);
      updateWorkflowSteps();
      return;
    }

    elements.exportState.textContent = formatLabel;
    elements.exportMeta.textContent = `${validationLabel} · 可复制、下载或打包。`;
    setStatusTone(elements.exportState.parentElement, "ready");
    setOutputActions(true);
    updateWorkflowSteps();
    return;
  }

  elements.exportState.textContent = "未生成";
  elements.exportMeta.textContent = `${formatLabel} / ${validationLabel}。`;
  setStatusTone(elements.exportState.parentElement, "neutral");
  setOutputActions(false);
  updateWorkflowSteps();
}

function currentOutputStaleReason() {
  if (elements.manuscript.value !== state.lastConvertedInput) {
    return {
      conversionDetail: "手稿已变更，当前结果可能不是最新。",
      exportDetail: "手稿已变更，当前导出可能不是最新。"
    };
  }

  if (elements.title.value !== state.lastTitle) {
    return {
      conversionDetail: "片名已变更，重新转换后写入输出。",
      exportDetail: "片名已变更，当前导出仍使用旧片名。"
    };
  }

  if (elements.provider.value !== state.lastProvider) {
    return {
      conversionDetail: "处理模式已变更，重新转换后生效。",
      exportDetail: "处理模式已变更，当前导出仍使用旧结果。"
    };
  }

  if (elements.validate.checked !== state.lastValidate) {
    return {
      conversionDetail: "Schema 校验设置已变更，重新转换后生效。",
      exportDetail: "Schema 校验设置已变更，当前导出仍使用旧设置。"
    };
  }

  if (elements.provider.value === "openai" && normalizedModel() !== state.lastModel) {
    return {
      conversionDetail: "OpenAI 模型已变更，重新转换后生效。",
      exportDetail: "OpenAI 模型已变更，当前导出仍使用旧模型结果。"
    };
  }

  return null;
}

function setConversionStatus(label, detail, tone) {
  elements.conversionState.textContent = label;
  elements.conversionMeta.textContent = detail;
  setStatusTone(elements.conversionState.parentElement, tone);
  updateWorkflowSteps();
}

function updateConversionFreshness() {
  if (!state.output) {
    return;
  }

  if (isCurrentRequestTooLarge()) {
    return;
  }

  const staleReason = currentOutputStaleReason();
  if (staleReason) {
    setConversionStatus("需重新转换", staleReason.conversionDetail, "warn");
    return;
  }

  setConversionStatus(
    "已完成",
    `${formatDuration(state.lastDurationMs)} · ${providerStatusSummary(
      state.lastProviderStatus
    )} · ${conversionSummary(state.lastSummary)}`,
    "ready"
  );
}

function setStatusTone(element, tone) {
  element.classList.remove("is-active", "is-error", "is-ready", "is-warn");
  if (tone && tone !== "neutral") {
    element.classList.add(`is-${tone}`);
  }
}

function updateWorkflowSteps() {
  const characterCount = countCharacters(elements.manuscript.value);
  const tooLarge = isCurrentRequestTooLarge();
  const staleReason = state.output ? currentOutputStaleReason() : null;

  if (!characterCount) {
    setWorkflowStep("input", "neutral", "等待手稿");
  } else if (tooLarge) {
    setWorkflowStep("input", "error", "超过请求上限");
  } else {
    setWorkflowStep("input", "ready", `${formatNumber(characterCount)} 字`);
  }

  if (tooLarge) {
    setWorkflowStep("preview", "error", "无法预检");
  } else if (state.isPreviewPending) {
    setWorkflowStep("preview", "active", "解析章节中");
  } else if (state.isPreviewReady) {
    setWorkflowStep(
      "preview",
      state.previewWarningCount ? "warn" : "ready",
      state.previewWarningCount ? `${state.previewWarningCount} 章需补素材` : "章节已通过"
    );
  } else if (characterCount) {
    setWorkflowStep("preview", "warn", "未通过预检");
  } else {
    setWorkflowStep("preview", "neutral", "等待章节解析");
  }

  if (tooLarge) {
    setWorkflowStep("convert", "error", "无法转换");
  } else if (state.isWorking) {
    setWorkflowStep("convert", "active", "生成剧本中");
  } else if (state.remoteConfirmationResolve) {
    setWorkflowStep("convert", "warn", "等待远程确认");
  } else if (state.output && staleReason) {
    setWorkflowStep("convert", "warn", "需重新转换");
  } else if (state.output) {
    setWorkflowStep("convert", "ready", "结果已生成");
  } else if (state.isPreviewReady) {
    setWorkflowStep("convert", "active", "可开始转换");
  } else {
    setWorkflowStep("convert", "neutral", "等待预检通过");
  }

  if (state.output && staleReason) {
    setWorkflowStep("export", "warn", "结果已过期");
  } else if (state.output) {
    setWorkflowStep("export", "ready", `${selectedOutputLabel()} 可用`);
  } else if (state.isWorking) {
    setWorkflowStep("export", "active", "等待生成结果");
  } else {
    setWorkflowStep("export", "neutral", "等待生成结果");
  }
}

function setWorkflowStep(name, tone, detail) {
  const step = elements.workflowSteps[name];
  if (!step) {
    return;
  }
  setStatusTone(step, tone);
  const meta = elements[`${name}StepMeta`];
  if (meta) {
    meta.textContent = detail;
  }
}

function countCharacters(text) {
  return Array.from(text.replace(/\s/g, "")).length;
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatDuration(milliseconds) {
  if (milliseconds < 1000) {
    return `${milliseconds}ms`;
  }
  return `${(milliseconds / 1000).toFixed(1)}s`;
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.ceil(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function conversionSummary(summary) {
  if (!summary) {
    return "已生成输出。";
  }
  const missing = summary.chapter_coverage?.missing_chapters || [];
  if (missing.length) {
    return `缺失章节：${missing.join("、")}`;
  }
  return `${summary.scene_count ?? 0} 场 · coverage ${summary.coverage_score ?? 0}`;
}

function providerStatusSummary(status) {
  if (!status) {
    return "处理方式未知";
  }
  if (status.remote) {
    return "OpenAI 增强";
  }
  if (status.requested === "openai") {
    return "本地回退";
  }
  return "本地转换";
}

function normalizeExports(result) {
  const exports = result.exports || {};
  return {
    yaml:
      typeof exports.yaml === "string"
        ? exports.yaml
        : result.format === "yaml"
          ? result.output
          : "",
    fountain:
      typeof exports.fountain === "string"
        ? exports.fountain
        : result.format === "fountain"
          ? result.output
          : "",
    markdown:
      typeof exports.markdown === "string"
        ? exports.markdown
        : result.format === "markdown"
          ? result.output
          : "",
    draftJson:
      typeof exports.draft_json === "string"
        ? exports.draft_json
        : `${JSON.stringify(result.draft || {}, null, 2)}\n`,
    summaryJson:
      typeof exports.summary_json === "string"
        ? exports.summary_json
        : `${JSON.stringify(result.summary || {}, null, 2)}\n`
  };
}

function normalizeExportManifest(manifest, exports) {
  const files = Array.isArray(manifest?.files)
    ? manifest.files.map(normalizeExportManifestFile).filter(Boolean)
    : fallbackExportManifestFiles(exports);
  const contentBytes = files.reduce((total, file) => total + Number(file.byte_size || 0), 0);
  return {
    selected: normalizeExportKey(manifest?.selected || state.selectedOutput),
    files,
    bundle: {
      file_count: Number(manifest?.bundle?.file_count || files.length),
      content_bytes: Number(manifest?.bundle?.content_bytes || contentBytes)
    }
  };
}

function normalizeExportManifestFile(file) {
  if (!file || typeof file !== "object") {
    return null;
  }
  const key = normalizeExportKey(file.key);
  return {
    key,
    label: file.label || exportLabelForKey(key),
    extension: file.extension || outputExtension(key),
    byte_size: Number(file.byte_size || 0)
  };
}

function fallbackExportManifestFiles(exports) {
  return ["yaml", "fountain", "markdown", "draftJson", "summaryJson"].map((key) => ({
    key,
    label: exportLabelForKey(key),
    extension: outputExtension(key),
    byte_size: textEncoder.encode(exports[key] || "").length
  }));
}

function normalizeExportKey(key) {
  const keys = {
    draft_json: "draftJson",
    summary_json: "summaryJson"
  };
  return keys[key] || key || "yaml";
}

function exportLabelForKey(key) {
  const labels = {
    yaml: "YAML",
    fountain: "Fountain",
    markdown: "Markdown 修订简报",
    draftJson: "Draft JSON",
    summaryJson: "Summary JSON"
  };
  return labels[key] || selectedOutputLabel();
}

function downloadBaseName() {
  const title = elements.title.value.trim() || state.lastSummary?.title || "";
  const safeTitle = safeFilenameSegment(title);
  return safeTitle || "novel2script-draft";
}

function exportBundleFiles() {
  if (!state.exports) {
    return [];
  }
  const baseName = downloadBaseName();
  return [
    { name: `${baseName}.yaml`, content: state.exports.yaml || "" },
    { name: `${baseName}.fountain`, content: state.exports.fountain || "" },
    { name: `${baseName}.revision.md`, content: state.exports.markdown || "" },
    { name: `${baseName}.draft.json`, content: state.exports.draftJson || "" },
    { name: `${baseName}.summary.json`, content: state.exports.summaryJson || "" }
  ];
}

function safeFilenameSegment(value) {
  return value
    .normalize("NFKC")
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-")
    .replace(/\s+/g, " ")
    .replace(/[.\s-]+$/g, "")
    .replace(/^[.\s-]+/g, "")
    .slice(0, 80);
}

function withEmpty(items, message) {
  return Array.isArray(items) && items.length ? items : [message];
}

function emptyItem(text) {
  const item = document.createElement("div");
  item.className = "empty";
  item.textContent = text;
  return item;
}

async function loadFile() {
  const [file] = elements.file.files;
  if (!file) {
    return;
  }
  if (importedFileRequestByteLength(file) > maxRequestBytes) {
    elements.file.value = "";
    showFileImportSizeError(file);
    return;
  }
  let text;
  try {
    text = await file.text();
  } catch {
    elements.file.value = "";
    showFileImportReadError(file);
    return;
  }
  elements.manuscript.value = text;
  elements.file.value = "";
  if (!elements.title.value) {
    elements.title.value = file.name.replace(/\.[^.]+$/, "");
  }
  saveLocalDraft();
  setConversionStatus("待转换", `已导入 ${file.name}，等待章节预检。`, "active");
  updateInputStatus();
}

async function copyOutput() {
  if (!state.output) {
    return;
  }
  const staleReason = currentOutputStaleReason();
  if (staleReason) {
    updateExportStatus();
    setConversionStatus("需重新转换", staleReason.conversionDetail, "warn");
    return;
  }
  clearTimeout(state.copyLabelTimer);
  try {
    if (!navigator.clipboard?.writeText) {
      throw new Error("Clipboard API is unavailable.");
    }
    await navigator.clipboard.writeText(state.output);
    elements.copy.textContent = "已复制";
  } catch {
    elements.copy.textContent = "复制失败";
    setConversionStatus("复制失败", "浏览器未允许写入剪贴板，请手动选中结果复制。", "warn");
  }
  state.copyLabelTimer = window.setTimeout(() => {
    elements.copy.textContent = "复制";
  }, 1400);
}

function downloadOutput() {
  if (!state.output) {
    return;
  }
  const staleReason = currentOutputStaleReason();
  if (staleReason) {
    updateExportStatus();
    setConversionStatus("需重新转换", staleReason.conversionDetail, "warn");
    return;
  }
  clearTimeout(state.downloadLabelTimer);
  let objectUrl = "";
  try {
    const extension = outputExtension(state.selectedOutput);
    const blob = new Blob([state.output], { type: "text/plain;charset=utf-8" });
    const link = document.createElement("a");
    objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = `${downloadBaseName()}.${extension}`;
    link.click();
    elements.download.textContent = "已下载";
  } catch {
    elements.download.textContent = "下载失败";
    elements.exportState.textContent = "下载失败";
    elements.exportMeta.textContent = "浏览器未能启动下载，请复制结果后手动保存。";
    setStatusTone(elements.exportState.parentElement, "warn");
  } finally {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
    state.downloadLabelTimer = window.setTimeout(() => {
      elements.download.textContent = "下载";
    }, 1400);
  }
}

function outputExtension(selection) {
  if (selection === "fountain") {
    return "fountain";
  }
  if (selection === "markdown") {
    return "revision.md";
  }
  if (selection === "draftJson") {
    return "draft.json";
  }
  if (selection === "summaryJson") {
    return "summary.json";
  }
  return "yaml";
}

function clearWorkbench() {
  clearTimeout(state.previewLabelTimer);
  clearTimeout(state.copyLabelTimer);
  clearTimeout(state.downloadLabelTimer);
  clearTimeout(state.bundleLabelTimer);
  clearTimeout(state.draftSaveTimer);
  state.output = "";
  state.exports = null;
  state.exportManifest = null;
  state.selectedOutput = outputSelectionForFormat(elements.format.value);
  state.previewRequestId += 1;
  state.previewInput = "";
  state.isPreviewPending = false;
  state.isPreviewReady = false;
  state.previewWarningCount = 0;
  dismissRemoteConfirmation({ quiet: true });
  state.openAiConfirmedFor = "";
  state.lastConvertedInput = "";
  state.lastTitle = "";
  state.lastValidate = elements.validate.checked;
  state.lastProvider = elements.provider.value;
  state.lastModel = normalizedModel();
  state.lastProviderStatus = null;
  state.lastSummary = null;
  state.lastDurationMs = 0;

  elements.manuscript.value = "";
  elements.title.value = "";
  elements.file.value = "";
  elements.output.classList.remove("is-error");
  elements.output.textContent = "转换结果会显示在这里。";
  elements.copy.textContent = "复制";
  elements.download.textContent = "下载";
  elements.bundle.textContent = "打包";
  renderSummary(null);
  renderProviderSelectionStatus();
  renderOutputTabs();
  renderExportManifest();
  saveLocalDraft();
  updateInputStatus();
  setConversionStatus("待转换", "工作台已清空，等待手稿输入。", "neutral");
  updateExportStatus();
}

function downloadBundle() {
  if (!state.output || !state.exports) {
    return;
  }
  const staleReason = currentOutputStaleReason();
  if (staleReason) {
    updateExportStatus();
    setConversionStatus("需重新转换", staleReason.conversionDetail, "warn");
    return;
  }
  clearTimeout(state.bundleLabelTimer);
  let objectUrl = "";
  try {
    const blob = createZipBlob(exportBundleFiles());
    const link = document.createElement("a");
    objectUrl = URL.createObjectURL(blob);
    link.href = objectUrl;
    link.download = `${downloadBaseName()}-export.zip`;
    link.click();
    elements.bundle.textContent = "已打包";
  } catch {
    elements.bundle.textContent = "打包失败";
    elements.exportState.textContent = "打包失败";
    elements.exportMeta.textContent = "浏览器未能生成打包文件，请分别下载或复制结果。";
    setStatusTone(elements.exportState.parentElement, "warn");
  } finally {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
    state.bundleLabelTimer = window.setTimeout(() => {
      elements.bundle.textContent = "打包";
    }, 1400);
  }
}

function createZipBlob(files) {
  const chunks = [];
  const centralDirectory = [];
  let offset = 0;
  const timestamp = zipDosTimestamp(new Date());

  for (const file of files) {
    const nameBytes = textEncoder.encode(file.name);
    const dataBytes = textEncoder.encode(file.content);
    const crc = crc32(dataBytes);
    const localHeader = new Uint8Array(30 + nameBytes.length);
    const localView = new DataView(localHeader.buffer);
    localView.setUint32(0, 0x04034b50, true);
    localView.setUint16(4, 20, true);
    localView.setUint16(6, 0x0800, true);
    localView.setUint16(8, 0, true);
    localView.setUint16(10, timestamp.time, true);
    localView.setUint16(12, timestamp.date, true);
    localView.setUint32(14, crc, true);
    localView.setUint32(18, dataBytes.length, true);
    localView.setUint32(22, dataBytes.length, true);
    localView.setUint16(26, nameBytes.length, true);
    localView.setUint16(28, 0, true);
    localHeader.set(nameBytes, 30);

    const centralHeader = new Uint8Array(46 + nameBytes.length);
    const centralView = new DataView(centralHeader.buffer);
    centralView.setUint32(0, 0x02014b50, true);
    centralView.setUint16(4, 20, true);
    centralView.setUint16(6, 20, true);
    centralView.setUint16(8, 0x0800, true);
    centralView.setUint16(10, 0, true);
    centralView.setUint16(12, timestamp.time, true);
    centralView.setUint16(14, timestamp.date, true);
    centralView.setUint32(16, crc, true);
    centralView.setUint32(20, dataBytes.length, true);
    centralView.setUint32(24, dataBytes.length, true);
    centralView.setUint16(28, nameBytes.length, true);
    centralView.setUint16(30, 0, true);
    centralView.setUint16(32, 0, true);
    centralView.setUint16(34, 0, true);
    centralView.setUint16(36, 0, true);
    centralView.setUint32(38, 0, true);
    centralView.setUint32(42, offset, true);
    centralHeader.set(nameBytes, 46);

    chunks.push(localHeader, dataBytes);
    centralDirectory.push(centralHeader);
    offset += localHeader.length + dataBytes.length;
  }

  const centralOffset = offset;
  const centralSize = centralDirectory.reduce((size, header) => size + header.length, 0);
  const endHeader = new Uint8Array(22);
  const endView = new DataView(endHeader.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(4, 0, true);
  endView.setUint16(6, 0, true);
  endView.setUint16(8, files.length, true);
  endView.setUint16(10, files.length, true);
  endView.setUint32(12, centralSize, true);
  endView.setUint32(16, centralOffset, true);
  endView.setUint16(20, 0, true);

  chunks.push(...centralDirectory, endHeader);
  return new Blob(chunks, { type: "application/zip" });
}

function zipDosTimestamp(date) {
  return {
    time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
    date: ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate()
  };
}

function buildCrc32Table() {
  const table = new Uint32Array(256);
  for (let index = 0; index < table.length; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    table[index] = value >>> 0;
  }
  return table;
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = crc32Table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function setWorking(isWorking) {
  state.isWorking = isWorking;
  syncConvertAvailability();
  elements.convert.textContent = isWorking ? "转换中" : "转换";
  elements.fileButton.disabled = isWorking;
  elements.sample.disabled = isWorking;
  elements.clear.disabled = isWorking;
}

function syncConvertAvailability() {
  elements.convert.disabled =
    state.isWorking ||
    Boolean(state.remoteConfirmationResolve) ||
    state.isPreviewPending ||
    !state.isPreviewReady ||
    isCurrentRequestTooLarge();
}

function setOutputActions(isEnabled) {
  elements.copy.disabled = !isEnabled;
  elements.download.disabled = !isEnabled;
  elements.bundle.disabled = !isEnabled;
  for (const button of elements.outputTabs) {
    button.disabled = !isEnabled;
  }
}

elements.sample.addEventListener("click", () => {
  elements.manuscript.value = sampleText;
  saveLocalDraft();
  updateInputStatus();
});
elements.clear.addEventListener("click", clearWorkbench);
elements.fileButton.addEventListener("click", () => {
  elements.file.click();
});
elements.file.addEventListener("change", loadFile);
elements.title.addEventListener("input", () => {
  dismissRemoteConfirmation();
  scheduleLocalDraftSave();
  resetProviderRunStatus();
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.manuscript.addEventListener("input", () => {
  dismissRemoteConfirmation();
  scheduleLocalDraftSave();
  updateInputStatus();
});
elements.provider.addEventListener("change", () => {
  dismissRemoteConfirmation();
  scheduleLocalDraftSave();
  syncConvertAvailability();
  updateExportStatus();
  updateProviderStatus();
});
elements.model.addEventListener("input", () => {
  dismissRemoteConfirmation();
  scheduleLocalDraftSave();
  resetProviderRunStatus();
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.format.addEventListener("change", () => {
  scheduleLocalDraftSave();
  syncConvertAvailability();
  const selection = outputSelectionForFormat(elements.format.value);
  if (state.exports) {
    selectOutput(selection);
    return;
  }
  state.selectedOutput = selection;
  renderOutputTabs();
  updateExportStatus();
});
elements.validate.addEventListener("change", () => {
  scheduleLocalDraftSave();
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.convert.addEventListener("click", convertManuscript);
elements.copy.addEventListener("click", copyOutput);
elements.download.addEventListener("click", downloadOutput);
elements.bundle.addEventListener("click", downloadBundle);
elements.remoteConfirmCancel?.addEventListener("click", () => resolveRemoteConfirmation(false));
elements.remoteConfirmProceed?.addEventListener("click", () => resolveRemoteConfirmation(true));
for (const button of elements.outputTabs) {
  button.addEventListener("click", () => {
    selectOutput(button.dataset.outputFormat || "yaml");
  });
}
window.addEventListener("beforeunload", saveLocalDraft);

checkServer();
