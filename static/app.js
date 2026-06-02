/**
 * Dementia Design Poster Generator — Frontend
 */

const API = {
  images: '/api/images',
  pipelines: '/api/pipelines',
  settings: '/api/settings',
  errors: '/api/errors',
  systemLog: '/api/system/log',
  jobs: '/api/jobs',
  queue: '/api/queue',
  capture: '/api/capture',
  upload: '/api/upload',
  run: '/api/run',
  status: '/api/status',
  runConfig: '/api/run-config',
  results: '/api/results',
  library: '/api/library',
  libraryExport: '/api/library/export',
  libraryImport: '/api/library/import',
  configSource: '/api/config/source',
  configReset: '/api/config/source/reset',
  cancel: '/api/cancel',
  meaningfulDifferenceClear: '/api/meaningful-difference/clear',
  watchedFolderPick: '/api/watched-folder/pick',
};
const PIPELINE_EDITING_ENABLED = false;

// --- DOM refs ---
const imagePickerGrid = document.getElementById('image-picker-grid');
const btnOpenPipelineEditor = document.getElementById('btn-open-pipeline-editor');
const imageUploadInput = document.getElementById('image-upload-input');
const btnUploadImage = document.getElementById('btn-upload-image');
const pipelineEditorModal = document.getElementById('pipeline-editor-modal');
const pipelineEditorBackdrop = document.getElementById('pipeline-editor-backdrop');
const btnPipelineEditorClose = document.getElementById('btn-pipeline-editor-close');
const pipelineEditorSelect = document.getElementById('pipeline-editor-select');
const pipelineEditorPath = document.getElementById('pipeline-editor-path');
const pipelineEditorTextarea = document.getElementById('pipeline-editor-textarea');
const newPipelineName = document.getElementById('new-pipeline-name');
const btnCreatePipeline = document.getElementById('btn-create-pipeline');
const btnPipelineEditorSave = document.getElementById('btn-pipeline-editor-save');
const outputModal = document.getElementById('output-modal');
const outputBackdrop = document.getElementById('output-backdrop');
const btnOutputPrev = document.getElementById('btn-output-prev');
const btnOutputNext = document.getElementById('btn-output-next');
const btnOutputReprint = document.getElementById('btn-output-reprint');
const btnOutputReload = document.getElementById('btn-output-reload');
const btnOutputClose = document.getElementById('btn-output-close');
const outputModalBody = document.getElementById('output-modal-body');
const cameraVideo = document.getElementById('camera-video');
const cameraPlaceholder = document.getElementById('camera-placeholder');
const cameraStatus = document.getElementById('camera-status');
const btnCameraStart = document.getElementById('btn-camera-start');
const btnCameraCapture = document.getElementById('btn-camera-capture');
const btnToggleInputRow = document.getElementById('btn-toggle-input-row');
const inputBoard = document.getElementById('input-board');
const selectionCount = document.getElementById('selection-count');
const btnSelectAll = document.getElementById('btn-select-all');
const btnClearSelection = document.getElementById('btn-clear-selection');
const aspectRatioSelect = document.getElementById('aspect-ratio-select');
const pipelineSelect = document.getElementById('pipeline-select');
const pipelinePath = document.getElementById('pipeline-path');
const promptInterp = document.getElementById('prompt-interpretation');
const promptInterpEditor = document.getElementById('prompt-interpretation-editor');
const promptImage = document.getElementById('prompt-image');
const promptImageEditor = document.getElementById('prompt-image-editor');
const meaningfulDifferenceEditor = document.getElementById('meaningful-difference-editor');
const runCountInput = document.getElementById('run-count');
const encourageVarietyWithinBatchesToggle = document.getElementById('encourage-variety-within-batches-toggle');
const encourageVarietyWithinBatchesCheckbox = document.getElementById('encourage-variety-within-batches');
const encourageVarietyAcrossSessionCheckbox = document.getElementById('encourage-variety-across-session');
const btnClearMeaningfulDifference = document.getElementById('btn-clear-meaningful-difference');
const btnClearMeaningfulDifferenceHeader = document.getElementById('btn-clear-meaningful-difference-header');
const btnRun = document.getElementById('btn-run');
const btnRefresh = document.getElementById('btn-refresh');
const btnSettings = document.getElementById('btn-settings');
const watcherEnabledToggle = document.getElementById('watcher-enabled-toggle');
const watchedFolderInput = document.getElementById('watched-folder-input');
const settingsModal = document.getElementById('settings-modal');
const settingsBackdrop = document.getElementById('settings-backdrop');
const btnSettingsClose = document.getElementById('btn-settings-close');
const btnSettingsSave = document.getElementById('btn-settings-save');
const btnLibraryExport = document.getElementById('btn-library-export');
const btnLibraryImport = document.getElementById('btn-library-import');
const libraryImportInput = document.getElementById('library-import-input');
const settingsConfigEditor = document.getElementById('settings-config-editor');
const btnConfigSave = document.getElementById('btn-config-save');
const btnConfigReset = document.getElementById('btn-config-reset');
const settingsDefaultPipeline = document.getElementById('settings-default-pipeline');
const settingsPrinterName = document.getElementById('settings-printer-name');
const settingsSendToPrinter = document.getElementById('settings-send-to-printer');
const settingsHttpAccessLogging = document.getElementById('settings-http-access-logging');
const settingsTextModel = document.getElementById('settings-text-model');
const settingsImageModel = document.getElementById('settings-image-model');
const settingsSkipImageGeneration = document.getElementById('settings-skip-image-generation');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const statusMessage = document.getElementById('status-message');
const systemLogStatus = document.getElementById('system-log-status');
const systemLogList = document.getElementById('system-log-list');
const btnSystemLogJump = document.getElementById('btn-system-log-jump');
const btnSystemLogPause = document.getElementById('btn-system-log-pause');
const btnSystemLogClear = document.getElementById('btn-system-log-clear');
const btnToggleSystemLog = document.getElementById('btn-toggle-system-log');
const btnToggleJobBrowser = document.getElementById('btn-toggle-job-browser');
const btnToggleLibrary = document.getElementById('btn-toggle-library');
const btnToggleMeaningfulDifference = document.getElementById('btn-toggle-meaningful-difference');
const jobBrowserGrid = document.getElementById('job-browser-grid');
const btnCancel = document.getElementById('btn-cancel');
const debugModal = document.getElementById('debug-modal');
const debugBackdrop = document.getElementById('debug-backdrop');
const btnDebugClose = document.getElementById('btn-debug-close');
const btnDebugClear = document.getElementById('btn-debug-clear');
const debugList = document.getElementById('debug-list');
const jobJsonModal = document.getElementById('job-json-modal');
const jobJsonBackdrop = document.getElementById('job-json-backdrop');
const btnJobJsonClose = document.getElementById('btn-job-json-close');
const jobJsonContent = document.getElementById('job-json-content');
const assetPreviewModal = document.getElementById('asset-preview-modal');
const assetPreviewBackdrop = document.getElementById('asset-preview-backdrop');
const btnAssetPreviewClose = document.getElementById('btn-asset-preview-close');
const assetPreviewTitle = document.getElementById('asset-preview-title');
const assetPreviewBody = document.getElementById('asset-preview-body');
const metadataImportModal = document.getElementById('metadata-import-modal');
const metadataImportBackdrop = document.getElementById('metadata-import-backdrop');
const btnMetadataImportClose = document.getElementById('btn-metadata-import-close');
const btnMetadataImportApply = document.getElementById('btn-metadata-import-apply');
const metadataImportPipeline = document.getElementById('metadata-import-pipeline');
const metadataImportInterpretation = document.getElementById('metadata-import-interpretation');
const metadataImportConcepts = document.getElementById('metadata-import-concepts');
const metadataImportDescription = document.getElementById('metadata-import-description');
const metadataImportImagePrompt = document.getElementById('metadata-import-image-prompt');
const metadataImportImageModel = document.getElementById('metadata-import-image-model');
const metadataImportAspectRatio = document.getElementById('metadata-import-aspect-ratio');
const jobHoverPreview = document.getElementById('job-hover-preview');
const jobHoverPreviewTitle = document.getElementById('job-hover-preview-title');
const jobHoverPreviewImage = document.getElementById('job-hover-preview-image');
const stageInput = document.getElementById('stage-input');
const stageSystemLog = document.getElementById('stage-system-log');
const stageJobBrowser = document.getElementById('stage-job-browser');
const stageLibrary = document.getElementById('stage-library');
const stageInterpretation = document.getElementById('stage-interpretation');
const stageMeaningfulDifference = document.getElementById('stage-meaningful-difference');
const stageDescription = document.getElementById('stage-description');
const stageImagePrompt = document.getElementById('stage-image-prompt');
const resizeHandleBottom = document.getElementById('resize-handle-bottom');
const descriptionEditor = document.getElementById('description-editor');
const libraryGrid = document.getElementById('library-grid');

let pollInterval = null;
let systemMonitorInterval = null;
let activeJobProgressInterval = null;
let cameraStream = null;
let images = [];
let libraryItems = [];
let currentPipelineId = null;
let defaultPipelineId = null;
let availablePrinters = [];
let printerName = '';
let sendToPrinter = false;
let httpAccessLogging = false;
let skipImageGeneration = false;
let watcherEnabled = true;
let watchedFolder = '/watch';
let errorItems = [];
let systemLogItems = [];
let pendingSystemLogItems = [];
let jobItems = [];
let queueStatus = {
  worker_running: false,
  queued_count: 0,
  queued_items: [],
  current_item: null,
};
let configSourceContent = '';
let activeJobId = null;
let systemLogPaused = false;
let systemLogPinnedToBottom = true;
let activeJobHoverKey = null;
let currentPosterFilename = null;
let loadedMetadataPosterFilename = null;
let textModel = 'anthropic/claude-opus-4.6';
let imageModel = 'replicate:google/nano-banana-pro';
let extractedConcepts = '';
let meaningfulDifferenceText = '';
let batchVarietyText = '';
let sessionVarietyText = '';
let pipelineEditorCurrentId = null;
let pipelineEditorSaveTimeout = null;
let pipelineEditorIsLoading = false;
let pipelineEditorLastSavedContent = '';
let imagesRefreshInterval = null;
let pipelineStatus = 'idle';
let promptSaveTimeout = null;
let promptSaveInFlight = false;
let promptSavePending = false;
let promptLastSavedState = null;
let interpretationHistory = [];
let activeResize = null;
let inputRowCollapsed = false;
let systemLogCollapsed = false;
let jobBrowserCollapsed = false;
let libraryCollapsed = false;
let meaningfulDifferenceCollapsed = false;
let runConfigSaveTimeout = null;
let watcherSettingsSaveTimeout = null;
let layoutSettings = {
  content_row_height: 448,
};
let lastLibraryPosterFilename = null;
const selectedImages = new Set();
const MODEL_ASPECT_RATIOS = {
  'replicate:openai/gpt-image-1.5': ['1:1', '3:2', '2:3'],
  'replicate:openai/gpt-image-2': ['1:1', '3:2', '2:3'],
};

