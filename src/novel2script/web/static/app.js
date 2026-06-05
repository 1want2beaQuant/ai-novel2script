const sampleText = `Chapter 1 The Locked Room
Mara found a sealed letter on the desk. Rain tapped the glass while the house stayed silent.

Chapter 2 The Empty Hall
Jon arrived before dawn and saw fresh footprints crossing the hall.

Chapter 3 The Last Tape
Mara and Jon played the tape together. The hidden name finally connected every clue.`;

const maxRequestBytes = 2000000;
const defaultModel = "gpt-4.1-mini";
const textEncoder = new TextEncoder();

const state = {
  output: "",
  format: "yaml",
  isWorking: false,
  copyLabelTimer: 0,
  downloadLabelTimer: 0,
  previewLabelTimer: 0,
  previewRequestId: 0,
  previewInput: "",
  isPreviewPending: false,
  isPreviewReady: false,
  openAiConfirmedFor: "",
  lastConvertedInput: "",
  lastTitle: "",
  lastFormat: "yaml",
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
  file: document.querySelector("#fileInput"),
  fileButton: document.querySelector("#fileButton"),
  copy: document.querySelector("#copyButton"),
  download: document.querySelector("#downloadButton"),
  serverStatus: document.querySelector("#serverStatus"),
  inputSize: document.querySelector("#inputSize"),
  inputHint: document.querySelector("#inputHint"),
  providerMode: document.querySelector("#providerMode"),
  privacyHint: document.querySelector("#privacyHint"),
  conversionState: document.querySelector("#conversionState"),
  conversionMeta: document.querySelector("#conversionMeta"),
  exportState: document.querySelector("#exportState"),
  exportMeta: document.querySelector("#exportMeta"),
  coverageRatio: document.querySelector("#coverageRatio"),
  chapterCount: document.querySelector("#chapterCount"),
  sceneCount: document.querySelector("#sceneCount"),
  blockCount: document.querySelector("#blockCount"),
  dialogueCount: document.querySelector("#dialogueCount"),
  characterCount: document.querySelector("#characterCount"),
  coverageScore: document.querySelector("#coverageScore"),
  verdict: document.querySelector("#verdict"),
  logline: document.querySelector("#loglineText"),
  scoresList: document.querySelector("#scoresList"),
  actionItems: document.querySelector("#actionItems"),
  beatsList: document.querySelector("#beatsList"),
  scenesList: document.querySelector("#scenesList"),
  strengthsList: document.querySelector("#strengthsList"),
  weaknessesList: document.querySelector("#weaknessesList"),
  qualityList: document.querySelector("#qualityList")
};

