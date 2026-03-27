/**
 * Dementia Design Poster Generator — Frontend
 */

const API = {
  images: '/api/images',
  pipelines: '/api/pipelines',
  settings: '/api/settings',
  errors: '/api/errors',
  capture: '/api/capture',
  upload: '/api/upload',
  run: '/api/run',
  status: '/api/status',
  results: '/api/results',
  library: '/api/library',
  libraryExport: '/api/library/export',
  libraryImport: '/api/library/import',
};

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
const promptImage = document.getElementById('prompt-image');
const promptImageEditor = document.getElementById('prompt-image-editor');
const runCountInput = document.getElementById('run-count');
const rerunInterpretationToggle = document.getElementById('rerun-interpretation-toggle');
const rerunInterpretationCheckbox = document.getElementById('rerun-interpretation');
const btnRun = document.getElementById('btn-run');
const btnRefresh = document.getElementById('btn-refresh');
const btnSettings = document.getElementById('btn-settings');
const settingsModal = document.getElementById('settings-modal');
const settingsBackdrop = document.getElementById('settings-backdrop');
const btnSettingsClose = document.getElementById('btn-settings-close');
const btnSettingsSave = document.getElementById('btn-settings-save');
const btnLibraryExport = document.getElementById('btn-library-export');
const btnLibraryImport = document.getElementById('btn-library-import');
const libraryImportInput = document.getElementById('library-import-input');
const settingsDefaultPipeline = document.getElementById('settings-default-pipeline');
const settingsTextModel = document.getElementById('settings-text-model');
const settingsImageModel = document.getElementById('settings-image-model');
const settingsDebugMode = document.getElementById('settings-debug-mode');
const settingsRestoreInterpretation = document.getElementById('settings-restore-interpretation');
const settingsRestoreDescription = document.getElementById('settings-restore-description');
const settingsRestoreImagePrompt = document.getElementById('settings-restore-image-prompt');
const settingsRestoreImageModel = document.getElementById('settings-restore-image-model');
const settingsRestoreAspectRatio = document.getElementById('settings-restore-aspect-ratio');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const statusMessage = document.getElementById('status-message');
const debugBar = document.getElementById('debug-bar');
const debugSummary = document.getElementById('debug-summary');
const btnDebugDetails = document.getElementById('btn-debug-details');
const btnDebugClearInline = document.getElementById('btn-debug-clear-inline');
const debugModal = document.getElementById('debug-modal');
const debugBackdrop = document.getElementById('debug-backdrop');
const btnDebugClose = document.getElementById('btn-debug-close');
const btnDebugClear = document.getElementById('btn-debug-clear');
const debugList = document.getElementById('debug-list');
const stageInput = document.getElementById('stage-input');
const stageInterpretation = document.getElementById('stage-interpretation');
const stageDescription = document.getElementById('stage-description');
const stageImagePrompt = document.getElementById('stage-image-prompt');
const resizeHandleBottom = document.getElementById('resize-handle-bottom');
const descriptionEditor = document.getElementById('description-editor');
const libraryGrid = document.getElementById('library-grid');

let pollInterval = null;
let cameraStream = null;
let images = [];
let libraryItems = [];
let currentPipelineId = null;
let defaultPipelineId = null;
let debugMode = false;
let errorItems = [];
let currentPosterFilename = null;
let loadedMetadataPosterFilename = null;
let textModel = 'anthropic/claude-opus-4.6';
let imageModel = 'replicate:google/nano-banana-pro';
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
let activeResize = null;
let inputRowCollapsed = false;
let layoutSettings = {
  content_row_height: 448,
};
let lastLibraryPosterFilename = null;
let restoreSettings = {
  interpretation_prompt: true,
  description: true,
  image_generation_prompt: true,
  image_model: true,
  aspect_ratio: true,
};
const selectedImages = new Set();
const MODEL_ASPECT_RATIOS = {
  'replicate:openai/gpt-image-1.5': ['1:1', '3:2', '2:3'],
};