// --- Init ---
async function init() {
  await loadImages();
  await loadPipelines();
  await loadLibrary();
  await loadSettings();
  await loadErrors();
  await loadSystemLog();
  await loadJobs();
  await loadQueueStatus();

  btnRefresh.addEventListener('click', loadImages);
  btnUploadImage.addEventListener('click', uploadSelectedImage);
  if (btnOpenPipelineEditor) {
    btnOpenPipelineEditor.addEventListener('click', openPipelineEditorModal);
  }
  btnPipelineEditorClose.addEventListener('click', closePipelineEditorModal);
  pipelineEditorBackdrop.addEventListener('click', closePipelineEditorModal);
  pipelineEditorSelect.addEventListener('change', () => loadPipelineSource(pipelineEditorSelect.value));
  pipelineEditorTextarea.addEventListener('input', schedulePipelineEditorAutosave);
  btnCreatePipeline.addEventListener('click', createPipelineFromEditor);
  btnPipelineEditorSave.addEventListener('click', savePipelineSource);
  document.addEventListener('click', handleBlockedControlClick, true);
  btnOutputPrev.addEventListener('click', showPreviousOutput);
  btnOutputNext.addEventListener('click', showNextOutput);
  btnOutputReprint.addEventListener('click', reprintCurrentOutput);
  btnOutputReload.addEventListener('click', reloadCurrentPosterMetadata);
  btnOutputClose.addEventListener('click', closeOutputModal);
  outputBackdrop.addEventListener('click', closeOutputModal);
  btnRun.addEventListener('click', runPipeline);
  btnSettings.addEventListener('click', openSettingsModal);
  if (btnCancel) {
    btnCancel.addEventListener('click', cancelPipeline);
  }
  btnSettingsClose.addEventListener('click', closeSettingsModal);
  settingsBackdrop.addEventListener('click', closeSettingsModal);
  watcherEnabledToggle.addEventListener('change', handleWatcherSettingsChange);
  watchedFolderInput.addEventListener('click', pickWatchedFolder);
  settingsDefaultPipeline.addEventListener('change', handleDefaultPipelineChange);
  settingsTextModel.addEventListener('change', handleRunConfigChange);
  settingsImageModel.addEventListener('change', handleRunConfigChange);
  settingsPrinterName.addEventListener('change', handlePrinterSettingsChange);
  settingsSendToPrinter.addEventListener('change', handlePrinterSettingsChange);
  settingsSkipImageGeneration.addEventListener('change', handleSkipImageGenerationChange);
  aspectRatioSelect.addEventListener('change', handleRunConfigChange);
  btnSettingsSave.addEventListener('click', saveSettings);
  btnLibraryExport.addEventListener('click', exportLibrary);
  btnLibraryImport.addEventListener('click', () => libraryImportInput.click());
  libraryImportInput.addEventListener('change', importLibrary);
  btnConfigSave.addEventListener('click', saveConfigSource);
  btnConfigReset.addEventListener('click', resetConfigSource);
  btnSystemLogPause.addEventListener('click', toggleSystemLogPause);
  btnSystemLogClear.addEventListener('click', clearSystemLog);
  btnSystemLogJump.addEventListener('click', jumpSystemLogToLatest);
  btnToggleSystemLog.addEventListener('click', toggleSystemLog);
  btnToggleJobBrowser.addEventListener('click', toggleJobBrowser);
  btnToggleLibrary.addEventListener('click', toggleLibrary);
  btnToggleMeaningfulDifference.addEventListener('click', toggleMeaningfulDifference);
  if (btnClearMeaningfulDifferenceHeader) {
    btnClearMeaningfulDifferenceHeader.addEventListener('click', clearMeaningfulDifference);
  }
  systemLogList.addEventListener('scroll', handleSystemLogScroll);
  btnDebugClose.addEventListener('click', closeDebugModal);
  btnDebugClear.addEventListener('click', clearErrors);
  debugBackdrop.addEventListener('click', closeDebugModal);
  btnJobJsonClose.addEventListener('click', closeJobJsonModal);
  jobJsonBackdrop.addEventListener('click', closeJobJsonModal);
  btnAssetPreviewClose.addEventListener('click', closeAssetPreviewModal);
  assetPreviewBackdrop.addEventListener('click', closeAssetPreviewModal);
  btnMetadataImportClose.addEventListener('click', closeMetadataImportModal);
  metadataImportBackdrop.addEventListener('click', closeMetadataImportModal);
  btnMetadataImportApply.addEventListener('click', applyMetadataImportSelection);
  jobBrowserGrid.addEventListener('click', handleJobBrowserClick);
  jobBrowserGrid.addEventListener('mouseover', handleJobBrowserHoverStart);
  jobBrowserGrid.addEventListener('mouseout', handleJobBrowserHoverEnd);
  jobBrowserGrid.addEventListener('mousemove', handleJobBrowserHoverMove);
  btnCameraStart.addEventListener('click', toggleCamera);
  btnCameraCapture.addEventListener('click', captureFrame);
  btnToggleInputRow.addEventListener('click', toggleInputRow);
  btnSelectAll.addEventListener('click', selectAllImages);
  btnClearSelection.addEventListener('click', clearSelection);
  imagePickerGrid.addEventListener('click', handleImageGridClick);
  pipelineSelect.addEventListener('change', handlePipelineSelectionChange);
  promptInterpEditor.addEventListener('input', handlePromptInterpEditorInput);
  promptImageEditor.addEventListener('input', handlePromptImageEditorInput);
  promptImageEditor.addEventListener('keydown', handlePromptImageEditorKeydown);
  runCountInput.addEventListener('input', handleRunCountChange);
  encourageVarietyWithinBatchesCheckbox.addEventListener('change', handleOperationalConfigChange);
  encourageVarietyAcrossSessionCheckbox.addEventListener('change', handleOperationalConfigChange);
  btnClearMeaningfulDifference.addEventListener('click', clearMeaningfulDifference);
  initRowResizers();
  descriptionEditor.addEventListener('input', () => {
    renderPromptImageEditor();
  });
  applyPipelineEditingLock();

  // Check if pipeline is already running (e.g. page refresh)
  const status = await fetchJSON(API.status);
  if (status?.pipeline_id) {
    await loadPipeline(status.pipeline_id);
  }
  if (status) {
    applyStatusState(status);
  }
  renderJobBrowser();
  if (status && !['idle', 'complete', 'error'].includes(status.status)) {
    startPolling();
  }

  startImageAutoRefresh();
  startSystemMonitor();
  restoreInputRowPreference();
  restoreSystemLogPreference();
  restoreJobBrowserPreference();
  restoreLibraryPreference();
  restoreMeaningfulDifferencePreference();
  updateVarietyGuidanceEditorHeight();
  syncRunOptions();
  updateRunButtonState();
  updateRunConfigInteractivity();
}

function applyPipelineEditingLock() {
  const pipelineEditingDisabled = !PIPELINE_EDITING_ENABLED;
  promptInterp.readOnly = pipelineEditingDisabled;
  promptInterpEditor.contentEditable = pipelineEditingDisabled ? 'false' : 'true';
  promptInterpEditor.setAttribute('aria-disabled', pipelineEditingDisabled ? 'true' : 'false');
  promptImage.readOnly = pipelineEditingDisabled;
  promptImageEditor.contentEditable = pipelineEditingDisabled ? 'false' : 'true';
  promptImageEditor.setAttribute('aria-disabled', pipelineEditingDisabled ? 'true' : 'false');
  pipelineEditorTextarea.readOnly = pipelineEditingDisabled;
  newPipelineName.readOnly = pipelineEditingDisabled;
  btnCreatePipeline.disabled = pipelineEditingDisabled;
  btnPipelineEditorSave.disabled = pipelineEditingDisabled;
}

function renderPrinterOptions(selectedPrinterName = '') {
  const options = [];
  availablePrinters.forEach(name => {
    options.push(`<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`);
  });
  settingsPrinterName.innerHTML = options.join('');
  if (availablePrinters.includes(selectedPrinterName)) {
    settingsPrinterName.value = selectedPrinterName;
  } else if (availablePrinters.length > 0) {
    settingsPrinterName.selectedIndex = 0;
  } else {
    settingsPrinterName.selectedIndex = -1;
  }
  settingsPrinterName.disabled = !sendToPrinter || isBatchRunning();
}

// --- Fetch helper ---
async function fetchJSON(url, options = {}) {
  try {
    const resp = await fetch(url, options);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || resp.statusText);
    }
    return await resp.json();
  } catch (e) {
    console.error(`Fetch error (${url}):`, e);
    if (url !== API.errors) {
      await recordError(`Fetch error (${url}): ${e.message}`, 'client');
    }
    return null;
  }
}

// --- Load images ---
async function loadImages() {
  btnRefresh.disabled = true;
  const data = await fetchJSON(API.images);
  btnRefresh.disabled = false;
  images = data?.images || [];
  syncSelectionWithAvailableImages();

  if (!data || !images.length) {
    imagePickerGrid.innerHTML = '<p class="empty-state">No images found in watch folder</p>';
    updateSelectionSummary();
    updateRunButtonState();
    return;
  }

  imagePickerGrid.innerHTML = images.map(img => `
    <button class="image-thumb ${selectedImages.has(img.filename) ? 'selected' : ''}" type="button" data-filename="${escapeHtml(img.filename)}">
      <img src="${img.data_url}" alt="${img.filename}" loading="lazy">
      <span class="thumb-check">${selectedImages.has(img.filename) ? 'Selected' : 'Select'}</span>
      <span class="thumb-delete" data-delete-filename="${escapeHtml(img.filename)}" role="button" aria-label="Delete ${escapeHtml(img.filename)}" title="Delete image">Delete</span>
      <span class="thumb-label">${img.filename}</span>
    </button>
  `).join('');

  renderSelection();
}

async function uploadSelectedImage() {
  if (isBatchRunning()) return;
  const file = imageUploadInput.files?.[0];
  if (!file) {
    updateStatus('error', 'Error', 'Choose an image to upload first.');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  btnUploadImage.disabled = true;

  const result = await fetchJSON(API.upload, {
    method: 'POST',
    body: formData,
  });

  btnUploadImage.disabled = false;
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to upload image.');
    return;
  }

  imageUploadInput.value = '';
  await loadImages();
  selectedImages.add(result.filename);
  renderSelection();
  updateStatus('idle', 'Idle', `${result.filename} uploaded to watch folder.`);
}

async function loadLibrary() {
  const data = await fetchJSON(API.library);
  libraryItems = data?.items || [];

  if (!libraryItems.length) {
    libraryGrid.innerHTML = '<p class="empty-state">No generated posters yet.</p>';
    return;
  }

  libraryGrid.innerHTML = libraryItems.map(item => `
    <button class="library-item" type="button" data-filename="${escapeHtml(item.poster_filename)}">
      <img src="/output/${encodeURIComponent(item.poster_filename)}" alt="${item.poster_filename}" loading="lazy">
      <span class="library-label">${formatLibraryLabel(item.created_at)}</span>
    </button>
  `).join('');

  libraryGrid.querySelectorAll('.library-item').forEach(button => {
    button.addEventListener('click', () => previewLibraryItem(button.dataset.filename));
  });

  renderLibrarySelectionState();
}

async function loadSystemLog() {
  const data = await fetchJSON(API.systemLog);
  if (!data) return;
  const items = Array.isArray(data.items) ? data.items : [];
  if (systemLogPaused) {
    pendingSystemLogItems = items;
    updateSystemLogStatus();
    return;
  }
  systemLogItems = items;
  pendingSystemLogItems = [];
  renderSystemLog();
}

async function loadPipelines() {
  const data = await fetchJSON(API.pipelines);
  const items = data?.items || [];
  currentPipelineId = data?.current_pipeline_id || items[0]?.id || null;
  defaultPipelineId = data?.default_pipeline_id || currentPipelineId;

  if (!items.length) {
    pipelineSelect.innerHTML = '';
    pipelinePath.textContent = 'No pipeline files found.';
    settingsDefaultPipeline.innerHTML = '';
    return;
  }

  pipelineSelect.innerHTML = items.map(item => `
    <option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>
  `).join('');
  settingsDefaultPipeline.innerHTML = items.map(item => `
    <option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>
  `).join('');
  pipelineEditorSelect.innerHTML = items.map(item => `
    <option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>
  `).join('');
  pipelineSelect.value = currentPipelineId;
  settingsDefaultPipeline.value = defaultPipelineId;
  pipelineEditorSelect.value = currentPipelineId;
  await loadPipeline(currentPipelineId);
}

async function loadSettings() {
  const data = await fetchJSON(API.settings);
  const availableTextModels = Array.isArray(data?.available_text_models) ? data.available_text_models : [];
  availablePrinters = Array.isArray(data?.available_printers) ? data.available_printers : [];
  printerName = data?.printer_name || '';
  sendToPrinter = Boolean(data?.send_to_printer);
  httpAccessLogging = Boolean(data?.http_access_logging);
  skipImageGeneration = Boolean(data?.skip_image_generation);
  watcherEnabled = data?.watcher_enabled !== false;
  watchedFolder = data?.watched_folder || '/watch';
  textModel = data?.text_model || 'anthropic/claude-opus-4.6';
  imageModel = data?.image_model || 'replicate:google/nano-banana-pro';
  const aspectRatio = data?.aspect_ratio || '3:4';
  const runCount = Math.max(1, Math.min(20, Number.parseInt(data?.run_count || '1', 10) || 1));
  encourageVarietyWithinBatchesCheckbox.checked = Boolean(data?.encourage_variety_within_batches);
  encourageVarietyAcrossSessionCheckbox.checked = Boolean(data?.encourage_variety_across_session);
  layoutSettings = { ...layoutSettings, ...(data?.layout || {}) };
  renderPrinterOptions(printerName);
  settingsSendToPrinter.checked = sendToPrinter;
  watcherEnabledToggle.checked = watcherEnabled;
  watchedFolderInput.value = watchedFolder;
  settingsHttpAccessLogging.checked = httpAccessLogging;
  if (availableTextModels.length) {
    settingsTextModel.innerHTML = availableTextModels.map(item => `
      <option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>
    `).join('');
  }
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  settingsSkipImageGeneration.checked = skipImageGeneration;
  applyLayoutSettings();
  syncAspectRatioOptions(imageModel, aspectRatio);
  aspectRatioSelect.value = aspectRatio;
  runCountInput.value = String(runCount);
  syncRunOptions();
}

async function loadConfigSource() {
  const data = await fetchJSON(API.configSource);
  if (!data) return;
  configSourceContent = data.content || '';
  settingsConfigEditor.value = configSourceContent;
}

async function loadErrors() {
  const data = await fetchJSON(API.errors);
  errorItems = data?.items || [];
}

async function loadJobs() {
  const data = await fetchJSON(API.jobs);
  if (!data) return;
  jobItems = Array.isArray(data.items) ? data.items : [];
  renderJobBrowser();
}

async function loadQueueStatus() {
  const data = await fetchJSON(API.queue);
  if (!data) return;
  queueStatus = {
    worker_running: Boolean(data.worker_running),
    queued_count: Number(data.queued_count || 0),
    queued_items: Array.isArray(data.queued_items) ? data.queued_items : [],
    current_item: data.current_item || null,
  };
  renderJobBrowser();
}

async function loadPipeline(pipelineId) {
  if (!pipelineId) return;

  clearTimeout(promptSaveTimeout);
  promptSavePending = false;

  const pipeline = await fetchJSON(`${API.pipelines}/${encodeURIComponent(pipelineId)}`);
  if (!pipeline) return;

  currentPipelineId = pipeline.id;
  pipelineSelect.value = pipeline.id;
  setPromptInterpValue(pipeline.interpretation || '');
  setPromptImageValue(pipeline.image || '');
  pipelinePath.textContent = pipeline.path || '';
  promptLastSavedState = JSON.stringify({
    pipelineId: pipeline.id,
    interpretation: getPromptInterpValue(),
    image: getPromptImageValue(),
  });
}