elements.manuscript.value = sampleText;
elements.output.textContent = "转换结果会显示在这里。";
renderSummary(null);
updateInputStatus();
updateProviderStatus();
updateExportStatus();

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

  if (!confirmRemoteProvider()) {
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

    state.output = result.output;
    state.format = result.format;
    state.lastConvertedInput = payload.text;
    state.lastTitle = payload.title;
    state.lastFormat = payload.format;
    state.lastValidate = payload.validate;
    state.lastProvider = payload.provider;
    state.lastModel = requestModel;
    state.lastProviderStatus = result.provider_status || null;
    state.lastSummary = result.summary;
    state.lastDurationMs = Math.max(0, Math.round(performance.now() - startedAt));
    elements.output.textContent = result.output;
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

  renderScores(summary?.scores || []);
  renderActionItems(summary?.action_items || summary?.revision_checklist || []);
  renderBeats(summary?.structure_beats || []);
  renderScenes(summary?.scenes || []);
  renderTextList(elements.strengthsList, summary?.strengths || []);
  renderTextList(
    elements.weaknessesList,
    [...(summary?.weaknesses || []), ...(summary?.structure_diagnostics || [])]
  );
  renderTextList(elements.qualityList, summary?.quality_flags || summary?.revision_checklist || []);
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

      item.append(title, meta, summary);
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

    const title = document.createElement("strong");
    title.textContent = chapter.title || `章节 ${chapterIndex}`;

    item.append(marker, title);
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

function requestByteLength(payload) {
  return textEncoder.encode(JSON.stringify(payload)).length;
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
  state.isPreviewPending = false;
  state.isPreviewReady = Boolean(preview.ready);
  elements.inputSize.textContent = `${formatNumber(characterCount)} 字 / ${chapterCount} 章`;
  elements.inputHint.textContent = preview.message || "转换时会再次校验。";
  renderChapterPreview(preview.ready ? "已通过" : "未通过", preview.chapters || [], {
    emptyMessage: "未检测到章节",
    tone: preview.ready ? "ready" : "warn"
  });

  if (preview.ready) {
    setStatusTone(elements.inputSize.parentElement, "ready");
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

function confirmRemoteProvider() {
  if (elements.provider.value !== "openai") {
    return true;
  }

  const confirmationKey = remoteConfirmationKey();
  if (state.openAiConfirmedFor === confirmationKey) {
    return true;
  }

  const confirmed = window.confirm(
    "OpenAI 模式会把当前手稿生成的截断章节摘要和本地 baseline JSON 发送给配置的远程兼容接口。确认继续？"
  );
  if (!confirmed) {
    setConversionStatus("已取消", "未确认远程发送，转换没有开始。", "warn");
    return false;
  }

  state.openAiConfirmedFor = confirmationKey;
  return true;
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
  const formatLabel = elements.format.value === "fountain" ? "Fountain" : "YAML";
  const validationLabel = elements.validate.checked ? "Schema 校验开启" : "Schema 校验关闭";

  if (state.output) {
    const staleReason = currentOutputStaleReason();
    if (staleReason) {
      elements.exportState.textContent = "需重新转换";
      elements.exportMeta.textContent = `${staleReason.exportDetail} 重新转换后再复制或下载。`;
      setStatusTone(elements.exportState.parentElement, "warn");
      setOutputActions(false);
      return;
    }

    elements.exportState.textContent = formatLabel;
    elements.exportMeta.textContent = `${validationLabel} · 可复制或下载。`;
    setStatusTone(elements.exportState.parentElement, "ready");
    setOutputActions(true);
    return;
  }

  elements.exportState.textContent = "未生成";
  elements.exportMeta.textContent = `${formatLabel} / ${validationLabel}。`;
  setStatusTone(elements.exportState.parentElement, "neutral");
  setOutputActions(false);
}

function currentOutputStaleReason() {
  const formatLabel = elements.format.value === "fountain" ? "Fountain" : "YAML";
  const outputLabel = state.format === "fountain" ? "Fountain" : "YAML";

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

  if (elements.format.value !== state.lastFormat) {
    return {
      conversionDetail: "输出格式已变更，重新转换后生成当前格式。",
      exportDetail: `当前结果仍是 ${outputLabel}，目标导出为 ${formatLabel}。`
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

function downloadBaseName() {
  const title = elements.title.value.trim() || state.lastSummary?.title || "";
  const safeTitle = safeFilenameSegment(title);
  return safeTitle || "novel2script-draft";
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
    const extension = state.format === "fountain" ? "fountain" : "yaml";
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

function setWorking(isWorking) {
  state.isWorking = isWorking;
  syncConvertAvailability();
  elements.convert.textContent = isWorking ? "转换中" : "转换";
  elements.fileButton.disabled = isWorking;
  elements.sample.disabled = isWorking;
}

function syncConvertAvailability() {
  elements.convert.disabled =
    state.isWorking || state.isPreviewPending || !state.isPreviewReady || isCurrentRequestTooLarge();
}

function setOutputActions(isEnabled) {
  elements.copy.disabled = !isEnabled;
  elements.download.disabled = !isEnabled;
}

elements.sample.addEventListener("click", () => {
  elements.manuscript.value = sampleText;
  updateInputStatus();
});
elements.fileButton.addEventListener("click", () => {
  elements.file.click();
});
elements.file.addEventListener("change", loadFile);
elements.title.addEventListener("input", () => {
  resetProviderRunStatus();
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.manuscript.addEventListener("input", updateInputStatus);
elements.provider.addEventListener("change", () => {
  syncConvertAvailability();
  updateExportStatus();
  updateProviderStatus();
});
elements.model.addEventListener("input", () => {
  resetProviderRunStatus();
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.format.addEventListener("change", () => {
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.validate.addEventListener("change", () => {
  syncConvertAvailability();
  updateExportStatus();
  updateConversionFreshness();
});
elements.convert.addEventListener("click", convertManuscript);
elements.copy.addEventListener("click", copyOutput);
elements.download.addEventListener("click", downloadOutput);

checkServer();
