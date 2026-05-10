/* ── VideoSubtitle Frontend ────────────────────────────────────────────── */

const DOM = {
  uploadZone:    document.getElementById('uploadZone'),
  fileInput:     document.getElementById('fileInput'),
  browseLink:    document.getElementById('browseLink'),
  settings:      document.getElementById('settingsSection'),
  startBtn:      document.getElementById('startBtn'),
  modelSelect:    document.getElementById('modelSelect'),
  languageSelect:  document.getElementById('languageSelect'),
  translateSelect: document.getElementById('translateSelect'),
  // Style
  styleSection:  document.getElementById('styleSection'),
  styleToggle:   document.getElementById('styleToggle'),
  styleBody:     document.getElementById('styleBody'),
  fontSelect:    document.getElementById('fontSelect'),
  boldToggle:    document.getElementById('boldToggle'),
  sizeSlider:    document.getElementById('sizeSlider'),
  sizeLabel:     document.getElementById('sizeLabel'),
  primaryColor:  document.getElementById('primaryColor'),
  primaryColorLabel: document.getElementById('primaryColorLabel'),
  outlineColor:  document.getElementById('outlineColor'),
  outlineColorLabel: document.getElementById('outlineColorLabel'),
  outlineWidth:  document.getElementById('outlineWidth'),
  // Progress/Result
  progress:      document.getElementById('progressSection'),
  progressStep:  document.getElementById('progressStep'),
  progressPct:   document.getElementById('progressPct'),
  progressFill:  document.getElementById('progressFill'),
  progressInfo:  document.getElementById('progressInfo'),
  result:        document.getElementById('resultSection'),
  resultVideo:   document.getElementById('resultVideo'),
  resultMeta:    document.getElementById('resultMeta'),
  downloadBtn:   document.getElementById('downloadBtn'),
  newBtn:        document.getElementById('newBtn'),
  retryBtn:      document.getElementById('retryBtn'),
  error:         document.getElementById('errorSection'),
  errorMsg:      document.getElementById('errorMsg'),
  pulseDots:     document.getElementById('pulseDots'),
};

let currentFile = null;
let currentTaskId = null;
let pollTimer = null;

/* ── Upload Zone ────────────────────────────────────────────────────────── */

DOM.uploadZone.addEventListener('click', () => DOM.fileInput.click());
DOM.browseLink.addEventListener('click', (e) => { e.stopPropagation(); DOM.fileInput.click(); });

DOM.fileInput.addEventListener('change', () => {
  if (DOM.fileInput.files.length) handleFile(DOM.fileInput.files[0]);
});

DOM.uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  DOM.uploadZone.classList.add('dragover');
});
DOM.uploadZone.addEventListener('dragleave', () => {
  DOM.uploadZone.classList.remove('dragover');
});
DOM.uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  DOM.uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file.type.startsWith('video/')) {
    alert('请选择视频文件');
    return;
  }
  currentFile = file;
  DOM.uploadZone.classList.add('file-selected');
  DOM.uploadZone.querySelector('.upload-text').textContent = file.name;
  DOM.settings.style.display = 'block';
  DOM.styleSection.style.display = 'block';
  resetResult();
}

/* ── Start Processing ──────────────────────────────────────────────────── */

DOM.startBtn.addEventListener('click', startProcessing);
DOM.newBtn.addEventListener('click', resetAll);
DOM.retryBtn.addEventListener('click', () => {
  DOM.error.style.display = 'none';
  DOM.settings.style.display = 'block';
});

/* ── Style Panel ──────────────────────────────────────────────────────────── */

DOM.styleToggle.addEventListener('click', () => {
  DOM.styleBody.classList.toggle('open');
  DOM.styleToggle.classList.toggle('collapsed');
});

// Bold toggle
DOM.boldToggle.addEventListener('click', () => {
  DOM.boldToggle.classList.toggle('active');
});

// Size slider
DOM.sizeSlider.addEventListener('input', () => {
  const val = parseInt(DOM.sizeSlider.value);
  DOM.sizeLabel.textContent = SIZE_LABELS[val] || '中';
});

// Color pickers
DOM.primaryColor.addEventListener('input', () => {
  DOM.primaryColorLabel.textContent = colorName(DOM.primaryColor.value);
});
DOM.outlineColor.addEventListener('input', () => {
  DOM.outlineColorLabel.textContent = colorName(DOM.outlineColor.value);
});

const SIZE_LABELS = { 1: '极小', 2: '小', 3: '中', 4: '大', 5: '极大' };
const SIZE_RATIOS = { 1: 0.015, 2: 0.020, 3: 0.025, 4: 0.032, 5: 0.040 };

function colorName(hex) {
  const map = {
    '#ffffff': '白色', '#000000': '黑色', '#ff0000': '红色',
    '#00ff00': '绿色', '#0000ff': '蓝色', '#ffff00': '黄色',
    '#ff8800': '橙色', '#ff00ff': '紫色', '#00ffff': '青色',
  };
  return map[hex.toLowerCase()] || hex;
}

function getStyleOptions() {
  return {
    font_name: DOM.fontSelect.value,
    bold: DOM.boldToggle.classList.contains('active'),
    font_size_ratio: SIZE_RATIOS[parseInt(DOM.sizeSlider.value)] || 0.025,
    primary_color: DOM.primaryColor.value,
    outline_color: DOM.outlineColor.value,
    outline_width: parseInt(DOM.outlineWidth.value),
  };
}