function schedulePromptAutosave() {
  if (!PIPELINE_EDITING_ENABLED) return;
  clearTimeout(promptSaveTimeout);
  promptSaveTimeout = setTimeout(() => {
    savePromptsToPipeline();
  }, 700);
}

async function savePromptsToPipeline() {
  if (!PIPELINE_EDITING_ENABLED) return;
  if (!currentPipelineId) return;

  const saveState = JSON.stringify({
    pipelineId: currentPipelineId,
    interpretation: getPromptInterpValue(),
    image: getPromptImageValue(),
  });
  if (saveState === promptLastSavedState) {
    return;
  }
  if (promptSaveInFlight) {
    promptSavePending = true;
    return;
  }

  promptSaveInFlight = true;
  promptSavePending = false;
  const payload = JSON.parse(saveState);
  const result = await fetchJSON(`${API.pipelines}/${encodeURIComponent(currentPipelineId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      interpretation: payload.interpretation,
      image: payload.image,
    }),
  });
  promptSaveInFlight = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to save pipeline prompts.');
    return;
  }

  promptLastSavedState = saveState;
  pipelinePath.textContent = result.path || pipelinePath.textContent;
  if (promptSavePending) {
    promptSavePending = false;
    savePromptsToPipeline();
  }
}

async function openSettingsModal() {
  settingsDefaultPipeline.value = defaultPipelineId || currentPipelineId || '';
  renderPrinterOptions(printerName);
  settingsSendToPrinter.checked = sendToPrinter;
  settingsHttpAccessLogging.checked = httpAccessLogging;
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  encourageVarietyWithinBatchesCheckbox.checked = Boolean(encourageVarietyWithinBatchesCheckbox.checked);
  encourageVarietyAcrossSessionCheckbox.checked = Boolean(encourageVarietyAcrossSessionCheckbox.checked);
  settingsSkipImageGeneration.checked = skipImageGeneration;
  syncAspectRatioOptions(settingsImageModel.value, aspectRatioSelect.value || '3:4');
  syncRunOptions();
  await loadConfigSource();
  settingsModal.hidden = false;
}

function closeSettingsModal() {
  settingsModal.hidden = true;
}

function startActiveJobProgressRefresh() {
  if (activeJobProgressInterval) clearInterval(activeJobProgressInterval);
  activeJobProgressInterval = setInterval(() => {
    const activeJob = getActiveJobRecord();
    if (activeJob && String(activeJob.status || '') === 'generating') {
      renderJobBrowser();
    }
  }, 1000);
}

function startImageAutoRefresh() {
  if (imagesRefreshInterval) clearInterval(imagesRefreshInterval);
  imagesRefreshInterval = setInterval(() => {
    loadImages();
  }, 1000);
}

function startSystemMonitor() {
  if (systemMonitorInterval) clearInterval(systemMonitorInterval);
  startActiveJobProgressRefresh();
  systemMonitorInterval = setInterval(async () => {
    await loadSystemLog();
    await loadJobs();
    await loadQueueStatus();
    if (!pollInterval) {
      const status = await fetchJSON(API.status);
      if (status) {
        applyStatusState(status);
        if (isBatchStatus(status.status)) {
          startPolling();
        }
      }
    }
  }, 2000);
}

async function openPipelineEditorModal() {
  if (isBatchRunning()) return;
  if (!pipelineEditorSelect.options.length) {
    await loadPipelines();
  }
  const targetPipelineId = currentPipelineId || pipelineEditorSelect.value;
  if (targetPipelineId) {
    pipelineEditorSelect.value = targetPipelineId;
    await loadPipelineSource(targetPipelineId);
  }
  pipelineEditorModal.hidden = false;
}

function closePipelineEditorModal() {
  pipelineEditorModal.hidden = true;
}

async function loadPipelineSource(pipelineId) {
  if (!pipelineId) return;

  pipelineEditorIsLoading = true;
  const data = await fetchJSON(`${API.pipelines}/${encodeURIComponent(pipelineId)}/source`);
  if (!data) {
    pipelineEditorIsLoading = false;
    return;
  }

  pipelineEditorCurrentId = data.id;
  pipelineEditorSelect.value = data.id;
  pipelineEditorPath.textContent = data.path || '';
  pipelineEditorTextarea.value = data.content || '';
  pipelineEditorLastSavedContent = data.content || '';
  pipelineEditorIsLoading = false;
  btnPipelineEditorSave.textContent = PIPELINE_EDITING_ENABLED ? 'Save Pipeline' : 'Read Only';
}

async function createPipelineFromEditor() {
  if (!PIPELINE_EDITING_ENABLED) return;
  const name = (newPipelineName.value || '').trim();
  if (!name) {
    updateStatus('error', 'Error', 'Enter a pipeline name first.');
    return;
  }

  btnCreatePipeline.disabled = true;
  const result = await fetchJSON(API.pipelines, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  btnCreatePipeline.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to create pipeline.');
    return;
  }

  newPipelineName.value = '';
  currentPipelineId = result.id;
  await loadPipelines();
  await loadPipelineSource(result.id);
  await loadPipeline(result.id);
  updateStatus('idle', 'Idle', `Created pipeline ${result.name}.`);
}

async function savePipelineSource() {
  if (!PIPELINE_EDITING_ENABLED) return;
  if (!pipelineEditorCurrentId) return;

  const content = pipelineEditorTextarea.value;
  if (content === pipelineEditorLastSavedContent) {
    btnPipelineEditorSave.textContent = 'Saved';
    return;
  }

  btnPipelineEditorSave.disabled = true;
  btnPipelineEditorSave.textContent = 'Saving...';
  const result = await fetchJSON(`${API.pipelines}/${encodeURIComponent(pipelineEditorCurrentId)}/source`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  btnPipelineEditorSave.disabled = false;

  if (!result || !result.ok) {
    btnPipelineEditorSave.textContent = 'Save Pipeline';
    updateStatus('error', 'Error', 'Failed to save pipeline file.');
    return;
  }

  pipelineEditorLastSavedContent = content;
  await loadPipelines();
  await loadPipeline(result.id);
  pipelineEditorCurrentId = result.id;
  pipelineEditorSelect.value = result.id;
  pipelineEditorPath.textContent = result.path || '';
  btnPipelineEditorSave.textContent = 'Saved';
  updateStatus('idle', 'Idle', `Saved pipeline ${result.name}.`);
}

function schedulePipelineEditorAutosave() {
  if (!PIPELINE_EDITING_ENABLED) return;
  if (pipelineEditorIsLoading) return;

  btnPipelineEditorSave.textContent = 'Save Pipeline';
  clearTimeout(pipelineEditorSaveTimeout);
  pipelineEditorSaveTimeout = setTimeout(() => {
    savePipelineSource();
  }, 700);
}

function openOutputModal() {
  const posterFilename = outputModal.dataset.posterFilename || currentPosterFilename;
  if (!posterFilename) return;
  currentPosterFilename = posterFilename;
  outputModal.dataset.posterFilename = posterFilename;

  const imgUrl = `/output/${encodeURIComponent(posterFilename)}`;
  outputModalBody.innerHTML = `<img src="${imgUrl}" alt="Generated poster preview">`;
  updateOutputModalNavigation();
  const item = libraryItems.find(entry => entry.poster_filename === posterFilename);
  const jobId = item?.job_json?.id || '';
  btnOutputReload.disabled = !item;
  btnOutputReprint.disabled = !jobId;
  outputModal.hidden = false;
}

function closeOutputModal() {
  outputModal.hidden = true;
}

async function reprintCurrentOutput() {
  const posterFilename = outputModal.dataset.posterFilename || currentPosterFilename;
  if (!posterFilename) return;
  const item = libraryItems.find(entry => entry.poster_filename === posterFilename);
  const jobId = item?.job_json?.id || '';
  if (!jobId) {
    updateStatus('error', 'Error', 'This library item does not have a job record to reprint from.');
    return;
  }
  await reprintJob(jobId, btnOutputReprint);
}

function openMetadataImportModal(item) {
  metadataImportModal.dataset.posterFilename = item?.poster_filename || '';
  metadataImportPipeline.checked = true;
  metadataImportInterpretation.checked = true;
  metadataImportConcepts.checked = true;
  metadataImportDescription.checked = true;
  metadataImportImagePrompt.checked = true;
  metadataImportImageModel.checked = true;
  metadataImportAspectRatio.checked = true;
  metadataImportModal.hidden = false;
}

function closeMetadataImportModal() {
  metadataImportModal.hidden = true;
  delete metadataImportModal.dataset.posterFilename;
}

async function applyMetadataImportSelection() {
  const posterFilename = metadataImportModal.dataset.posterFilename;
  if (!posterFilename) {
    closeMetadataImportModal();
    return;
  }

  const item = libraryItems.find(entry => entry.poster_filename === posterFilename);
  if (!item) {
    closeMetadataImportModal();
    updateStatus('error', 'Error', 'Could not find that library item.');
    return;
  }

  if (metadataImportPipeline.checked && item.pipeline_id) {
    await loadPipeline(item.pipeline_id);
  }
  if (metadataImportInterpretation.checked) {
    setPromptInterpValue(item.interpretation_prompt || getPromptInterpValue() || '');
  }
  if (metadataImportConcepts.checked) {
    extractedConcepts = item.extracted_concepts || '';
    renderPromptInterpEditor();
  }
  if (metadataImportImagePrompt.checked) {
    setPromptImageValue(item.image_generation_prompt || getPromptImageValue() || '');
  }
  if (metadataImportDescription.checked) {
    descriptionEditor.value = item.description || '';
    renderPromptImageEditor();
  }
  if (metadataImportImageModel.checked) {
    imageModel = item.image_model || imageModel || 'replicate:google/nano-banana-pro';
    settingsImageModel.value = imageModel;
  }
  if (metadataImportAspectRatio.checked) {
    syncAspectRatioOptions(imageModel, item.aspect_ratio || aspectRatioSelect.value || '3:4');
    aspectRatioSelect.value = item.aspect_ratio || aspectRatioSelect.value || '3:4';
  }

  showResults(item.description, item.poster_filename);
  loadedMetadataPosterFilename = item.poster_filename;
  renderLibrarySelectionState();
  descriptionEditor.readOnly = true;
  await persistOperationalConfig({ showErrorStatus: false });
  closeMetadataImportModal();
  updateStatus('complete', 'Library', `Imported selected metadata from ${item.poster_filename}`);
}

function updateOutputModalNavigation() {
  const posterFilename = outputModal.dataset.posterFilename || currentPosterFilename;
  const currentIndex = libraryItems.findIndex(item => item.poster_filename === posterFilename);
  const hasItems = currentIndex !== -1 && libraryItems.length > 1;
  btnOutputPrev.disabled = !hasItems;
  btnOutputNext.disabled = !hasItems;
}

function showPreviousOutput() {
  navigateOutputModal(-1);
}

function showNextOutput() {
  navigateOutputModal(1);
}

function navigateOutputModal(direction) {
  const posterFilename = outputModal.dataset.posterFilename || currentPosterFilename;
  if (!libraryItems.length || !posterFilename) return;

  const currentIndex = libraryItems.findIndex(item => item.poster_filename === posterFilename);
  if (currentIndex === -1) return;

  const nextIndex = (currentIndex + direction + libraryItems.length) % libraryItems.length;
  currentPosterFilename = libraryItems[nextIndex].poster_filename;
  outputModal.dataset.posterFilename = currentPosterFilename;
  openOutputModal();
}

async function saveSettings() {
  if (isBatchRunning()) return;
  const selectedDefault = settingsDefaultPipeline.value;
  if (!selectedDefault) return;

  defaultPipelineId = selectedDefault;
  httpAccessLogging = settingsHttpAccessLogging.checked;
  skipImageGeneration = settingsSkipImageGeneration.checked;

  btnSettingsSave.disabled = true;
  const result = await persistSettings({ closeModal: true, showSavedMessage: true });
  btnSettingsSave.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to save settings.');
    return;
  }

  await persistOperationalConfig({ showErrorStatus: false });
}

async function saveConfigSource() {
  if (isBatchRunning()) return;
  btnConfigSave.disabled = true;
  const result = await fetchJSON(API.configSource, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: settingsConfigEditor.value }),
  });
  btnConfigSave.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to save config.json.');
    return;
  }

  configSourceContent = result.content || settingsConfigEditor.value;
  settingsConfigEditor.value = configSourceContent;
  await loadSettings();
  await loadPipelines();
  updateStatus('idle', 'Idle', 'config.json saved.');
}

async function resetConfigSource() {
  if (isBatchRunning()) return;
  const confirmed = window.confirm(
    'Reset config.json to the built-in default version? This will overwrite the current config file.'
  );
  if (!confirmed) return;

  btnConfigReset.disabled = true;
  const result = await fetchJSON(API.configReset, {
    method: 'POST',
  });
  btnConfigReset.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to reset config.json.');
    return;
  }

  configSourceContent = result.content || '';
  settingsConfigEditor.value = configSourceContent;
  await loadSettings();
  await loadPipelines();
  updateStatus('idle', 'Idle', 'config.json reset to default.');
}

function buildSettingsPayload() {
  return {
    default_pipeline_id: defaultPipelineId || currentPipelineId || settingsDefaultPipeline.value,
    watcher_enabled: watcherEnabled,
    watched_folder: watchedFolder,
    printer_name: settingsPrinterName.value,
    send_to_printer: sendToPrinter,
    http_access_logging: httpAccessLogging,
    text_model: settingsTextModel.value,
    image_model: settingsImageModel.value,
    aspect_ratio: aspectRatioSelect.value,
    run_count: Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1)),
    encourage_variety_within_batches: encourageVarietyWithinBatchesCheckbox.checked,
    encourage_variety_across_session: encourageVarietyAcrossSessionCheckbox.checked,
    skip_image_generation: skipImageGeneration,
    layout: layoutSettings,
  };
}

async function persistSettings({ closeModal = false, showSavedMessage = false } = {}) {
  const payload = buildSettingsPayload();
  const result = await fetchJSON(API.settings, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!result || !result.ok) {
    return null;
  }

  defaultPipelineId = result.default_pipeline_id;
  availablePrinters = Array.isArray(result.available_printers) ? result.available_printers : availablePrinters;
  printerName = result.printer_name || '';
  sendToPrinter = Boolean(result.send_to_printer);
  httpAccessLogging = Boolean(result.http_access_logging);
  skipImageGeneration = Boolean(result.skip_image_generation);
  watcherEnabled = result.watcher_enabled !== false;
  watchedFolder = result.watched_folder || watchedFolder || '/watch';
  textModel = result.text_model || textModel;
  imageModel = result.image_model || imageModel;
  const aspectRatio = result.aspect_ratio || aspectRatioSelect.value || '3:4';
  const runCount = Math.max(1, Math.min(20, Number.parseInt(result.run_count || runCountInput.value || '1', 10) || 1));
  layoutSettings = { ...layoutSettings, ...(result.layout || {}) };
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  settingsDefaultPipeline.value = defaultPipelineId;
  settingsSendToPrinter.checked = sendToPrinter;
  watcherEnabledToggle.checked = watcherEnabled;
  watchedFolderInput.value = watchedFolder;
  renderPrinterOptions(printerName);
  settingsHttpAccessLogging.checked = httpAccessLogging;
  settingsSkipImageGeneration.checked = skipImageGeneration;
  applyLayoutSettings();
  syncAspectRatioOptions(imageModel, aspectRatio);
  aspectRatioSelect.value = aspectRatio;
  runCountInput.value = String(runCount);
  encourageVarietyWithinBatchesCheckbox.checked = Boolean(result.encourage_variety_within_batches);
  encourageVarietyAcrossSessionCheckbox.checked = Boolean(result.encourage_variety_across_session);
  syncRunOptions();

  if (closeModal) {
    closeSettingsModal();
  }
  if (showSavedMessage) {
    updateStatus('idle', 'Idle', 'Settings saved.');
  }

  return result;
}

function handleRunConfigChange() {
  if (isBatchRunning()) return;
  textModel = settingsTextModel.value;
  imageModel = settingsImageModel.value;
  syncAspectRatioOptions(imageModel, aspectRatioSelect.value || '3:4');
  syncRunOptions();
  clearTimeout(runConfigSaveTimeout);
  runConfigSaveTimeout = setTimeout(async () => {
    const result = await persistSettings();
    if (!result || !result.ok) {
      updateStatus('error', 'Error', 'Failed to save run configuration.');
      return;
    }
    await persistOperationalConfig({ showErrorStatus: false });
    updateStatus('idle', 'Idle', 'Run configuration updated.');
  }, 250);
}

function handleRunCountChange() {
  if (isBatchRunning()) return;
  syncRunOptions();
  clearTimeout(runConfigSaveTimeout);
  runConfigSaveTimeout = setTimeout(async () => {
    const result = await persistSettings();
    if (!result || !result.ok) {
      updateStatus('error', 'Error', 'Failed to save run configuration.');
      return;
    }
    await persistOperationalConfig({ showErrorStatus: false });
    updateStatus('idle', 'Idle', 'Run configuration updated.');
  }, 250);
}

function handleWatcherSettingsChange() {
  watcherEnabled = watcherEnabledToggle.checked;
  watchedFolder = (watchedFolderInput.value || '').trim() || '/watch';
  watchedFolderInput.value = watchedFolder;
  clearTimeout(watcherSettingsSaveTimeout);
  watcherSettingsSaveTimeout = setTimeout(async () => {
    const result = await persistSettings({ showSavedMessage: false });
    if (!result || !result.ok) {
      await loadSettings();
      updateStatus('error', 'Error', 'Failed to update watcher settings.');
      return;
    }
    await loadImages();
    updateStatus('idle', 'Idle', `Watcher settings updated. ${watcherEnabled ? 'Auto-processing is on.' : 'Auto-processing is off.'}`);
  }, 150);
}

async function handleDefaultPipelineChange() {
  if (isBatchRunning()) return;
  const selectedPipeline = settingsDefaultPipeline.value;
  if (!selectedPipeline) return;
  defaultPipelineId = selectedPipeline;
  currentPipelineId = selectedPipeline;
  pipelineSelect.value = selectedPipeline;
  await loadPipeline(selectedPipeline);
  const result = await persistSettings({ showSavedMessage: false });
  if (!result || !result.ok) {
    await loadSettings();
    updateStatus('error', 'Error', 'Failed to update default pipeline.');
    return;
  }
  await persistOperationalConfig({ showErrorStatus: false });
  updateStatus('idle', 'Idle', 'Default pipeline updated.');
}

function handlePrinterSettingsChange() {
  if (isBatchRunning()) return;
  sendToPrinter = settingsSendToPrinter.checked;
  printerName = settingsPrinterName.value || '';
  renderPrinterOptions(printerName);
  clearTimeout(runConfigSaveTimeout);
  runConfigSaveTimeout = setTimeout(async () => {
    const result = await persistSettings({ showSavedMessage: false });
    if (!result || !result.ok) {
      await loadSettings();
      updateStatus('error', 'Error', 'Failed to update printer settings.');
      return;
    }
    updateStatus('idle', 'Idle', 'Printer settings updated.');
  }, 150);
}

function handleSkipImageGenerationChange() {
  if (isBatchRunning()) return;
  skipImageGeneration = settingsSkipImageGeneration.checked;
  clearTimeout(runConfigSaveTimeout);
  runConfigSaveTimeout = setTimeout(async () => {
    const result = await persistSettings({ showSavedMessage: false });
    if (!result || !result.ok) {
      await loadSettings();
      updateStatus('error', 'Error', 'Failed to update skip-image-generation setting.');
      return;
    }
    await persistOperationalConfig({ showErrorStatus: false });
    updateStatus('idle', 'Idle', 'Skip image generation setting updated.');
  }, 150);
}

async function pickWatchedFolder() {
  if (isBatchRunning()) return;
  watchedFolderInput.disabled = true;
  const result = await fetchJSON(API.watchedFolderPick, { method: 'POST' });
  watchedFolderInput.disabled = false;
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to open the watched-folder chooser.');
    return;
  }
  if (result.cancelled) {
    return;
  }
  watchedFolder = result.watched_folder || watchedFolder || '/watch';
  watchedFolderInput.value = watchedFolder;
  handleWatcherSettingsChange();
}

async function handlePipelineSelectionChange() {
  if (isBatchRunning()) return;
  await loadPipeline(pipelineSelect.value);
  await persistOperationalConfig();
}

function handleOperationalConfigChange(event) {
  if (isBatchRunning()) return;
  syncRunOptions();
  clearTimeout(runConfigSaveTimeout);
  const isImmediate = event?.type === 'change';
  if (isImmediate) {
    persistOperationalConfig();
    return;
  }
  runConfigSaveTimeout = setTimeout(async () => {
    await persistOperationalConfig();
  }, 250);
}

function buildOperationalConfigPayload() {
  return {
    pipeline_id: currentPipelineId || pipelineSelect.value || defaultPipelineId,
    image_model: imageModel,
    aspect_ratio: aspectRatioSelect.value,
    run_count: Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1)),
    encourage_variety_within_batches: encourageVarietyWithinBatchesCheckbox.checked,
    encourage_variety_across_session: encourageVarietyAcrossSessionCheckbox.checked,
  };
}

async function persistOperationalConfig({ showErrorStatus = true } = {}) {
  imageModel = settingsImageModel.value || imageModel;
  const payload = buildOperationalConfigPayload();
  const result = await fetchJSON(API.runConfig, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!result || !result.ok) {
    if (showErrorStatus) {
      updateStatus('error', 'Error', 'Failed to update run configuration.');
    }
    return null;
  }

  currentPipelineId = result.pipeline_id || currentPipelineId;
  imageModel = result.image_model || imageModel;
  syncAspectRatioOptions(imageModel, result.aspect_ratio || aspectRatioSelect.value);
  aspectRatioSelect.value = result.aspect_ratio || aspectRatioSelect.value;
  runCountInput.value = String(result.run_count || 1);
  encourageVarietyWithinBatchesCheckbox.checked = Boolean(result.encourage_variety_within_batches);
  encourageVarietyAcrossSessionCheckbox.checked = Boolean(result.encourage_variety_across_session);
  syncRunOptions();
  return result;
}

async function exportLibrary() {
  btnLibraryExport.disabled = true;
  try {
    const response = await fetch(API.libraryExport);
    if (!response.ok) {
      throw new Error(`Export failed (${response.status})`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const disposition = response.headers.get('Content-Disposition') || '';
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
    const filename = filenameMatch?.[1] || 'library_export.zip';
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    updateStatus('idle', 'Idle', 'Library exported.');
  } catch (error) {
    updateStatus('error', 'Error', error.message || 'Failed to export library.');
  } finally {
    btnLibraryExport.disabled = false;
  }
}

async function importLibrary() {
  const file = libraryImportInput.files?.[0];
  if (!file) return;

  const confirmed = window.confirm(
    'Importing this archive will overwrite all current image and job data in the system. ' +
    'This will clear the jobs, watch, and output folders before restoring the archive. Continue?'
  );
  if (!confirmed) {
    libraryImportInput.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  btnLibraryImport.disabled = true;

  const result = await fetchJSON(API.libraryImport, {
    method: 'POST',
    body: formData,
  });

  btnLibraryImport.disabled = false;
  libraryImportInput.value = '';

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to import library.');
    return;
  }

  await loadLibrary();
  window.alert(`Restore complete. ${result.imported} file${result.imported === 1 ? '' : 's'} restored from the archive.`);
  updateStatus('idle', 'Idle', `Restored ${result.imported} file${result.imported === 1 ? '' : 's'} from the archive.`);
}

function openDebugModal() {
  renderDebugList();
  debugModal.hidden = false;
}

function closeDebugModal() {
  debugModal.hidden = true;
}

async function recordError(message, source = 'client') {
  await fetch(API.errors, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, source }),
  }).catch(() => null);
  await loadErrors();
}

async function clearErrors() {
  btnDebugClear.disabled = true;
  const result = await fetchJSON(API.errors, { method: 'DELETE' });
  btnDebugClear.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to clear errors.');
    return;
  }

  errorItems = [];
  renderDebugList();
}

function renderSystemLog() {
  const shouldStickToBottom = systemLogPinnedToBottom;
  if (!systemLogItems.length) {
    systemLogList.innerHTML = '<p class="empty-state">No system events yet.</p>';
    updateSystemLogStatus();
    return;
  }

  systemLogList.innerHTML = systemLogItems.map(item => {
    const time = escapeHtml(formatSystemLogTime(item.timestamp));
    const source = escapeHtml(item.source || 'system');
    const level = escapeHtml(item.level || 'info');
    const message = escapeHtml(item.message || '');
    return `
      <div class="system-log-entry level-${level}">
        <span class="system-log-time">${time}</span>
        <span class="system-log-source">${source}</span>
        <span class="system-log-message">${message}</span>
      </div>
    `;
  }).join('');

  if (shouldStickToBottom) {
    requestAnimationFrame(() => {
      systemLogList.scrollTop = systemLogList.scrollHeight;
    });
  }
  updateSystemLogStatus();
}

function toggleSystemLogPause() {
  systemLogPaused = !systemLogPaused;
  if (!systemLogPaused && pendingSystemLogItems.length) {
    systemLogItems = pendingSystemLogItems;
    pendingSystemLogItems = [];
    renderSystemLog();
  } else {
    updateSystemLogStatus();
  }
}

async function clearSystemLog() {
  btnSystemLogClear.disabled = true;
  const result = await fetchJSON(API.systemLog, { method: 'DELETE' });
  btnSystemLogClear.disabled = false;
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to clear system log.');
    return;
  }

  systemLogItems = [];
  pendingSystemLogItems = [];
  renderSystemLog();
  errorItems = [];
}

function jumpSystemLogToLatest() {
  systemLogPinnedToBottom = true;
  systemLogList.scrollTop = systemLogList.scrollHeight;
  updateSystemLogStatus();
}

function handleSystemLogScroll() {
  systemLogPinnedToBottom = isSystemLogNearBottom();
  updateSystemLogStatus();
}

function isSystemLogNearBottom() {
  const threshold = 24;
  return systemLogList.scrollHeight - systemLogList.scrollTop - systemLogList.clientHeight <= threshold;
}

function formatSystemLogTime(timestamp) {
  if (!timestamp) return '--:--:--';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function updateSystemLogStatus() {
  if (systemLogCollapsed) {
    btnSystemLogPause.textContent = systemLogPaused ? 'Resume' : 'Pause';
    btnSystemLogJump.hidden = true;
    return;
  }
  const pausedCount = pendingSystemLogItems.length > systemLogItems.length
    ? pendingSystemLogItems.length - systemLogItems.length
    : 0;
  if (systemLogPaused) {
    if (systemLogStatus) {
      systemLogStatus.textContent = pausedCount > 0 ? `Paused · ${pausedCount} new` : 'Paused';
    }
  } else if (systemLogPinnedToBottom) {
    if (systemLogStatus) {
      systemLogStatus.textContent = 'Live';
    }
  } else {
    if (systemLogStatus) {
      systemLogStatus.textContent = 'Reviewing older entries';
    }
  }
  btnSystemLogPause.textContent = systemLogPaused ? 'Resume' : 'Pause';
  btnSystemLogJump.hidden = systemLogPinnedToBottom && !systemLogPaused;
}

function renderJobBrowser() {
  const activeJob = getActiveJobRecord();
  renderUnifiedJobGrid(activeJob);
}

function getActiveJobRecord() {
  if (!activeJobId || !isBatchRunning()) {
    return null;
  }
  return jobItems.find(job => job.id === activeJobId) || null;
}

function renderUnifiedJobGrid(activeJob) {
  const previousJobs = jobItems.filter(job => {
    if (!job || !job.id || job.id === activeJob?.id) {
      return false;
    }
    return isTerminalJobStatus(job.status);
  });

  const cards = [];
  if (activeJob) {
    cards.push(renderJobCard(activeJob, { isActive: true, showReprint: false, showRequeue: false, showFeedback: false }));
  } else {
    cards.push(renderActiveJobPlaceholderCard());
  }
  cards.push(renderQueueCard());
  previousJobs.forEach(job => {
    cards.push(renderJobCard(job, {
      isActive: false,
      showRequeue: Array.isArray(job.source_images) && job.source_images.length > 0,
      showFeedback: Boolean(job.output_filename),
      showReprint: Boolean(job.output_filename),
    }));
  });

  jobBrowserGrid.innerHTML = cards.join('');
}

function renderQueueCard() {
  const queuedItems = Array.isArray(queueStatus.queued_items) ? queueStatus.queued_items : [];
  const currentItem = queueStatus.current_item;
  const queueCountLabel = queueStatus.queued_count === 1 ? '1 queued item' : `${queueStatus.queued_count} queued items`;
  const currentClaimLabel = currentItem?.job_id
    ? `${escapeHtml(currentItem.pipeline_name || currentItem.pipeline_id || 'Queued job')} (${escapeHtml(currentItem.filename || 'No filename')})`
    : 'None';
  const queuedList = queuedItems.length
    ? queuedItems.map(item => `
        <div class="queue-item">
          <div class="queue-item-main">
            <div class="queue-item-title">${escapeHtml(item.pipeline_name || item.pipeline_id || 'Queued job')}</div>
            <div class="queue-item-meta">${escapeHtml(item.filename || (Array.isArray(item.source_images) ? item.source_images[0] || '' : '') || 'No filename')}</div>
          </div>
          <button class="btn-secondary btn-queue-remove" type="button" data-queue-action="remove" data-job-id="${escapeHtml(item.job_id || '')}" ${item.job_id ? '' : 'disabled'}>Remove</button>
        </div>
      `).join('')
    : '<div class="queue-empty">Queue is empty.</div>';

  return `
    <article class="job-item job-item-queue">
      <div class="job-item-header">
        <span class="job-status ${queueStatus.worker_running ? 'job-status-complete' : 'job-status-error'}">${queueStatus.worker_running ? 'Worker Running' : 'Worker Stopped'}</span>
        <span class="job-trigger">${escapeHtml(queueCountLabel)}</span>
      </div>
      <div class="job-title">Queue</div>
      <div class="job-meta">Current claim: ${currentClaimLabel}</div>
      <div class="queue-list">${queuedList}</div>
      <div class="job-actions">
        <button class="btn-secondary" type="button" data-queue-action="restart">Restart Queue</button>
      </div>
    </article>
  `;
}

function renderActiveJobPlaceholderCard() {
  return `
    <article class="job-item job-item-placeholder">
      <div class="job-title">Active job will be shown here</div>
      <div class="job-meta">Watcher-triggered and manual jobs appear here while they are running.</div>
    </article>
  `;
}

function renderJobCard(job, { isActive = false, showReprint = false, showRequeue = false, showFeedback = false } = {}) {
  const status = escapeHtml(formatJobStatus(job.status));
  const triggerLabel = escapeHtml(formatJobTrigger(job.trigger));
  const title = escapeHtml(job.pipeline_name || job.pipeline_id || 'Untitled job');
  const createdAt = formatJobCardDateTime(job.created_at);
  const sourceImages = Array.isArray(job.source_images) ? job.source_images : [];
  const primarySource = sourceImages[0] || '';
  const detailMessage = getJobDetailMessage(job);
  const generationProgress = isActive ? getGenerationProgress(job) : null;

  return `
    <article class="job-item ${isActive ? 'is-active' : ''}" data-job-id="${escapeHtml(job.id)}">
      <div class="job-item-header">
        <span class="job-status job-status-${escapeHtml(job.status || 'unknown')}">${status}</span>
        <span class="job-trigger">${triggerLabel}</span>
      </div>
      <div class="job-meta job-meta-date">${createdAt}</div>
      <div class="job-title">${title}</div>
      ${detailMessage ? `<div class="job-meta">${escapeHtml(detailMessage)}</div>` : ''}
      ${generationProgress ? renderGenerationProgress(generationProgress) : ''}
      <div class="job-actions">
        <button class="btn-secondary" type="button" data-job-action="json" data-job-id="${escapeHtml(job.id)}">JSON</button>
        ${isActive
          ? `<button class="btn-secondary" type="button" data-job-action="input" data-job-id="${escapeHtml(job.id)}" ${primarySource ? '' : 'disabled'}>Input</button>`
          : `<div class="job-action-combo ${primarySource ? '' : 'is-disabled'}" data-job-preview="input" data-job-id="${escapeHtml(job.id)}">
              <button class="job-action-main" type="button" data-job-action="input" data-job-id="${escapeHtml(job.id)}" ${primarySource ? '' : 'disabled'}>Input</button>
              <div class="job-action-links">
                ${showRequeue
                  ? `<button class="job-action-link" type="button" data-job-action="requeue" data-job-id="${escapeHtml(job.id)}">RQ</button>`
                  : '<span class="job-action-link is-disabled">RQ</span>'}
              </div>
            </div>`}
        ${isActive
          ? `<button class="btn-secondary" type="button" data-job-action="output" data-job-id="${escapeHtml(job.id)}" ${job.output_filename ? '' : 'disabled'}>Output</button>`
          : `<div class="job-action-combo ${job.output_filename ? '' : 'is-disabled'}" data-job-preview="output" data-job-id="${escapeHtml(job.id)}">
              <button class="job-action-main" type="button" data-job-action="output" data-job-id="${escapeHtml(job.id)}" ${job.output_filename ? '' : 'disabled'}>Output</button>
              <div class="job-action-links">
                ${showFeedback
                  ? `<button class="job-action-link" type="button" data-job-action="feedback" data-job-id="${escapeHtml(job.id)}">Q</button>`
                  : '<span class="job-action-link is-disabled">Q</span>'}
                <span class="job-action-separator">|</span>
                ${showReprint
                  ? `<button class="job-action-link" type="button" data-job-action="reprint" data-job-id="${escapeHtml(job.id)}">RP</button>`
                  : '<span class="job-action-link is-disabled">RP</span>'}
              </div>
            </div>`}
        ${isActive
          ? `<button class="btn-secondary" type="button" data-job-action="cancel" data-job-id="${escapeHtml(job.id)}" ${pipelineStatus === 'cancelling' ? 'disabled' : ''}>${pipelineStatus === 'cancelling' ? 'Cancelling...' : 'Cancel'}</button>`
          : ''}
      </div>
    </article>
  `;
}

function getGenerationProgress(job) {
  if (String(job?.status || '') !== 'generating') {
    return null;
  }

  const startedAt = String(job?.generation_started_at || '').trim();
  const estimateSeconds = Number(job?.generation_estimate_seconds);
  if (!startedAt || !Number.isFinite(estimateSeconds) || estimateSeconds <= 0) {
    return null;
  }

  const startedMs = Date.parse(startedAt);
  if (Number.isNaN(startedMs)) {
    return null;
  }

  const elapsedSeconds = Math.max(0, (Date.now() - startedMs) / 1000);
  const progress = Math.max(0, Math.min(1, elapsedSeconds / estimateSeconds));
  return {
    progressPercent: progress * 100,
    estimateLabel: Math.round(estimateSeconds),
    elapsedLabel: Math.round(elapsedSeconds),
  };
}

function renderGenerationProgress(progress) {
  return `
    <div class="job-progress">
      <div class="job-progress-meta">Estimated image generation time: ~${escapeHtml(String(progress.estimateLabel))}s · elapsed ${escapeHtml(String(progress.elapsedLabel))}s</div>
      <div class="job-progress-bar" aria-hidden="true">
        <div class="job-progress-fill" style="width: ${progress.progressPercent.toFixed(1)}%"></div>
      </div>
    </div>
  `;
}

function formatJobStatus(status) {
  const labels = {
    extracting_concepts: 'Extracting Concepts',
    interpreting: 'Interpreting',
    generating: 'Generating',
    downloading: 'Saving Output',
    printing: 'Sending to Printer',
    cancelling: 'Cancelling',
    complete: 'Complete',
    cancelled: 'Cancelled',
    error: 'Error',
    queued: 'Queued',
  };
  return labels[status] || capitalise(String(status || 'unknown').replaceAll('_', ' '));
}

function formatJobTrigger(trigger) {
  if (trigger === 'watch') return 'Trigger: Watch';
  if (trigger === 'manual') return 'Trigger: Manual';
  return 'Trigger: Job';
}

function getJobDetailMessage(job) {
  const settingsSnapshot = job.settings_snapshot || {};
  const runCount = Math.max(1, Number.parseInt(settingsSnapshot.run_count || '1', 10) || 1);
  const runLabel = runCount === 1 ? '1 run' : `${runCount} runs`;
  const skipImageGeneration = Boolean(settingsSnapshot.skip_image_generation);
  const sendToPrinter = Boolean(settingsSnapshot.send_to_printer);
  const printStatus = String(job.print_status || '').trim();
  const status = String(job.status || '').trim();
  const message = String(job.message || '').trim();

  if (status === 'complete') {
    if (skipImageGeneration) {
      return runCount === 1
        ? 'Job complete with placeholder output because image generation was skipped'
        : `Job complete after ${runLabel} with placeholder outputs because image generation was skipped`;
    }
    if (sendToPrinter && printStatus === 'printed') {
      return runCount === 1
        ? 'Job complete and was sent to print'
        : `Job complete after ${runLabel}, sent to print`;
    }
    if (sendToPrinter && printStatus === 'error') {
      return runCount === 1
        ? 'Job complete but print handoff failed'
        : `Job complete after ${runLabel}, but print handoff failed`;
    }
    if (sendToPrinter && printStatus === 'skipped') {
      return runCount === 1
        ? 'Job complete without print handoff'
        : `Job complete after ${runLabel} without print handoff`;
    }
    if (!sendToPrinter) {
      return runCount === 1
        ? 'Job complete without printing'
        : `Job complete after ${runLabel} without printing`;
    }
    return runCount === 1 ? 'Job complete' : `Job complete after ${runLabel}`;
  }

  if (status === 'cancelled') {
    return runCount === 1 ? 'Job was cancelled' : `Job was cancelled during ${runLabel}`;
  }

  if (status === 'error') {
    if (message.startsWith('Error:')) {
      return message;
    }
    return runCount === 1 ? 'Job failed' : `Job failed during ${runLabel}`;
  }

  if (!message) return '';

  const redundantMessages = new Set([
    'Cancelled',
    'Job complete',
    'Saved output sent to print queue',
  ]);
  if (redundantMessages.has(message)) {
    return '';
  }
  return message;
}

function isTerminalJobStatus(status) {
  return ['complete', 'cancelled', 'error'].includes(status);
}

function formatJobDateTime(timestamp) {
  if (!timestamp) return 'Unknown time';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatJobCardDateTime(timestamp) {
  if (!timestamp) return 'Unknown time';
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return 'Unknown time';

  const time = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
  const day = new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
  }).format(date);
  return `<strong>${escapeHtml(time)}</strong>, ${escapeHtml(day)}`;
}

function handleJobBrowserClick(event) {
  const queueActionButton = event.target.closest('[data-queue-action]');
  if (queueActionButton) {
    const queueAction = queueActionButton.dataset.queueAction;
    const queuedJobId = queueActionButton.dataset.jobId;
    if (queueAction === 'restart') {
      restartQueueWorker(queueActionButton);
      return;
    }
    if (queueAction === 'remove' && queuedJobId) {
      removeQueuedJob(queuedJobId, queueActionButton);
      return;
    }
  }

  const actionButton = event.target.closest('[data-job-action]');
  if (!actionButton) return;
  const jobId = actionButton.dataset.jobId;
  const action = actionButton.dataset.jobAction;
  if (!jobId || !action) return;

  if (action === 'json') {
    openJobJsonModal(jobId);
    return;
  }
  if (action === 'input') {
    openJobInputPreview(jobId);
    return;
  }
  if (action === 'output') {
    openJobOutputPreview(jobId);
    return;
  }
  if (action === 'requeue') {
    requeueJob(jobId, actionButton);
    return;
  }
  if (action === 'feedback') {
    feedbackJob(jobId, actionButton);
    return;
  }
  if (action === 'reprint') {
    reprintJob(jobId, actionButton);
    return;
  }
  if (action === 'cancel') {
    cancelPipeline();
  }
}

function handleJobBrowserHoverStart(event) {
  const previewTarget = event.target.closest('[data-job-preview], [data-job-action="input"], [data-job-action="output"]');
  if (!previewTarget || !jobBrowserGrid.contains(previewTarget)) {
    return;
  }
  if (previewTarget.classList?.contains('is-disabled')) {
    return;
  }
  const action = previewTarget.dataset.jobPreview || previewTarget.dataset.jobAction;
  const jobId = previewTarget.dataset.jobId;
  if (!jobId || (action !== 'input' && action !== 'output')) return;
  if ('disabled' in previewTarget && previewTarget.disabled) return;

  const preview = getJobHoverPreviewData(jobId, action);
  if (!preview) {
    return;
  }

  const hoverKey = `${jobId}:${action}`;
  activeJobHoverKey = hoverKey;
  jobHoverPreviewTitle.textContent = preview.title;
  jobHoverPreviewImage.src = preview.src;
  jobHoverPreviewImage.alt = preview.alt;
  positionJobHoverPreview(event.clientX, event.clientY);
  jobHoverPreview.hidden = false;
}

function handleJobBrowserHoverMove(event) {
  if (jobHoverPreview.hidden) {
    return;
  }
  positionJobHoverPreview(event.clientX, event.clientY);
}

function handleJobBrowserHoverEnd(event) {
  const previewTarget = event.target.closest('[data-job-preview], [data-job-action="input"], [data-job-action="output"]');
  if (!previewTarget || !jobBrowserGrid.contains(previewTarget)) {
    return;
  }
  const action = previewTarget.dataset.jobPreview || previewTarget.dataset.jobAction;
  const jobId = previewTarget.dataset.jobId;
  if (!jobId || (action !== 'input' && action !== 'output')) {
    return;
  }

  const nextHoverButton = event.relatedTarget instanceof Element
    ? event.relatedTarget.closest('[data-job-preview], [data-job-action="input"], [data-job-action="output"]')
    : null;
  if (
    nextHoverButton
    && jobBrowserGrid.contains(nextHoverButton)
    && nextHoverButton.dataset.jobId === jobId
    && (nextHoverButton.dataset.jobPreview || nextHoverButton.dataset.jobAction) === action
  ) {
    return;
  }

  hideJobHoverPreview();
}

function getJobHoverPreviewData(jobId, action) {
  const job = jobItems.find(item => item.id === jobId);
  if (!job) {
    return null;
  }

  if (action === 'input') {
    const sourceImages = Array.isArray(job.source_images) ? job.source_images : [];
    const filename = sourceImages[0];
    if (!filename) {
      return null;
    }
    return {
      title: `Source Image · ${filename}`,
      src: `/api/watch/${encodeURIComponent(filename)}`,
      alt: filename,
    };
  }

  if (action === 'output') {
    const filename = job.output_filename;
    if (!filename) {
      return null;
    }
    return {
      title: `Generated Output · ${filename}`,
      src: `/output/${encodeURIComponent(filename)}`,
      alt: filename,
    };
  }

  return null;
}

function positionJobHoverPreview(clientX, clientY) {
  const offset = 18;
  const width = jobHoverPreview.offsetWidth || Math.min(window.innerWidth * 0.44, 608);
  const height = jobHoverPreview.offsetHeight || Math.min(window.innerHeight * 0.62, 520);
  let left = clientX + offset;
  let top = clientY + offset;

  if (left + width > window.innerWidth - 12) {
    left = Math.max(12, clientX - width - offset);
  }
  if (top + height > window.innerHeight - 12) {
    top = Math.max(12, window.innerHeight - height - 12);
  }

  jobHoverPreview.style.left = `${left}px`;
  jobHoverPreview.style.top = `${top}px`;
}

function hideJobHoverPreview() {
  activeJobHoverKey = null;
  jobHoverPreview.hidden = true;
  jobHoverPreviewImage.removeAttribute('src');
}

async function openJobJsonModal(jobId) {
  const job = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}`);
  if (!job) return;
  jobJsonContent.textContent = JSON.stringify(job, null, 2)
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t');
  jobJsonModal.hidden = false;
}

