/**
 * Dementia Design Poster Generator — Frontend
 */

const API = {
  images: '/api/images',
  pipelines: '/api/pipelines',
  settings: '/api/settings',
  errors: '/api/errors',
  capture: '/api/capture',
  run: '/api/run',
  status: '/api/status',
  results: '/api/results',
  library: '/api/library',
};

// --- DOM refs ---
const btnOpenImagePicker = document.getElementById('btn-open-image-picker');
const imagePickerModal = document.getElementById('image-picker-modal');
const imagePickerBackdrop = document.getElementById('image-picker-backdrop');
const btnImagePickerClose = document.getElementById('btn-image-picker-close');
const imagePickerGrid = document.getElementById('image-picker-grid');
const btnOpenPipelineEditor = document.getElementById('btn-open-pipeline-editor');
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
const btnOutputClose = document.getElementById('btn-output-close');
const outputModalBody = document.getElementById('output-modal-body');
const cameraVideo = document.getElementById('camera-video');
const cameraPlaceholder = document.getElementById('camera-placeholder');
const cameraStatus = document.getElementById('camera-status');
const btnCameraStart = document.getElementById('btn-camera-start');
const btnCameraCapture = document.getElementById('btn-camera-capture');
const selectionCount = document.getElementById('selection-count');
const btnSelectAll = document.getElementById('btn-select-all');
const btnClearSelection = document.getElementById('btn-clear-selection');
const aspectRatioSelect = document.getElementById('aspect-ratio-select');
const pipelineSelect = document.getElementById('pipeline-select');
const pipelinePath = document.getElementById('pipeline-path');
const promptInterp = document.getElementById('prompt-interpretation');
const promptImage = document.getElementById('prompt-image');
const btnRun = document.getElementById('btn-run');
const btnRefresh = document.getElementById('btn-refresh');
const btnSettings = document.getElementById('btn-settings');
const busyOverlay = document.getElementById('busy-overlay');
const busyOverlayPanel = document.getElementById('busy-overlay-panel');
const busyOverlayTitle = document.getElementById('busy-overlay-title');
const busyOverlayMessage = document.getElementById('busy-overlay-message');
const settingsModal = document.getElementById('settings-modal');
const settingsBackdrop = document.getElementById('settings-backdrop');
const btnSettingsClose = document.getElementById('btn-settings-close');
const btnSettingsSave = document.getElementById('btn-settings-save');
const settingsDefaultPipeline = document.getElementById('settings-default-pipeline');
const settingsTextModel = document.getElementById('settings-text-model');
const settingsImageModel = document.getElementById('settings-image-model');
const settingsDebugMode = document.getElementById('settings-debug-mode');
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
let busyOverlayDismissed = false;
let busyOverlayMode = 'idle';
const selectedImages = new Set();

// --- Init ---
async function init() {
  await loadImages();
  await loadPipelines();
  await loadLibrary();
  await loadSettings();
  await loadErrors();

  btnRefresh.addEventListener('click', loadImages);
  btnOpenImagePicker.addEventListener('click', openImagePickerModal);
  btnImagePickerClose.addEventListener('click', closeImagePickerModal);
  imagePickerBackdrop.addEventListener('click', closeImagePickerModal);
  btnOpenPipelineEditor.addEventListener('click', openPipelineEditorModal);
  btnPipelineEditorClose.addEventListener('click', closePipelineEditorModal);
  pipelineEditorBackdrop.addEventListener('click', closePipelineEditorModal);
  pipelineEditorSelect.addEventListener('change', () => loadPipelineSource(pipelineEditorSelect.value));
  pipelineEditorTextarea.addEventListener('input', schedulePipelineEditorAutosave);
  btnCreatePipeline.addEventListener('click', createPipelineFromEditor);
  btnPipelineEditorSave.addEventListener('click', savePipelineSource);
  busyOverlay.addEventListener('click', handleBusyOverlayClick);
  btnOutputPrev.addEventListener('click', showPreviousOutput);
  btnOutputNext.addEventListener('click', showNextOutput);
  btnOutputClose.addEventListener('click', closeOutputModal);
  outputBackdrop.addEventListener('click', closeOutputModal);
  btnRun.addEventListener('click', runPipeline);
  btnSettings.addEventListener('click', openSettingsModal);
  btnSettingsClose.addEventListener('click', closeSettingsModal);
  settingsBackdrop.addEventListener('click', closeSettingsModal);
  btnSettingsSave.addEventListener('click', saveSettings);
  btnDebugDetails.addEventListener('click', openDebugModal);
  btnDebugClearInline.addEventListener('click', clearErrors);
  btnDebugClose.addEventListener('click', closeDebugModal);
  btnDebugClear.addEventListener('click', clearErrors);
  debugBackdrop.addEventListener('click', closeDebugModal);
  btnCameraStart.addEventListener('click', toggleCamera);
  btnCameraCapture.addEventListener('click', captureFrame);
  btnSelectAll.addEventListener('click', selectAllImages);
  btnClearSelection.addEventListener('click', clearSelection);
  pipelineSelect.addEventListener('change', () => loadPipeline(pipelineSelect.value));
  promptInterp.addEventListener('input', schedulePromptAutosave);
  promptImage.addEventListener('input', schedulePromptAutosave);
  descriptionEditor.addEventListener('input', () => {
    if (!descriptionEditor.readOnly) return;
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
  updateRunButtonState();
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

  imagePickerGrid.querySelectorAll('.image-thumb').forEach(button => {
    button.addEventListener('click', () => toggleImageSelection(button.dataset.filename));
  });
  imagePickerGrid.querySelectorAll('.thumb-delete').forEach(button => {
    button.addEventListener('click', event => {
      event.stopPropagation();
      deleteImage(button.dataset.deleteFilename);
    });
  });

  renderSelection();
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
    button.addEventListener('click', () => restoreLibraryItem(button.dataset.filename));
  });
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
  settingsTextModel.value = textModel;
  settingsImageModel.value = imageModel;
  settingsDebugMode.checked = debugMode;
  refreshDebugBar();
}