// --- Init ---
async function init() {
  await loadImages();
  await loadPipelines();
  await loadLibrary();
  await loadSettings();
  await loadErrors();

  btnRefresh.addEventListener('click', loadImages);
  btnUploadImage.addEventListener('click', uploadSelectedImage);
  btnOpenPipelineEditor.addEventListener('click', openPipelineEditorModal);
  btnPipelineEditorClose.addEventListener('click', closePipelineEditorModal);
  pipelineEditorBackdrop.addEventListener('click', closePipelineEditorModal);
  pipelineEditorSelect.addEventListener('change', () => loadPipelineSource(pipelineEditorSelect.value));
  pipelineEditorTextarea.addEventListener('input', schedulePipelineEditorAutosave);
  btnCreatePipeline.addEventListener('click', createPipelineFromEditor);
  btnPipelineEditorSave.addEventListener('click', savePipelineSource);
  document.addEventListener('click', handleBlockedControlClick, true);
  btnOutputPrev.addEventListener('click', showPreviousOutput);
  btnOutputNext.addEventListener('click', showNextOutput);
  btnOutputReload.addEventListener('click', reloadCurrentPosterMetadata);
  btnOutputClose.addEventListener('click', closeOutputModal);
  outputBackdrop.addEventListener('click', closeOutputModal);
  btnRun.addEventListener('click', runPipeline);
  btnSettings.addEventListener('click', openSettingsModal);
  btnSettingsClose.addEventListener('click', closeSettingsModal);
  settingsBackdrop.addEventListener('click', closeSettingsModal);
  settingsImageModel.addEventListener('change', () => syncAspectRatioOptions(settingsImageModel.value));
  btnSettingsSave.addEventListener('click', saveSettings);
  btnLibraryExport.addEventListener('click', exportLibrary);
  btnLibraryImport.addEventListener('click', () => libraryImportInput.click());
  libraryImportInput.addEventListener('change', importLibrary);
  btnDebugDetails.addEventListener('click', openDebugModal);
  btnDebugClearInline.addEventListener('click', clearErrors);
  btnDebugClose.addEventListener('click', closeDebugModal);
  btnDebugClear.addEventListener('click', clearErrors);
  debugBackdrop.addEventListener('click', closeDebugModal);
  btnCameraStart.addEventListener('click', toggleCamera);
  btnCameraCapture.addEventListener('click', captureFrame);
  btnToggleInputRow.addEventListener('click', toggleInputRow);
  btnSelectAll.addEventListener('click', selectAllImages);
  btnClearSelection.addEventListener('click', clearSelection);
  imagePickerGrid.addEventListener('click', handleImageGridClick);
  pipelineSelect.addEventListener('change', () => loadPipeline(pipelineSelect.value));
  promptInterp.addEventListener('input', schedulePromptAutosave);
  promptImageEditor.addEventListener('input', handlePromptImageEditorInput);
  promptImageEditor.addEventListener('keydown', handlePromptImageEditorKeydown);
  runCountInput.addEventListener('input', syncRunOptions);
  initRowResizers();
  descriptionEditor.addEventListener('input', () => {
    renderPromptImageEditor();
  });

  // Check if pipeline is already running (e.g. page refresh)
  const status = await fetchJSON(API.status);
  if (status?.pipeline_id) {
    await loadPipeline(status.pipeline_id);
  }
  if (status) {
    applyStatusState(status);
  }
  if (status && !['idle', 'complete', 'error'].includes(status.status)) {
    startPolling();
  }

  startImageAutoRefresh();
  restoreInputRowPreference();
  syncRunOptions();
  updateRunButtonState();
  updateRunConfigInteractivity();
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
  debugMode = Boolean(data?.debug_mode);
  textModel = data?.text_model || 'anthropic/claude-opus-4.6';
  imageModel = data?.image_model || 'replicate:google/nano-banana-pro';
  layoutSettings = { ...layoutSettings, ...(data?.layout || {}) };
  restoreSettings = { ...restoreSettings, ...(data?.restore_settings || {}) };
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  settingsDebugMode.checked = debugMode;
  settingsRestoreInterpretation.checked = Boolean(restoreSettings.interpretation_prompt);
  settingsRestoreDescription.checked = Boolean(restoreSettings.description);
  settingsRestoreImagePrompt.checked = Boolean(restoreSettings.image_generation_prompt);
  settingsRestoreImageModel.checked = Boolean(restoreSettings.image_model);
  settingsRestoreAspectRatio.checked = Boolean(restoreSettings.aspect_ratio);
  applyLayoutSettings();
  syncAspectRatioOptions(imageModel);
  refreshDebugBar();
}

async function loadErrors() {
  const data = await fetchJSON(API.errors);
  errorItems = data?.items || [];
  refreshDebugBar();
}