function closeJobJsonModal() {
  jobJsonModal.hidden = true;
}

async function openJobInputPreview(jobId) {
  const job = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}`);
  if (!job) return;
  const sourceImages = Array.isArray(job.source_images) ? job.source_images : [];
  const filename = sourceImages[0];
  if (!filename) {
    updateStatus('error', 'Error', 'This job does not have a source image to preview.');
    return;
  }
  openAssetPreviewModal(`Source Image · ${filename}`, `/api/watch/${encodeURIComponent(filename)}`, filename);
}

async function openJobOutputPreview(jobId) {
  const job = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}`);
  if (!job) return;
  const filename = job.output_filename;
  if (!filename) {
    updateStatus('error', 'Error', 'This job does not have a generated output yet.');
    return;
  }
  openAssetPreviewModal(`Generated Output · ${filename}`, `/output/${encodeURIComponent(filename)}`, filename);
}

function openAssetPreviewModal(title, src, alt) {
  assetPreviewTitle.textContent = title;
  assetPreviewBody.innerHTML = `<img src="${src}" alt="${escapeHtml(alt || title)}">`;
  assetPreviewModal.hidden = false;
}

function closeAssetPreviewModal() {
  assetPreviewModal.hidden = true;
}

async function reprintJob(jobId, button) {
  if (button) {
    button.disabled = true;
  }
  const result = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}/reprint`, {
    method: 'POST',
  });
  if (button) {
    button.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to reprint this job.');
    return;
  }

  await loadJobs();
  await loadQueueStatus();
  await loadSystemLog();
  updateStatus('idle', 'Idle', 'Saved output sent to print queue.');
}

async function removeQueuedJob(jobId, button) {
  if (button) {
    button.disabled = true;
  }
  const result = await fetchJSON(`${API.queue}/${encodeURIComponent(jobId)}`, {
    method: 'DELETE',
  });
  if (button) {
    button.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to remove queued job.');
    return;
  }
  await loadQueueStatus();
  await loadJobs();
  updateStatus('idle', 'Idle', 'Removed queued job.');
}

async function restartQueueWorker(button) {
  if (button) {
    button.disabled = true;
  }
  const result = await fetchJSON(`${API.queue}/restart`, {
    method: 'POST',
  });
  if (button) {
    button.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to restart queue worker.');
    return;
  }
  await loadQueueStatus();
  updateStatus('idle', 'Idle', 'Queue worker restarted.');
}

async function requeueJob(jobId, button) {
  if (button) {
    button.disabled = true;
  }
  const result = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}/requeue`, {
    method: 'POST',
  });
  if (button) {
    button.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to requeue this job.');
    return;
  }

  await loadImages();
  await loadSystemLog();
  const count = Array.isArray(result.filenames) ? result.filenames.length : 0;
  updateStatus('idle', 'Idle', `Requeued ${count} source image${count === 1 ? '' : 's'} back into the watch folder.`);
}