async function loadErrors() {
  const data = await fetchJSON(API.errors);
  errorItems = data?.items || [];
  refreshDebugBar();
}

async function loadPipeline(pipelineId) {
  if (!pipelineId) return;

  const pipeline = await fetchJSON(`${API.pipelines}/${encodeURIComponent(pipelineId)}`);
  if (!pipeline) return;

  currentPipelineId = pipeline.id;
  pipelineSelect.value = pipeline.id;
  promptInterp.value = pipeline.interpretation || '';
  promptImage.value = pipeline.image || '';
  pipelinePath.textContent = pipeline.path || '';
  promptLastSavedState = JSON.stringify({
    pipelineId: pipeline.id,
    interpretation: promptInterp.value,
    image: promptImage.value,
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
    image: promptImage.value,
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
  settingsModal.hidden = false;
}

function closeSettingsModal() {
  settingsModal.hidden = true;
}

function openImagePickerModal() {
  imagePickerModal.hidden = false;
}

function closeImagePickerModal() {
  imagePickerModal.hidden = true;
}

function startImageAutoRefresh() {
  if (imagesRefreshInterval) clearInterval(imagesRefreshInterval);
  imagesRefreshInterval = setInterval(() => {
    loadImages();
  }, 1000);
}

async function openPipelineEditorModal() {
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
  restoreLibraryItem(libraryItems[nextIndex].poster_filename);
}

async function saveSettings() {
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
  await loadPipelines();
  closeSettingsModal();
  updateStatus('idle', 'Idle', 'Settings saved.');
  refreshDebugBar();
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

  if (status === 'complete') {
    stopPolling();
    showResults(description, poster_filename);
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
  }

  if (posterFilename) {
    currentPosterFilename = posterFilename;
  }
}

async function restoreLibraryItem(filename) {
  const item = libraryItems.find(entry => entry.poster_filename === filename);
  if (!item) return;

  if (item.pipeline_id) {
    await loadPipeline(item.pipeline_id);
  }

  promptInterp.value = item.interpretation_prompt || promptInterp.value || '';
  promptImage.value = item.image_generation_prompt || promptImage.value || '';
  descriptionEditor.value = item.description || '';
  imageModel = item.image_model || imageModel || 'replicate:google/nano-banana-pro';
  settingsImageModel.value = imageModel;
  aspectRatioSelect.value = item.aspect_ratio || aspectRatioSelect.value || '3:4';

  showResults(item.description, item.poster_filename);
  openOutputModal();
  updateStatus('complete', 'Library', `Loaded saved poster ${item.poster_filename}`);
  descriptionEditor.readOnly = true;
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
  }
  if (data.image_model) {
    imageModel = data.image_model;
    settingsImageModel.value = imageModel;
  }
  if (data.aspect_ratio) {
    aspectRatioSelect.value = data.aspect_ratio;
  }

  if (['interpreting', 'generating', 'downloading'].includes(status)) {
    updateStatus('working', capitalise(status), message);
    descriptionEditor.readOnly = true;
  } else if (status === 'complete') {
    updateStatus('complete', 'Complete', message);
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
  updateBusyOverlay();
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

function updateRunButtonState() {
  btnRun.disabled = selectedImages.size === 0 || ['interpreting', 'generating', 'downloading'].includes(pipelineStatus);
}

function updateBusyOverlay() {
  const nextMode = ['interpreting', 'generating', 'downloading'].includes(pipelineStatus)
    ? 'running'
    : (pipelineStatus === 'error' ? 'error' : 'idle');

  if (nextMode !== busyOverlayMode) {
    busyOverlayDismissed = false;
    busyOverlayMode = nextMode;
  }

  if (nextMode === 'idle') {
    busyOverlay.hidden = true;
    busyOverlay.classList.remove('panel-dismissed');
    return;
  }

  busyOverlay.hidden = false;
  busyOverlayTitle.textContent = pipelineStatus === 'error' ? 'Pipeline error' : 'Pipeline running';
  busyOverlayMessage.textContent = statusMessage.textContent || statusText.textContent || '';
  busyOverlay.classList.toggle('panel-dismissed', busyOverlayDismissed && nextMode === 'running');
}

function handleBusyOverlayClick(event) {
  if (event.target !== busyOverlay) return;
  if (busyOverlayMode === 'running') {
    busyOverlayDismissed = true;
    busyOverlay.classList.add('panel-dismissed');
    return;
  }
  if (busyOverlayMode === 'error') {
    busyOverlay.hidden = true;
    busyOverlayMode = 'idle';
    busyOverlayDismissed = false;
  }
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