async function loadPipeline(pipelineId) {
  if (!pipelineId) return;

  clearTimeout(promptSaveTimeout);
  promptSavePending = false;

  const pipeline = await fetchJSON(`${API.pipelines}/${encodeURIComponent(pipelineId)}`);
  if (!pipeline) return;

  currentPipelineId = pipeline.id;
  pipelineSelect.value = pipeline.id;
  promptInterp.value = pipeline.interpretation || '';
  setPromptImageValue(pipeline.image || '');
  pipelinePath.textContent = pipeline.path || '';
  promptLastSavedState = JSON.stringify({
    pipelineId: pipeline.id,
    interpretation: promptInterp.value,
    image: getPromptImageValue(),
  });
}

function schedulePromptAutosave() {
  clearTimeout(promptSaveTimeout);
  promptSaveTimeout = setTimeout(() => {
    savePromptsToPipeline();
  }, 700);
}

async function savePromptsToPipeline() {
  if (!currentPipelineId) return;

  const saveState = JSON.stringify({
    pipelineId: currentPipelineId,
    interpretation: promptInterp.value,
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

function openSettingsModal() {
  settingsDefaultPipeline.value = defaultPipelineId || currentPipelineId || '';
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  settingsDebugMode.checked = debugMode;
  settingsRestoreInterpretation.checked = Boolean(restoreSettings.interpretation_prompt);
  settingsRestoreDescription.checked = Boolean(restoreSettings.description);
  settingsRestoreImagePrompt.checked = Boolean(restoreSettings.image_generation_prompt);
  settingsRestoreImageModel.checked = Boolean(restoreSettings.image_model);
  settingsRestoreAspectRatio.checked = Boolean(restoreSettings.aspect_ratio);
  syncAspectRatioOptions(settingsImageModel.value);
  settingsModal.hidden = false;
}

function closeSettingsModal() {
  settingsModal.hidden = true;
}

function startImageAutoRefresh() {
  if (imagesRefreshInterval) clearInterval(imagesRefreshInterval);
  imagesRefreshInterval = setInterval(() => {
    loadImages();
  }, 1000);
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
  btnPipelineEditorSave.textContent = 'Save Pipeline';
}

async function createPipelineFromEditor() {
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
  if (pipelineEditorIsLoading) return;

  btnPipelineEditorSave.textContent = 'Save Pipeline';
  clearTimeout(pipelineEditorSaveTimeout);
  pipelineEditorSaveTimeout = setTimeout(() => {
    savePipelineSource();
  }, 700);
}

function openOutputModal() {
  if (!currentPosterFilename) return;

  const imgUrl = `/output/${encodeURIComponent(currentPosterFilename)}`;
  outputModalBody.innerHTML = `<img src="${imgUrl}" alt="Generated poster preview">`;
  updateOutputModalNavigation();
  btnOutputReload.disabled = !libraryItems.some(item => item.poster_filename === currentPosterFilename);
  outputModal.hidden = false;
}

function closeOutputModal() {
  outputModal.hidden = true;
}

function updateOutputModalNavigation() {
  const currentIndex = libraryItems.findIndex(item => item.poster_filename === currentPosterFilename);
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
  if (!libraryItems.length || !currentPosterFilename) return;

  const currentIndex = libraryItems.findIndex(item => item.poster_filename === currentPosterFilename);
  if (currentIndex === -1) return;

  const nextIndex = (currentIndex + direction + libraryItems.length) % libraryItems.length;
  previewLibraryItem(libraryItems[nextIndex].poster_filename);
}

async function saveSettings() {
  if (isBatchRunning()) return;
  const selectedDefault = settingsDefaultPipeline.value;
  if (!selectedDefault) return;

  btnSettingsSave.disabled = true;
  const result = await fetchJSON(API.settings, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      default_pipeline_id: selectedDefault,
      text_model: settingsTextModel.value,
      image_model: settingsImageModel.value,
      debug_mode: settingsDebugMode.checked,
      restore_settings: {
        interpretation_prompt: settingsRestoreInterpretation.checked,
        description: settingsRestoreDescription.checked,
        image_generation_prompt: settingsRestoreImagePrompt.checked,
        image_model: settingsRestoreImageModel.checked,
        aspect_ratio: settingsRestoreAspectRatio.checked,
      },
      layout: layoutSettings,
    }),
  });
  btnSettingsSave.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to save settings.');
    return;
  }

  defaultPipelineId = result.default_pipeline_id;
  debugMode = Boolean(result.debug_mode);
  textModel = result.text_model || textModel;
  imageModel = result.image_model || imageModel;
  layoutSettings = { ...layoutSettings, ...(result.layout || {}) };
  restoreSettings = { ...restoreSettings, ...(result.restore_settings || {}) };
  applyLayoutSettings();
  syncAspectRatioOptions(imageModel);
  settingsDefaultPipeline.value = defaultPipelineId;
  pipelineSelect.value = currentPipelineId;
  pipelineEditorSelect.value = currentPipelineId;
  closeSettingsModal();
  updateStatus('idle', 'Idle', 'Settings saved.');
  refreshDebugBar();
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
  updateStatus('idle', 'Idle', `Imported ${result.imported} file${result.imported === 1 ? '' : 's'} into the library.`);
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
  btnDebugClearInline.disabled = true;
  const result = await fetchJSON(API.errors, { method: 'DELETE' });
  btnDebugClear.disabled = false;
  btnDebugClearInline.disabled = false;

  if (!result || !result.ok) {
    updateStatus('error', 'Error', 'Failed to clear errors.');
    return;
  }

  errorItems = [];
  renderDebugList();
  refreshDebugBar();
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
      interpretation_prompt: promptInterp.value,
      image_generation_prompt: promptImage.value,
      image_model: imageModel,
      aspect_ratio: aspectRatioSelect.value,
      run_count: Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1)),
      rerun_interpretation: rerunInterpretationCheckbox.checked,
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

  applyStatusState(data);

  if (poster_filename && poster_filename !== lastLibraryPosterFilename) {
    lastLibraryPosterFilename = poster_filename;
    showResults(description, poster_filename);
    loadLibrary();
  }

  if (status === 'complete') {
    stopPolling();
    loadLibrary();
  } else if (status === 'error') {
    stopPolling();
    loadErrors();
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
  statusDot.className = 'status-dot ' + (state === 'working' ? 'working' : state);
  statusText.textContent = text;
  statusMessage.textContent = message || '';
  refreshDebugBar();
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
  openOutputModal();
}