async function feedbackJob(jobId, button) {
  if (button) {
    button.disabled = true;
  }
  const result = await fetchJSON(`${API.jobs}/${encodeURIComponent(jobId)}/feedback`, {
    method: 'POST',
  });
  if (button) {
    button.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to feed this output back into the watch folder.');
    return;
  }

  await loadImages();
  await loadSystemLog();
  updateStatus('idle', 'Idle', 'Generated output copied back into the watch folder.');
}

// --- Camera ---
async function toggleCamera() {
  if (isBatchRunning()) return;
  if (cameraStream) {
    stopCamera();
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    setCameraStatus('Camera capture is not supported in this browser.');
    return;
  }

  btnCameraStart.disabled = true;
  setCameraStatus('Requesting camera access...');

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
      audio: false,
    });
    cameraVideo.srcObject = cameraStream;
    cameraVideo.hidden = false;
    cameraPlaceholder.hidden = true;
    btnCameraCapture.disabled = false;
    btnCameraStart.textContent = 'Stop Camera';
    setCameraStatus('Camera is live. Capture saves a still image into the watch folder.');
  } catch (error) {
    console.error('Camera error:', error);
    setCameraStatus('Could not access the camera. Check browser permissions and try again.');
  } finally {
    btnCameraStart.disabled = false;
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  cameraVideo.srcObject = null;
  cameraVideo.hidden = true;
  cameraPlaceholder.hidden = false;
  btnCameraCapture.disabled = true;
  btnCameraStart.textContent = 'Start Camera';
  setCameraStatus('Camera stopped.');
}

