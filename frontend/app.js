// ============================================================
//  DOM 引用
// ============================================================
const resultEl = document.querySelector('#result');
const historyEl = document.querySelector('#history');
const textForm = document.querySelector('#text-form');
const fileForm = document.querySelector('#file-form');

// 风险等级中文映射
const severityLabels = {
  high: '高风险',
  medium: '中风险',
  low: '低风险'
};

// ============================================================
//  工具函数
// ============================================================

/** 设置按钮的加载状态 */
function setBusy(button, busy, defaultLabel) {
  button.disabled = busy;
  button.textContent = busy ? '三个智能体正在评审…' : defaultLabel;
}

/** 显示错误信息到结果区域 */
function showError(message) {
  resultEl.classList.remove('hidden');
  resultEl.innerHTML = `
    <section class="panel error">
      <h2>评审未完成</h2>
      <p>${escapeHtml(message)}</p>
    </section>
  `;
}

/** 格式化时间戳 */
function formatTime(value) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'short',
    timeStyle: 'short'
  }).format(new Date(value));
}

/** 防 XSS 转义 */
function escapeHtml(str) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#039;',
    '"': '&quot;'
  };
  return String(str).replace(/[&<>'"]/g, char => map[char]);
}

// ============================================================
//  历史记录加载
// ============================================================

async function loadHistory() {
  try {
    const response = await fetch('/api/reviews'); //向当前域名下的 /api/reviews 路径发送 GET 请求。
    const items = await response.json(); //将后端返回的 JSON 字符串解析为 JavaScript 对象数组 items。

    historyEl.innerHTML = ''; // 清空

    if (items.length === 0) {
      historyEl.innerHTML = '<p class="muted">暂无评审记录</p>';
      return;
    }

    items.forEach(item => {
      const button = document.createElement('button');
      button.className = 'history-item'; //设置类名：history-item 用于绑定 CSS 样式
      button.innerHTML = `
        <strong>${escapeHtml(item.title)}</strong>
        <small>${formatTime(item.created_at)} · 高风险 ${item.high_count}</small>
      `;
      button.onclick = () => openReview(item.id);
      //绑定点击事件：button.onclick = () => openReview(item.id)。当用户点击该按钮时，会调用 openReview 函数，并传入该条记录的 id，从而加载完整报告。
      historyEl.append(button);
      //追加到 DOM：historyEl.append(button) 将构造好的按钮插入到容器末尾。
    });
  } catch {
    historyEl.innerHTML = '<p class="muted">历史记录加载失败</p>';
  }
}

// ============================================================
//  渲染评审报告
// ============================================================

function renderReview(review) {
  resultEl.classList.remove('hidden');
  resultEl.innerHTML = ''; // 清空

  // ---- 1. 报告头部 ----
  const header = document.createElement('section');
  header.className = 'panel report-head';

  // 头部左半部分：标题、摘要
  const infoDiv = document.createElement('div');
  infoDiv.innerHTML = `
    <p class="eyebrow">REVIEW REPORT</p>
    <h2>${escapeHtml(review.title)}</h2>
    <p>${escapeHtml(review.summary)}</p>
  `;

  // 头部右半部分：操作按钮
  const actionsDiv = document.createElement('div');
  actionsDiv.className = 'actions';
  actionsDiv.innerHTML = `
    <a class="outline" href="/api/reviews/${review.id}/export">下载 Markdown</a>
    <button class="danger" id="delete-review">删除记录</button>
  `;
  // 绑定删除事件
  actionsDiv.querySelector('#delete-review').onclick = () => deleteReview(review.id);

  // 风险计数
  const countsDiv = document.createElement('div');
  countsDiv.className = 'counts';
  countsDiv.innerHTML = `
    <span class="high">高 ${review.counts.high}</span>
    <span class="medium">中 ${review.counts.medium}</span>
    <span class="low">低 ${review.counts.low}</span>
  `;

  header.append(infoDiv, actionsDiv, countsDiv);
  resultEl.append(header);

  // ---- 2. 具体发现列表 ----
  const findingsGrid = document.createElement('section');
  findingsGrid.className = 'findings';

  review.findings.forEach(item => {
    // 从模板克隆
    const template = document.querySelector('#finding-template');
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector('.finding');
    card.classList.add(item.severity);

    fragment.querySelector('.badge').textContent = severityLabels[item.severity];
    fragment.querySelector('.reviewer').textContent = `${item.reviewer}评审`;
    fragment.querySelector('h3').textContent = item.title;
    fragment.querySelector('.evidence').textContent = item.evidence;
    fragment.querySelector('.reason').textContent = item.reason;
    fragment.querySelector('.recommendation').textContent = item.recommendation;

    findingsGrid.append(fragment);
  });

  resultEl.append(findingsGrid);
}

// ============================================================
//  打开 / 删除历史记录
// ============================================================

async function openReview(id) {
  const response = await fetch(`/api/reviews/${id}`);
  if (!response.ok) {
    return showError('无法读取这份历史评审。');
  }
  const review = await response.json();
  renderReview(review);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function deleteReview(id) {
  if (!confirm('确定删除这份评审记录吗？')) {
    return;
  }
  const response = await fetch(`/api/reviews/${id}`, { method: 'DELETE' });
  if (!response.ok) {
    return showError('删除失败，请稍后重试。');
  }
  resultEl.classList.add('hidden');
  await loadHistory();
}

// ============================================================
//  提交文本 / 文件
// ============================================================

async function submitText() {
  const button = document.querySelector('#submit-text');
  const titleInput = document.querySelector('#title');
  const docInput = document.querySelector('#document');

  const title = titleInput.value.trim();
  const documentText = docInput.value.trim();

  if (title.length < 2 || documentText.length < 30) {
    return showError('请填写至少 2 个字符的标题和 30 个字符的 PRD 内容。');
  }

  setBusy(button, true, '开始 AI 评审');

  try {
    const response = await fetch('/api/reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, document: documentText })
    });

    const review = await response.json();
    if (!response.ok) {
      throw new Error(review.detail || '评审请求失败');
    }

    renderReview(review);
    await loadHistory();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(button, false, '开始 AI 评审');
  }
}

async function submitFile() {
  const button = document.querySelector('#submit-file');
  const fileInput = document.querySelector('#file');
  const file = fileInput.files[0];

  if (!file) {
    return showError('请先选择一份需求文件。');
  }

  const titleInput = document.querySelector('#file-title');
  const title = titleInput.value.trim();

  const payload = new FormData();
  payload.append('file', file);
  if (title) {
    payload.append('title', title);
  }

  setBusy(button, true, '上传并开始评审');

  try {
    const response = await fetch('/api/reviews/upload', {
      method: 'POST',
      body: payload
    });

    const review = await response.json();
    if (!response.ok) {
      throw new Error(review.detail || '文件评审失败');
    }

    renderReview(review);
    await loadHistory();
  } catch (error) {
    showError(error.message);
  } finally {
    setBusy(button, false, '上传并开始评审');
  }
}

// ============================================================
//  事件绑定与初始化
// ============================================================

function init() {
  // ---- 模式切换 ----
  const modeButtons = document.querySelectorAll('.mode');
  modeButtons.forEach(button => {
    button.addEventListener('click', () => {
      // 切换激活状态
      modeButtons.forEach(btn => btn.classList.toggle('active', btn === button));
      const isText = button.dataset.mode === 'text';
      textForm.classList.toggle('hidden', !isText);
      fileForm.classList.toggle('hidden', isText);
    });
  });

  // ---- 文件选择显示文件名 ----
  const fileInput = document.querySelector('#file');
  const fileNameSpan = document.querySelector('#file-name');
  fileInput.addEventListener('change', () => {
    const name = fileInput.files[0]?.name || '支持 .txt、.md、.pdf、.docx，最大 8MB';
    fileNameSpan.textContent = name;
  });

  // ---- 提交按钮 ----
  document.querySelector('#submit-text').addEventListener('click', submitText);
  document.querySelector('#submit-file').addEventListener('click', submitFile);

  // ---- 新建评审（回到输入区域） ----
  document.querySelector('#new-review').addEventListener('click', () => {
    resultEl.classList.add('hidden');
    document.querySelector('#editor').scrollIntoView({ behavior: 'smooth' });
  });

  // ---- 加载历史 ----
  loadHistory();
}

// 启动
init();