async function reloadCurrentPosterMetadata() {
  if (!currentPosterFilename) return;

  const item = libraryItems.find(entry => entry.poster_filename === currentPosterFilename);
  if (!item) return;

  if (item.pipeline_id) {
    await loadPipeline(item.pipeline_id);
  }

  if (restoreSettings.interpretation_prompt) {
    promptInterp.value = item.interpretation_prompt || promptInterp.value || '';
  }
  if (restoreSettings.image_generation_prompt) {
    setPromptImageValue(item.image_generation_prompt || getPromptImageValue() || '');
  }
  if (restoreSettings.description) {
    descriptionEditor.value = item.description || '';
    renderPromptImageEditor();
  }
  if (restoreSettings.image_model) {
    imageModel = item.image_model || imageModel || 'replicate:google/nano-banana-pro';
    settingsImageModel.value = imageModel;
  }
  if (restoreSettings.aspect_ratio) {
    syncAspectRatioOptions(imageModel, item.aspect_ratio || aspectRatioSelect.value || '3:4');
    aspectRatioSelect.value = item.aspect_ratio || aspectRatioSelect.value || '3:4';
  }

  showResults(item.description, item.poster_filename);
  loadedMetadataPosterFilename = item.poster_filename;
  renderLibrarySelectionState();
  updateStatus('complete', 'Library', `Loaded saved poster ${item.poster_filename}`);
  descriptionEditor.readOnly = true;
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

function applyStatusState(data) {
  const { status, message, description, poster_filename, error } = data;
  pipelineStatus = status || 'idle';

  if (description) {
    descriptionEditor.value = description;
    renderPromptImageEditor();
  }
  if (data.image_model) {
    imageModel = data.image_model;
    settingsImageModel.value = imageModel;
    syncAspectRatioOptions(imageModel, data.aspect_ratio || aspectRatioSelect.value);
  }

  if (['interpreting', 'generating', 'downloading'].includes(status)) {
    updateStatus('working', capitalise(status), message);
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
    if (!poster_filename && !description) {
      currentPosterFilename = null;
    }
  }

  updateRunButtonState();
  updateRunConfigInteractivity();
  updateStageHighlights(data);
}

function updateStageHighlights(data) {
  const { status, description } = data;
  const stages = [stageInput, stageInterpretation, stageDescription, stageImagePrompt];
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
    return;
  }

  stageInterpretation.classList.add('is-complete');

  if (['generating', 'downloading', 'complete'].includes(status)) {
    if (description) {
      stageDescription.classList.add(status === 'generating' ? 'is-active' : 'is-complete');
    }
    if (status === 'generating' || status === 'downloading') {
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
  btnRun.disabled = selectedImages.size === 0;
  btnRun.dataset.runBlocked = isBatchRunning() ? 'true' : 'false';
  btnRun.classList.toggle('is-run-blocked', isBatchRunning());
}

function isBatchRunning() {
  return ['interpreting', 'generating', 'downloading'].includes(pipelineStatus);
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
    rerunInterpretationCheckbox,
    pipelineSelect,
    btnOpenPipelineEditor,
    btnSettings,
    btnSettingsSave,
    settingsDefaultPipeline,
    settingsTextModel,
    settingsImageModel,
    settingsDebugMode,
    settingsRestoreInterpretation,
    settingsRestoreDescription,
    settingsRestoreImagePrompt,
    settingsRestoreImageModel,
    settingsRestoreAspectRatio,
    btnLibraryExport,
    btnLibraryImport,
  ];
  blockedControls.forEach(control => {
    if (!control) return;
    control.dataset.runBlocked = disabled ? 'true' : 'false';
    control.classList.toggle('is-run-blocked', disabled);
  });
  promptInterp.readOnly = disabled;
  descriptionEditor.readOnly = true;
  promptImageEditor.contentEditable = disabled ? 'false' : 'true';
  promptImageEditor.setAttribute('aria-disabled', disabled ? 'true' : 'false');
  renderSelection();
}

function handleBlockedControlClick(event) {
  if (!isBatchRunning()) return;
  const blockedControl = event.target.closest('[data-run-blocked="true"]');
  if (!blockedControl) return;
  event.preventDefault();
  event.stopPropagation();
  updateStatus('working', capitalise(pipelineStatus), 'This control is locked while the current batch is running. You can still browse the library.');
}

function syncRunOptions() {
  const runCount = Math.max(1, Math.min(20, Number.parseInt(runCountInput.value || '1', 10) || 1));
  runCountInput.value = String(runCount);
  rerunInterpretationToggle.hidden = runCount <= 1;
  if (runCount <= 1) {
    rerunInterpretationCheckbox.checked = false;
  }
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
  const parts = [];
  promptImageEditor.childNodes.forEach(node => {
    if (node.nodeType !== Node.ELEMENT_NODE) {
      parts.push(node.textContent || '');
      return;
    }
    if (node.dataset?.token === 'description') {
      parts.push('{description}');
      return;
    }
    if (node.dataset?.fragment === 'text') {
      const rawText = (node.innerText || '').replace(/\u00a0/g, ' ').replace(/\r\n/g, '\n');
      parts.push(rawText.replace(/\n$/, ''));
      return;
    }
    parts.push(node.textContent || '');
  });
  return parts.join('');
}

function handlePromptImageEditorInput() {
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

function toggleInputRow() {
  setInputRowCollapsed(!inputRowCollapsed);
}

function setInputRowCollapsed(collapsed) {
  inputRowCollapsed = Boolean(collapsed);
  stageInput.classList.toggle('is-collapsed', inputRowCollapsed);
  inputBoard.hidden = inputRowCollapsed;
  btnToggleInputRow.textContent = inputRowCollapsed ? 'Expand' : 'Collapse';
  btnToggleInputRow.setAttribute('aria-expanded', String(!inputRowCollapsed));
  window.localStorage.setItem('inputRowCollapsed', inputRowCollapsed ? 'true' : 'false');
}

function restoreInputRowPreference() {
  const saved = window.localStorage.getItem('inputRowCollapsed');
  setInputRowCollapsed(saved === 'true');
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

  const result = await fetchJSON(API.settings, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      default_pipeline_id: defaultPipelineId || currentPipelineId,
      text_model: textModel,
      image_model: imageModel,
      debug_mode: debugMode,
      restore_settings: restoreSettings,
      layout: layoutSettings,
    }),
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

function refreshDebugBar() {
  if (!debugMode) {
    debugBar.hidden = true;
    return;
  }

  debugBar.hidden = false;
  const count = errorItems.length;
  debugSummary.textContent = count > 0 ? `Debug mode on · ${count} error${count === 1 ? '' : 's'}` : 'Debug mode on · No errors';
  btnDebugDetails.hidden = count === 0;
  btnDebugDetails.disabled = count === 0;
  btnDebugClearInline.hidden = count === 0;
  btnDebugClearInline.disabled = count === 0;
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
});
window.addEventListener('keydown', event => {
  if (outputModal.hidden && event.key !== 'Escape') {
    return;
  }
  if (event.key === 'Escape') {
    closeOutputModal();
  } else if (event.key === 'ArrowLeft') {
    showPreviousOutput();
  } else if (event.key === 'ArrowRight') {
    showNextOutput();
  }
});

// --- Go ---
init();