async function captureFrame() {
  if (isBatchRunning()) return;
  if (!cameraStream || cameraVideo.videoWidth === 0 || cameraVideo.videoHeight === 0) {
    setCameraStatus('Camera is not ready yet.');
    return;
  }

  btnCameraCapture.disabled = true;
  setCameraStatus('Saving captured image to watch folder...');

  const canvas = document.createElement('canvas');
  canvas.width = cameraVideo.videoWidth;
  canvas.height = cameraVideo.videoHeight;
  const context = canvas.getContext('2d');
  context.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);

  const result = await fetchJSON(API.capture, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image: canvas.toDataURL('image/png') }),
  });

  if (!result || !result.ok) {
    btnCameraCapture.disabled = false;
    setCameraStatus('Capture failed. Try again.');
    return;
  }

  setCameraStatus(`Saved ${result.filename} to the watch folder.`);
  await loadImages();
  selectedImages.add(result.filename);
  renderSelection();
  btnCameraCapture.disabled = false;
}

async function deleteImage(filename) {
  if (isBatchRunning()) return;
  const confirmed = window.confirm(`Delete ${filename} from the watch folder?`);
  if (!confirmed) return;

  const result = await fetchJSON(`${API.images}/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to delete image.');
    return;
  }

  selectedImages.delete(filename);
  await loadImages();
  updateStatus('idle', 'Deleted', `${filename} removed from watch folder.`);
}

// --- Run pipeline ---
async function runPipeline() {
  if (selectedImages.size === 0) {
    updateStatus('error', 'Error', 'Select at least one image to run the pipeline.');
    return;
  }
  const allowedAspectRatios = MODEL_ASPECT_RATIOS[imageModel] || ['1:1', '3:4', '4:3', '9:16', '16:9'];
  const selectedAspectRatio = aspectRatioSelect.value;
  if (!selectedAspectRatio || !allowedAspectRatios.includes(selectedAspectRatio)) {
    updateStatus('error', 'Error', 'Select a valid aspect ratio before running the pipeline.');
    syncAspectRatioOptions(imageModel);
    return;
  }
  btnRun.disabled = true;
  btnRun.textContent = 'Running...';

  const result = await fetchJSON(API.run, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filenames: Array.from(selectedImages),
      pipeline_id: currentPipelineId,
      interpretation_prompt: getPromptInterpValue(),
      image_generation_prompt: promptImage.value,
      image_model: imageModel,
      aspect_ratio: aspectRatioSelect.value,
      run_count: Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1)),
      rerun_interpretation: true,
      encourage_variety_within_batches: encourageVarietyWithinBatchesCheckbox.checked,
      encourage_variety_across_session: encourageVarietyAcrossSessionCheckbox.checked,
    }),
  });
  if (!result || !result.ok) {
    btnRun.disabled = false;
    btnRun.textContent = 'Run Pipeline';
    updateStatus('error', 'Error', result?.detail || 'Failed to start pipeline');
    return;
  }

  startPolling();
}

// --- Poll status ---
function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(pollStatus, 1500);
  pollStatus(); // immediate first poll
}

async function pollStatus() {
  const data = await fetchJSON(API.status);
  if (!data) return;

  const { status, message, description, poster_filename, error } = data;
  if (data.pipeline_id && data.pipeline_id !== currentPipelineId) {
    await loadPipeline(data.pipeline_id);
  }

  applyStatusState(data);

  if (poster_filename && poster_filename !== lastLibraryPosterFilename) {
    lastLibraryPosterFilename = poster_filename;
    showResults(description, poster_filename);
    loadLibrary();
  }

  if (status === 'complete') {
    stopPolling();
    loadLibrary();
    loadJobs();
  } else if (status === 'cancelled') {
    stopPolling();
    loadJobs();
  } else if (status === 'error') {
    stopPolling();
    loadErrors();
    loadJobs();
  }
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  btnRun.textContent = 'Run Pipeline';
  updateRunButtonState();
}

// --- UI updates ---
function updateStatus(state, text, message) {
  if (statusDot) {
    statusDot.className = 'status-dot ' + (state === 'working' ? 'working' : state);
  }
  if (statusText) {
    statusText.textContent = text;
  }
  if (statusMessage) {
    statusMessage.textContent = message || '';
  }
}

function showResults(description, posterFilename) {
  if (description) {
    descriptionEditor.value = description;
    renderPromptImageEditor();
  }

  if (posterFilename) {
    currentPosterFilename = posterFilename;
  }
}

function previewLibraryItem(filename) {
  const item = libraryItems.find(entry => entry.poster_filename === filename);
  if (!item) return;
  currentPosterFilename = item.poster_filename;
  outputModal.dataset.posterFilename = item.poster_filename;
  openOutputModal();
}

async function reloadCurrentPosterMetadata() {
  const posterFilename = outputModal.dataset.posterFilename || currentPosterFilename;
  if (!posterFilename) return;
  const item = libraryItems.find(entry => entry.poster_filename === posterFilename);
  if (!item) {
    updateStatus('error', 'Error', 'Could not find metadata for this library item.');
    return;
  }
  closeOutputModal();
  openMetadataImportModal(item);
}

function renderLibrarySelectionState() {
  libraryGrid.querySelectorAll('.library-item').forEach(button => {
    button.classList.toggle('is-loaded', button.dataset.filename === loadedMetadataPosterFilename);
  });
}

function capitalise(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function setCameraStatus(message) {
  cameraStatus.textContent = message;
}

function updateVarietyGuidanceEditorHeight() {
  if (!meaningfulDifferenceEditor) return;
  const hasContent = Boolean((meaningfulDifferenceEditor.value || '').trim());
  meaningfulDifferenceEditor.classList.toggle('is-empty', !hasContent);
  meaningfulDifferenceEditor.style.height = 'auto';
  const minimumHeight = hasContent ? 88 : 52;
  meaningfulDifferenceEditor.style.height = `${Math.max(minimumHeight, meaningfulDifferenceEditor.scrollHeight)}px`;
}

function buildInjectedVarietyGuidancePreview() {
  const buildSection = text => [
    '### Variety Guidance',
    'Avoid these concepts:',
    text.trim(),
  ].join('\n');

  const sections = [];
  if ((batchVarietyText || '').trim()) {
    sections.push(buildSection(batchVarietyText));
  }
  if ((sessionVarietyText || '').trim()) {
    sections.push(buildSection(sessionVarietyText));
  }
  if (sections.length) {
    return sections.join('\n\n');
  }
  if ((meaningfulDifferenceText || '').trim()) {
    return buildSection(meaningfulDifferenceText);
  }
  return '';
}

function applyStatusState(data) {
  const { status, message, description, poster_filename, error } = data;
  pipelineStatus = status || 'idle';
  activeJobId = data?.job_id || null;
  interpretationHistory = Array.isArray(data.job_interpretation_history) ? data.job_interpretation_history : [];
  extractedConcepts = typeof data.extracted_concepts === 'string' ? data.extracted_concepts : extractedConcepts;
  meaningfulDifferenceText = typeof data.variety_guidance_text === 'string'
    ? data.variety_guidance_text
    : (typeof data.meaningful_difference_text === 'string'
        ? data.meaningful_difference_text
        : '');
  batchVarietyText = typeof data.job_variety_text === 'string' ? data.job_variety_text : '';
  sessionVarietyText = typeof data.session_variety_text === 'string' ? data.session_variety_text : '';
  meaningfulDifferenceEditor.value = meaningfulDifferenceText || '';
  updateVarietyGuidanceEditorHeight();
  if (typeof data.encourage_variety_within_batches === 'boolean') {
    encourageVarietyWithinBatchesCheckbox.checked = data.encourage_variety_within_batches;
  }
  if (typeof data.encourage_variety_across_session === 'boolean') {
    encourageVarietyAcrossSessionCheckbox.checked = data.encourage_variety_across_session;
  }
  if (typeof data.send_to_printer === 'boolean') {
    sendToPrinter = data.send_to_printer;
    settingsSendToPrinter.checked = sendToPrinter;
  }
  if (data.pipeline_id) {
    pipelineSelect.value = data.pipeline_id;
  }

  if (description) {
    descriptionEditor.value = description;
    renderPromptImageEditor();
  }
  if (data.image_model) {
    imageModel = data.image_model;
    settingsImageModel.value = imageModel;
    syncAspectRatioOptions(imageModel, data.aspect_ratio || aspectRatioSelect.value);
  }

  if (['interpreting', 'generating', 'downloading', 'printing', 'cancelling'].includes(status)) {
    updateStatus('working', capitalise(status), message);
    descriptionEditor.readOnly = true;
  } else if (status === 'cancelled') {
    updateStatus('idle', 'Cancelled', message || 'Cancelled');
    descriptionEditor.readOnly = true;
  } else if (status === 'complete') {
    updateStatus('complete', 'Finished', message);
    descriptionEditor.readOnly = true;
  } else if (status === 'error') {
    updateStatus('error', 'Error', error || message);
    descriptionEditor.readOnly = true;
  } else {
    updateStatus('idle', 'Idle', '');
    descriptionEditor.readOnly = true;
  }

  syncRunOptions();
  renderPromptInterpEditor();
  updateRunButtonState();
  updateRunConfigInteractivity();
  updateCancelButton();
  updateStageHighlights(data);
  renderJobBrowser();
}

function isBatchStatus(status) {
  return ['interpreting', 'generating', 'downloading', 'printing', 'cancelling'].includes(status);
}

function updateStageHighlights(data) {
  const { status, description } = data;
  const stages = [stageInput, stageInterpretation, stageMeaningfulDifference, stageDescription, stageImagePrompt];
  stages.forEach(stage => {
    stage.classList.remove('is-active', 'is-complete');
  });

  if (status === 'idle') {
    stageInput.classList.add('is-active');
    return;
  }

  stageInput.classList.add('is-complete');

  if (status === 'interpreting') {
    stageInterpretation.classList.add('is-active');
    if (meaningfulDifferenceText) {
      stageMeaningfulDifference.classList.add('is-complete');
    }
    return;
  }

  stageInterpretation.classList.add('is-complete');
  if (meaningfulDifferenceText) {
    stageMeaningfulDifference.classList.add('is-complete');
  }

  if (['generating', 'downloading', 'printing', 'complete'].includes(status)) {
    if (description) {
      stageDescription.classList.add(status === 'generating' ? 'is-active' : 'is-complete');
    }
    if (status === 'generating' || status === 'downloading' || status === 'printing') {
      stageImagePrompt.classList.add('is-active');
    } else {
      stageDescription.classList.add('is-complete');
      stageImagePrompt.classList.add('is-complete');
    }
  }

  if (status === 'error') {
    if (description) {
      stageDescription.classList.add('is-complete');
      stageImagePrompt.classList.add('is-active');
    } else {
      stageInterpretation.classList.add('is-active');
    }
  }
}

function toggleImageSelection(filename) {
  if (selectedImages.has(filename)) {
    selectedImages.delete(filename);
  } else {
    selectedImages.add(filename);
  }
  renderSelection();
}

function handleImageGridClick(event) {
  if (isBatchRunning()) return;
  const deleteButton = event.target.closest('.thumb-delete');
  if (deleteButton) {
    event.preventDefault();
    event.stopPropagation();
    deleteImage(deleteButton.dataset.deleteFilename);
    return;
  }

  const thumbButton = event.target.closest('.image-thumb');
  if (!thumbButton || !imagePickerGrid.contains(thumbButton)) return;
  toggleImageSelection(thumbButton.dataset.filename);
}

function selectAllImages() {
  images.forEach(image => selectedImages.add(image.filename));
  renderSelection();
}

function clearSelection() {
  selectedImages.clear();
  renderSelection();
}

function syncSelectionWithAvailableImages() {
  const available = new Set(images.map(image => image.filename));
  for (const filename of selectedImages) {
    if (!available.has(filename)) {
      selectedImages.delete(filename);
    }
  }
  if (images.length > 0 && selectedImages.size === 0) {
    selectedImages.add(images[0].filename);
  }
}

function renderSelection() {
  imagePickerGrid.querySelectorAll('.image-thumb').forEach(button => {
    const isSelected = selectedImages.has(button.dataset.filename);
    button.classList.toggle('selected', isSelected);
    button.dataset.runBlocked = isBatchRunning() ? 'true' : 'false';
    button.classList.toggle('is-run-blocked', isBatchRunning());
    const badge = button.querySelector('.thumb-check');
    if (badge) {
      badge.textContent = isSelected ? 'Selected' : 'Select';
    }
  });
  updateSelectionSummary();
  updateRunButtonState();
}

function updateSelectionSummary() {
  selectionCount.textContent = `${selectedImages.size} selected`;
}

function syncAspectRatioOptions(modelId, preferredValue = null) {
  const allowed = MODEL_ASPECT_RATIOS[modelId] || ['1:1', '3:4', '4:3', '9:16', '16:9'];
  const fallback = allowed.includes('3:4') ? '3:4' : allowed[0];
  const currentValue = aspectRatioSelect.value;
  const selected = allowed.includes(preferredValue)
    ? preferredValue
    : (allowed.includes(currentValue) ? currentValue : fallback);

  aspectRatioSelect.innerHTML = allowed.map(value => `
    <option value="${value}">${value}</option>
  `).join('');
  aspectRatioSelect.value = selected;
  if (!aspectRatioSelect.value && allowed.length > 0) {
    aspectRatioSelect.value = allowed[0];
  }
}

function updateRunButtonState() {
  const running = isBatchRunning();
  btnRun.disabled = selectedImages.size === 0 || running;
  btnRun.dataset.runBlocked = running ? 'true' : 'false';
  btnRun.classList.toggle('is-run-blocked', running);
  btnRun.textContent = running ? 'Running...' : 'Run Pipeline';
}

function updateCancelButton() {
  if (btnCancel) {
    btnCancel.hidden = true;
  }
}

function isBatchRunning() {
  return ['interpreting', 'generating', 'downloading', 'printing', 'cancelling'].includes(pipelineStatus);
}

async function cancelPipeline() {
  if (!isBatchRunning()) return;
  if (btnCancel) {
    btnCancel.disabled = true;
  }
  const result = await fetchJSON(API.cancel, {
    method: 'POST',
  });
  if (btnCancel) {
    btnCancel.disabled = false;
  }
  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to cancel the current batch.');
    return;
  }
  pipelineStatus = 'cancelling';
  updateStatus('working', 'Cancelling', 'Cancelling current batch...');
  updateRunButtonState();
  updateRunConfigInteractivity();
  updateCancelButton();
  renderJobBrowser();
}

function updateRunConfigInteractivity() {
  const disabled = isBatchRunning();
  const blockedControls = [
    imageUploadInput,
    btnUploadImage,
    btnCameraStart,
    btnCameraCapture,
    btnRun,
    btnSelectAll,
    btnClearSelection,
    btnRefresh,
    aspectRatioSelect,
    runCountInput,
    encourageVarietyWithinBatchesCheckbox,
    encourageVarietyAcrossSessionCheckbox,
    pipelineSelect,
    btnOpenPipelineEditor,
    btnSettings,
    btnSettingsSave,
    settingsDefaultPipeline,
    settingsSendToPrinter,
    settingsPrinterName,
    settingsSkipImageGeneration,
    settingsTextModel,
    settingsImageModel,
    btnLibraryExport,
    btnLibraryImport,
  ];
  blockedControls.forEach(control => {
    if (!control) return;
    control.dataset.runBlocked = disabled ? 'true' : 'false';
    control.classList.toggle('is-run-blocked', disabled);
  });
  watcherEnabledToggle.disabled = disabled;
  watchedFolderInput.disabled = disabled;
  settingsPrinterName.disabled = disabled || !sendToPrinter;
  promptInterp.readOnly = disabled || !PIPELINE_EDITING_ENABLED;
  descriptionEditor.readOnly = true;
  promptInterpEditor.contentEditable = disabled || !PIPELINE_EDITING_ENABLED ? 'false' : 'true';
  promptInterpEditor.setAttribute('aria-disabled', disabled || !PIPELINE_EDITING_ENABLED ? 'true' : 'false');
  promptImage.readOnly = disabled || !PIPELINE_EDITING_ENABLED;
  promptImageEditor.contentEditable = disabled || !PIPELINE_EDITING_ENABLED ? 'false' : 'true';
  promptImageEditor.setAttribute('aria-disabled', disabled || !PIPELINE_EDITING_ENABLED ? 'true' : 'false');
  renderSelection();
}

function getPromptInterpValue() {
  return promptInterp.value || '';
}

function getExtractedConceptsTokenText() {
  return (extractedConcepts || '').trim() || 'Extracted concepts will appear here';
}

function setPromptInterpValue(value) {
  promptInterp.value = value || '';
  renderPromptInterpEditor();
}

function renderPromptInterpEditor() {
  const template = getPromptInterpValue();
  const displayTemplate = template.replaceAll('{meaningfuldifference}', '');
  const injectedVarietyGuidance = buildInjectedVarietyGuidancePreview();
  promptInterpEditor.innerHTML = '';
  const tokens = [
    {
      token: '{extracted-concepts}',
      getText: getExtractedConceptsTokenText,
    },
  ];

  const renderTextWithTokens = (text, tokenIndex = 0) => {
    if (tokenIndex >= tokens.length) {
      const textBlock = document.createElement('div');
      textBlock.className = 'prompt-editor-spacer';
      textBlock.dataset.fragment = 'text';
      textBlock.textContent = text || '';
      if (!text) {
        textBlock.appendChild(document.createElement('br'));
      }
      promptInterpEditor.appendChild(textBlock);
      return;
    }

    const { token, getText } = tokens[tokenIndex];
    const fragments = text.split(token);
    const hasPlaceholder = text.includes(token);

    fragments.forEach((fragment, index) => {
      if (fragment || (hasPlaceholder && (index === 0 || index === fragments.length - 1))) {
        renderTextWithTokens(fragment, tokenIndex + 1);
      }
      if (hasPlaceholder && index < fragments.length - 1) {
        const chip = document.createElement('span');
        chip.className = 'prompt-token-chip';
        chip.dataset.token = token;
        chip.contentEditable = 'false';
        chip.textContent = getText();
        promptInterpEditor.appendChild(chip);
      }
    });
  };

  renderTextWithTokens(displayTemplate);

  if (injectedVarietyGuidance) {
    const chip = document.createElement('div');
    chip.className = 'prompt-token-chip prompt-token-chip-injected';
    chip.dataset.token = 'variety-guidance-injected';
    chip.contentEditable = 'false';

    const title = document.createElement('span');
    title.className = 'prompt-token-chip-title';
    title.textContent = 'Variety Guidance (injected at runtime)';
    chip.appendChild(title);

    const body = document.createElement('div');
    body.textContent = injectedVarietyGuidance;
    chip.appendChild(body);

    promptInterpEditor.appendChild(chip);
  }

  updatePromptInterpEditorPlaceholderState(displayTemplate);
}

function handlePromptInterpEditorInput() {
  if (!PIPELINE_EDITING_ENABLED) {
    renderPromptInterpEditor();
    return;
  }
  promptInterp.value = serializePromptInterpEditor();
  updatePromptInterpEditorPlaceholderState(promptInterp.value);
  schedulePromptAutosave();
}

function serializePromptInterpEditor() {
  const clone = promptInterpEditor.cloneNode(true);
  clone.querySelectorAll('[data-token="extracted-concepts"]').forEach(node => {
    node.replaceWith(document.createTextNode('{extracted-concepts}'));
  });
  clone.querySelectorAll('[data-token="{meaningfuldifference}"]').forEach(node => {
    node.replaceWith(document.createTextNode('{meaningfuldifference}'));
  });
  return editorInnerText(clone);
}

function updatePromptInterpEditorPlaceholderState(template) {
  if (!template) {
    promptInterpEditor.classList.add('is-empty');
    promptInterpEditor.dataset.placeholder = 'Type the pipeline prompt here.';
    return;
  }
  promptInterpEditor.classList.remove('is-empty');
  promptInterpEditor.removeAttribute('data-placeholder');
}

function handleBlockedControlClick(event) {
  if (!isBatchRunning()) return;
  const blockedControl = event.target.closest('[data-run-blocked="true"]');
  if (!blockedControl) return;
  event.preventDefault();
  event.stopPropagation();
  updateStatus('working', capitalise(pipelineStatus), 'This control is locked while the current batch is running. You can still browse the library.');
}

async function clearMeaningfulDifference() {
  if (isBatchRunning()) return;
  btnClearMeaningfulDifference.disabled = true;
  const result = await fetchJSON(API.meaningfulDifferenceClear, {
    method: 'POST',
  });
  if (!result || !result.ok) {
    syncRunOptions();
    updateStatus('error', 'Error', 'Failed to clear session variety memory.');
    return;
  }
  meaningfulDifferenceText = '';
  interpretationHistory = [];
  meaningfulDifferenceEditor.value = '';
  updateVarietyGuidanceEditorHeight();
  renderPromptInterpEditor();
  syncRunOptions();
  updateStatus('idle', 'Idle', 'Session variety memory cleared.');
}

function syncRunOptions() {
  const runCount = Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1));
  runCountInput.value = String(runCount);
  const canEncourageVarietyWithinBatches = runCount > 1;
  encourageVarietyWithinBatchesToggle.hidden = false;
  encourageVarietyWithinBatchesCheckbox.disabled = !canEncourageVarietyWithinBatches || isBatchRunning();
  encourageVarietyAcrossSessionCheckbox.disabled = isBatchRunning();
  if (!canEncourageVarietyWithinBatches) {
    encourageVarietyWithinBatchesCheckbox.checked = false;
  }
  settingsPrinterName.disabled = isBatchRunning() || !sendToPrinter;
  btnClearMeaningfulDifference.disabled = isBatchRunning() || !meaningfulDifferenceText;
  renderPromptInterpEditor();
}

function getPromptImageValue() {
  return promptImage.value || '';
}

function setPromptImageValue(value) {
  promptImage.value = value || '';
  renderPromptImageEditor();
}

function getDescriptionTokenText() {
  return (descriptionEditor.value || '').trim() || 'Description will appear here';
}

function renderPromptImageEditor() {
  const template = getPromptImageValue();
  const fragments = template.split('{description}');
  const hasPlaceholder = template.includes('{description}');
  promptImageEditor.innerHTML = '';

  fragments.forEach((fragment, index) => {
    const needsSpacer = hasPlaceholder && !fragment && (index === 0 || index === fragments.length - 1);
    if (fragment || needsSpacer) {
      const textBlock = document.createElement('div');
      textBlock.className = 'prompt-editor-spacer';
      textBlock.dataset.fragment = 'text';
      textBlock.textContent = fragment || '';
      if (!fragment) {
        textBlock.appendChild(document.createElement('br'));
      }
      promptImageEditor.appendChild(textBlock);
    }
    if (hasPlaceholder && index < fragments.length - 1) {
      const chip = document.createElement('span');
      chip.className = 'prompt-token-chip';
      chip.dataset.token = 'description';
      chip.contentEditable = 'false';
      chip.textContent = getDescriptionTokenText();
      promptImageEditor.appendChild(chip);
    }
  });

  updatePromptImageEditorPlaceholderState(template);
}

function serializePromptImageEditor() {
  const clone = promptImageEditor.cloneNode(true);
  clone.querySelectorAll('[data-token="description"]').forEach(node => {
    node.replaceWith(document.createTextNode('{description}'));
  });
  return editorInnerText(clone);
}

function handlePromptImageEditorInput() {
  if (!PIPELINE_EDITING_ENABLED) {
    renderPromptImageEditor();
    return;
  }
  promptImage.value = serializePromptImageEditor();
  updatePromptImageEditorPlaceholderState(promptImage.value);
  schedulePromptAutosave();
}

function handlePromptImageEditorKeydown(event) {
  if ((event.key === 'Enter' && !event.shiftKey) || event.key === 'Tab') {
    return;
  }
}

function updatePromptImageEditorPlaceholderState(template) {
  if (!template) {
    promptImageEditor.classList.add('is-empty');
    promptImageEditor.dataset.placeholder = 'Type the image generation prompt here. {description} will render inline.';
    return;
  }
  promptImageEditor.classList.remove('is-empty');
  promptImageEditor.removeAttribute('data-placeholder');
}

function editorInnerText(element) {
  return (element.innerText || '')
    .replace(/\u00a0/g, ' ')
    .replace(/\r\n/g, '\n');
}

function toggleInputRow() {
  setInputRowCollapsed(!inputRowCollapsed);
}

function setCollapseToggleState(button, expanded, labelBase) {
  if (!button) return;
  const action = expanded ? 'Collapse' : 'Expand';
  button.setAttribute('aria-expanded', String(expanded));
  button.setAttribute('aria-label', `${action} ${labelBase}`);
  button.setAttribute('title', `${action} ${labelBase}`);
}

function setInputRowCollapsed(collapsed) {
  inputRowCollapsed = Boolean(collapsed);
  stageInput.classList.toggle('is-collapsed', inputRowCollapsed);
  inputBoard.hidden = inputRowCollapsed;
  setCollapseToggleState(btnToggleInputRow, !inputRowCollapsed, 'manual control');
  window.localStorage.setItem('inputRowCollapsed', inputRowCollapsed ? 'true' : 'false');
}

function restoreInputRowPreference() {
  const saved = window.localStorage.getItem('inputRowCollapsed');
  setInputRowCollapsed(saved === 'true');
}

function toggleSystemLog() {
  setSystemLogCollapsed(!systemLogCollapsed);
}

function toggleJobBrowser() {
  setJobBrowserCollapsed(!jobBrowserCollapsed);
}

function toggleLibrary() {
  setLibraryCollapsed(!libraryCollapsed);
}

function toggleMeaningfulDifference() {
  setMeaningfulDifferenceCollapsed(!meaningfulDifferenceCollapsed);
}

function setSystemLogCollapsed(collapsed) {
  systemLogCollapsed = Boolean(collapsed);
  stageSystemLog.classList.toggle('is-collapsed', systemLogCollapsed);
  systemLogList.hidden = systemLogCollapsed;
  btnSystemLogPause.hidden = systemLogCollapsed;
  btnSystemLogClear.hidden = systemLogCollapsed;
  btnSystemLogJump.hidden = systemLogCollapsed || (systemLogPinnedToBottom && !systemLogPaused);
  if (systemLogStatus) {
    systemLogStatus.hidden = systemLogCollapsed;
  }
  setCollapseToggleState(btnToggleSystemLog, !systemLogCollapsed, 'system log');
  window.localStorage.setItem('systemLogCollapsed', systemLogCollapsed ? 'true' : 'false');
}

function restoreSystemLogPreference() {
  const saved = window.localStorage.getItem('systemLogCollapsed');
  setSystemLogCollapsed(saved === 'true');
}

function setJobBrowserCollapsed(collapsed) {
  jobBrowserCollapsed = Boolean(collapsed);
  stageJobBrowser.classList.toggle('is-collapsed', jobBrowserCollapsed);
  jobBrowserGrid.hidden = jobBrowserCollapsed;
  setCollapseToggleState(btnToggleJobBrowser, !jobBrowserCollapsed, 'job browser');
  window.localStorage.setItem('jobBrowserCollapsed', jobBrowserCollapsed ? 'true' : 'false');
}

function restoreJobBrowserPreference() {
  const saved = window.localStorage.getItem('jobBrowserCollapsed');
  setJobBrowserCollapsed(saved === 'true');
}

function setLibraryCollapsed(collapsed) {
  libraryCollapsed = Boolean(collapsed);
  stageLibrary.classList.toggle('is-collapsed', libraryCollapsed);
  libraryGrid.hidden = libraryCollapsed;
  setCollapseToggleState(btnToggleLibrary, !libraryCollapsed, 'library');
  window.localStorage.setItem('libraryCollapsed', libraryCollapsed ? 'true' : 'false');
}

function restoreLibraryPreference() {
  const saved = window.localStorage.getItem('libraryCollapsed');
  setLibraryCollapsed(saved === 'true');
}

function setMeaningfulDifferenceCollapsed(collapsed) {
  meaningfulDifferenceCollapsed = Boolean(collapsed);
  stageMeaningfulDifference.classList.toggle('is-collapsed', meaningfulDifferenceCollapsed);
  meaningfulDifferenceEditor.hidden = meaningfulDifferenceCollapsed;
  setCollapseToggleState(btnToggleMeaningfulDifference, !meaningfulDifferenceCollapsed, 'variety guidance');
  window.localStorage.setItem('meaningfulDifferenceCollapsed', meaningfulDifferenceCollapsed ? 'true' : 'false');
}

function restoreMeaningfulDifferencePreference() {
  const saved = window.localStorage.getItem('meaningfulDifferenceCollapsed');
  setMeaningfulDifferenceCollapsed(saved === 'true');
}

function initRowResizers() {
  bindRowResizer(resizeHandleBottom, '--content-row-height', stageInterpretation);
}

function bindRowResizer(handle, cssVarName, measuredElement) {
  if (!handle || !measuredElement) return;
  handle.addEventListener('pointerdown', event => {
    if (window.innerWidth <= 900) return;
    event.preventDefault();
    activeResize = {
      handle,
      cssVarName,
      startY: event.clientY,
      startHeight: measuredElement.getBoundingClientRect().height,
    };
    handle.classList.add('is-dragging');
    window.addEventListener('pointermove', onRowResizeMove);
    window.addEventListener('pointerup', onRowResizeEnd);
  });
}

function onRowResizeMove(event) {
  if (!activeResize) return;
  const nextHeight = Math.max(220, activeResize.startHeight + (event.clientY - activeResize.startY));
  document.documentElement.style.setProperty(activeResize.cssVarName, `${nextHeight}px`);
  if (activeResize.cssVarName === '--content-row-height') {
    layoutSettings.content_row_height = Math.round(nextHeight);
  }
}

async function onRowResizeEnd() {
  if (!activeResize) return;
  const shouldPersistLayout = activeResize.cssVarName === '--content-row-height';
  activeResize.handle.classList.remove('is-dragging');
  activeResize = null;
  window.removeEventListener('pointermove', onRowResizeMove);
  window.removeEventListener('pointerup', onRowResizeEnd);
  if (shouldPersistLayout) {
    await persistLayoutSettings();
  }
}

function applyLayoutSettings() {
  if (layoutSettings.content_row_height) {
    document.documentElement.style.setProperty('--content-row-height', `${layoutSettings.content_row_height}px`);
  }
}

async function persistLayoutSettings() {
  if (!defaultPipelineId && !currentPipelineId) return;
  const payload = buildSettingsPayload();
  payload.layout = layoutSettings;

  const result = await fetchJSON(API.settings, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to save layout.');
    return;
  }

  layoutSettings = { ...layoutSettings, ...(result.layout || {}) };
  applyLayoutSettings();
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function formatLibraryLabel(isoString) {
  if (!isoString) return 'Saved poster';

  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return 'Saved poster';

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function renderDebugList() {
  if (!errorItems.length) {
    debugList.innerHTML = '<p class="empty-state">No errors logged.</p>';
    return;
  }

  debugList.innerHTML = errorItems.slice().reverse().map(item => `
    <div class="debug-item">
      <div class="debug-meta">${escapeHtml(item.timestamp || '')} · ${escapeHtml(item.source || 'unknown')}</div>
      <div class="debug-message">${escapeHtml(item.message || '')}</div>
    </div>
  `).join('');
}

window.addEventListener('beforeunload', stopCamera);
window.addEventListener('beforeunload', () => {
  if (imagesRefreshInterval) {
    clearInterval(imagesRefreshInterval);
  }
  if (activeJobProgressInterval) {
    clearInterval(activeJobProgressInterval);
  }
});
window.addEventListener('keydown', event => {
  if (outputModal.hidden && assetPreviewModal.hidden && jobJsonModal.hidden && event.key !== 'Escape') {
    return;
  }
  if (event.key === 'Escape') {
    closeOutputModal();
    closeAssetPreviewModal();
    closeJobJsonModal();
  } else if (event.key === 'ArrowLeft') {
    if (!outputModal.hidden) {
      showPreviousOutput();
    }
  } else if (event.key === 'ArrowRight') {
    if (!outputModal.hidden) {
      showNextOutput();
    }
  }
});

// --- Go ---
init();