async function startProcessing() {
  if (!currentFile) return;

  DOM.startBtn.disabled = true;
  DOM.startBtn.textContent = '上传中...';
  DOM.progress.style.display = 'block';
  DOM.progressStep.textContent = '正在上传...';
  DOM.progressPct.textContent = '0%';
  DOM.progressFill.style.width = '0%';
  DOM.pulseDots.style.display = 'flex';
  DOM.settings.style.display = 'none';

  try {
    const form = new FormData();
    form.append('file', currentFile);
    form.append('model', DOM.modelSelect.value);
    const lang = DOM.languageSelect.value;
    if (lang) form.append('language', lang);
    const trans = DOM.translateSelect.value;
    if (trans) form.append('translate_to', trans);
    form.append('style', JSON.stringify(getStyleOptions()));

    const resp = await fetch('/api/upload', { method: 'POST', body: form });
    if (!resp.ok) throw new Error(`上传失败 (${resp.status})`);

    const data = await resp.json();
    currentTaskId = data.task_id;

    DOM.startBtn.textContent = '开始处理';
    pollStatus(currentTaskId);

  } catch (err) {
    showError(err.message);
    DOM.startBtn.disabled = false;
    DOM.startBtn.textContent = '开始处理';
  }
}

/* ── Poll Status ────────────────────────────────────────────────────────── */

function pollStatus(taskId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    try {
      const resp = await fetch(`/api/tasks/${taskId}`);
      if (!resp.ok) throw new Error('查询状态失败');

      const data = await resp.json();
      updateProgress(data);

      if (data.status === 'completed') {
        clearInterval(pollTimer);
        pollTimer = null;
        showResult(data);
      } else if (data.status === 'failed') {
        clearInterval(pollTimer);
        pollTimer = null;
        showError(data.error || '处理失败');
      }
    } catch (err) {
      clearInterval(pollTimer);
      pollTimer = null;
      showError(err.message);
    }
  }, 800);
}

function updateProgress(data) {
  DOM.progressStep.textContent = data.step || '处理中...';
  DOM.progressPct.textContent = `${Math.round(data.progress)}%`;
  DOM.progressFill.style.width = `${data.progress}%`;
  DOM.progress.style.display = 'block';

  if (data.status === 'processing') {
    DOM.pulseDots.style.display = 'flex';
  }

  // 显示详细信息
  const infoParts = [];
  if (data.video_duration) infoParts.push(`时长 ${formatDuration(data.video_duration)}`);
  if (data.language) infoParts.push(`语言 ${data.language}`);
  if (data.subtitle_count) infoParts.push(`${data.subtitle_count} 条字幕`);
  DOM.progressInfo.textContent = infoParts.join(' · ');
}

function showResult(data) {
  DOM.pulseDots.style.display = 'none';
  DOM.progress.style.display = 'none';
  DOM.result.style.display = 'block';

  // 视频播放
  if (data.output_filename) {
    DOM.resultVideo.src = `/api/download/${data.output_filename}`;
    DOM.downloadBtn.href = `/api/download/${data.output_filename}`;
  }

  // 结果头部显示翻译标识
  const badgeHtml = data.translate_lang
    ? `处理完成 · 已翻译为 ${data.translate_lang}`
    : '处理完成';
  document.querySelector('.result-badge').textContent = badgeHtml;

  // 元信息
  const transHtml = data.translate_lang
    ? `<span>翻译 <strong>${data.translate_lang}</strong></span>`
    : '';
  DOM.resultMeta.innerHTML = `
    <span>时长 <strong>${formatDuration(data.video_duration)}</strong></span>
    <span>分辨率 <strong>${data.video_resolution || '-'}</strong></span>
    <span>语言 <strong>${data.language || '-'}</strong></span>
    <span>字幕 <strong>${data.subtitle_count || 0} 条</strong></span>
    <span>模型 <strong>${data.model_used || '-'}</strong></span>
    ${transHtml}
  `;
}

function showError(msg) {
  DOM.pulseDots.style.display = 'none';
  DOM.progress.style.display = 'none';
  DOM.error.style.display = 'block';
  DOM.errorMsg.textContent = msg;
  DOM.startBtn.disabled = false;
}

function resetResult() {
  DOM.result.style.display = 'none';
  DOM.error.style.display = 'none';
  DOM.progress.style.display = 'none';
  DOM.progressFill.style.width = '0%';
  DOM.resultVideo.src = '';
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function resetAll() {
  resetResult();
  currentFile = null;
  currentTaskId = null;
  DOM.fileInput.value = '';
  DOM.uploadZone.classList.remove('file-selected');
  DOM.uploadZone.querySelector('.upload-text').textContent = '拖放视频到此处，或点击选择文件';
  DOM.settings.style.display = 'none';
  DOM.styleSection.style.display = 'none';
  DOM.styleBody.classList.remove('open');
  DOM.styleToggle.classList.remove('collapsed');
  DOM.startBtn.disabled = false;
}

/* ── Helpers ────────────────────────────────────────────────────────────── */

function formatDuration(sec) {
  if (!sec) return '-';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  if (h > 0) return `${h}h${m}m${s}s`;
  if (m > 0) return `${m}m${s}s`;
  return `${s}s`;
}
