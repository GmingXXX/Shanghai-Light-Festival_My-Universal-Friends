// ==== 0) 配置区 ====
// 根据 video 文件夹自动生成的视频列表
let ALL_VIDEOS = [];

const STORAGE_KEY = 'voteData';

// ==== 1) DOM 引用 ====
const grid = document.getElementById('video-grid');
const btnSubmit = document.getElementById('btn-submit');
const btnStats = document.getElementById('btn-stats');
const btnRefresh = document.getElementById('btn-refresh');

const modal = document.getElementById('stats-modal');
const modalBackdrop = modal.querySelector('.modal-backdrop');
const btnCloseStats = document.getElementById('btn-close-stats');
const statsTableWrap = document.getElementById('stats-table-wrap');
const btnReset = document.getElementById('btn-reset');
const btnExportExcel = document.getElementById('btn-export-excel');

const toast = document.getElementById('toast');

// ==== 2) 状态 ====
let selectedSet = new Set();     // 当前选择
let currentBatch = [];           // 当前展示的视频列表（最多20）
let resizeObserverAttached = false;

// ==== 3) 工具函数 ====
function safeParse(json, fallback = {}) {
  try { return JSON.parse(json); } catch { return fallback; }
}

function readVotes() {
  const raw = localStorage.getItem(STORAGE_KEY);
  const obj = safeParse(raw, {});
  return (obj && typeof obj === 'object' && !Array.isArray(obj)) ? obj : {};
}

function writeVotes(obj) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
}

function showToast(msg = '操作成功', ms = 1200) {
  toast.textContent = msg;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, ms);
}

function fileBaseName(path) {
  const seg = path.split('/').pop() || path;
  return seg.replace(/\.[^.]+$/, ''); // 去扩展名
}

// Fisher-Yates 洗牌算法
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function updateSubmitButton() {
  const count = selectedSet.size;
  btnSubmit.disabled = count === 0;
  btnSubmit.textContent = `确认提交投票（已选 ${count}/3）`;
}

function updateVoteButtonsDisabled() {
  const count = selectedSet.size;
  const btns = grid.querySelectorAll('.btn-vote');
  btns.forEach(btn => {
    const video = btn.dataset.video;
    const isSelected = selectedSet.has(video);
    btn.disabled = !isSelected && count >= 3;
  });
}

// ==== 4) 视频卡片渲染 ====
function createCard(videoSrc) {
  const card = document.createElement('div');
  card.className = 'card';

  // 视频元素
  let videoEl = document.createElement('video');
  videoEl.className = 'card-video';
  videoEl.src = videoSrc;
  videoEl.autoplay = true;
  videoEl.muted = true;
  videoEl.loop = true;
  videoEl.playsInline = true; // iOS 支持
  videoEl.preload = 'metadata';
  videoEl.disablePictureInPicture = true;
  videoEl.controls = false;

  // 左上角标签：宇宙朋友 编号
  const label = document.createElement('div');
  label.className = 'card-label';
  label.textContent = `宇宙朋友 ${fileBaseName(videoSrc)}`;

  // 视频加载错误处理
  videoEl.addEventListener('error', () => {
    const placeholder = document.createElement('div');
    placeholder.className = 'placeholder';
    placeholder.textContent = '该视频无法播放';
    card.replaceChild(placeholder, videoEl);
    // 禁用对应的投票按钮
    const btn = card.querySelector('.btn-vote');
    if (btn) btn.disabled = true;
  });

  // 卡片主体
  const body = document.createElement('div');
  body.className = 'card-body';

  const btn = document.createElement('button');
  btn.className = 'btn btn-vote';
  btn.type = 'button';
  btn.textContent = '投TA一票';
  btn.dataset.video = videoSrc;
  btn.setAttribute('aria-pressed', 'false');
  body.appendChild(btn);

  card.appendChild(videoEl);
  card.appendChild(label);
  card.appendChild(body);

  return card;
}

function displayRandomVideos() {
  grid.setAttribute('aria-busy', 'true');
  grid.innerHTML = '';

  if (!ALL_VIDEOS || ALL_VIDEOS.length === 0) {
    const tip = document.createElement('div');
    tip.className = 'placeholder';
    tip.textContent = '未找到视频，请先在 script.js 配置 ALL_VIDEOS。';
    grid.appendChild(tip);
    grid.setAttribute('aria-busy', 'false');
    return;
  }

  // 随机抽取最多20个视频
  const list = shuffle([...ALL_VIDEOS]);
  currentBatch = list.slice(0, Math.min(20, list.length));
  selectedSet.clear();
  updateSubmitButton();

  // 创建文档片段优化性能
  const frag = document.createDocumentFragment();
  currentBatch.forEach(src => frag.appendChild(createCard(src)));
  grid.appendChild(frag);

  updateVoteButtonsDisabled();
  grid.setAttribute('aria-busy', 'false');

  // 渲染后计算单屏高度，确保20个卡片完全显示
  requestAnimationFrame(updateGridHeightToFitScreen);
}

// 计算视频网格高度，使 5×4 网格恰好放入可视区域
function updateGridHeightToFitScreen() {
  const header = document.querySelector('.app-header');
  const footer = document.querySelector('.app-footer');
  const headerH = header ? header.getBoundingClientRect().height : 0;
  const footerH = footer ? footer.getBoundingClientRect().height : 0;
  const vh = window.innerHeight;
  const available = Math.max(200, vh - headerH - footerH - 16 /*余量*/);
  document.documentElement.style.setProperty('--grid-height', available + 'px');
}

// ==== 5) 事件监听 ====
// 委托处理投票选择
grid.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn-vote');
  if (!btn) return;
  const video = btn.dataset.video;
  if (!video) return;

  const isSelected = selectedSet.has(video);

  if (isSelected) {
    // 取消选择
    selectedSet.delete(video);
    btn.classList.remove('selected');
    btn.setAttribute('aria-pressed', 'false');
  } else {
    if (selectedSet.size >= 3) {
      // 已达上限，不处理（按钮会被禁用）
      return;
    }
    // 添加选择
    selectedSet.add(video);
    btn.classList.add('selected');
    btn.setAttribute('aria-pressed', 'true');
  }

  updateSubmitButton();
  updateVoteButtonsDisabled();
});

// 提交投票
btnSubmit.addEventListener('click', () => {
  if (selectedSet.size === 0) return;

  const votes = readVotes();
  for (const v of selectedSet) {
    votes[v] = (votes[v] || 0) + 1;
  }
  writeVotes(votes);
  showToast('投票成功！页面即将刷新，展示新的朋友们！');

  // 清空选择，刷新卡片（不整页刷新）
  selectedSet.clear();
  updateSubmitButton();

  // 短暂延迟以展示Toast
  setTimeout(() => {
    displayRandomVideos();
  }, 600);
});

// 统计模态相关事件
btnStats.addEventListener('click', () => {
  openStats();
});

modalBackdrop.addEventListener('click', (e) => {
  if (e.target.dataset.close) closeStats();
});

btnCloseStats.addEventListener('click', closeStats);

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !modal.hidden) closeStats();
});

btnReset.addEventListener('click', () => {
  const ok = confirm('确定要重置投票记录吗？此操作不可恢复。');
  if (!ok) return;
  localStorage.removeItem(STORAGE_KEY);
  buildStatsTable(); // 刷新视图
  showToast('已重置投票记录');
});

// 导出票数为Excel
if (btnExportExcel) {
  btnExportExcel.addEventListener('click', async () => {
    try {
      await exportStatsToExcel();
      showToast('已导出Excel表格');
    } catch (e) {
      console.error(e);
      showToast('导出失败，请重试');
    }
  });
}

// ==== 6) 统计功能 ====
function openStats() {
  buildStatsTable();
  modal.hidden = false;
  // 聚焦提升可访问性
  btnCloseStats.focus();
}

function closeStats() {
  modal.hidden = true;
  btnStats.focus();
}

function buildStatsTable() {
  const votes = readVotes();
  const entries = Object.entries(votes); // [ [path, count], ... ]
  
  if (entries.length === 0) {
    statsTableWrap.innerHTML = '<div class="placeholder">暂无投票数据</div>';
    return;
  }

  // 按票数降序排列
  entries.sort((a, b) => b[1] - a[1]);

  const rows = entries.map(([path, count]) => {
    const name = `宇宙朋友 ${fileBaseName(path)}`;
    return `<tr><td title="${path}">${name}</td><td>${count}</td></tr>`;
  }).join('');

  statsTableWrap.innerHTML = `
    <table aria-describedby="stats-title">
      <thead><tr><th>视频</th><th>票数</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ==== 8) 导出为 Excel（CSV格式）====
async function exportStatsToExcel() {
  const votes = readVotes();
  const entries = Object.entries(votes).sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    showToast('暂无投票数据可导出');
    return;
  }

  // CSV 格式：使用逗号分隔，UTF-8 BOM 确保中文正常显示
  const lines = [
    '视频名称,票数,视频路径'  // 表头
  ];
  
  for (const [path, count] of entries) {
    const name = `宇宙朋友 ${fileBaseName(path)}`;
    // 将字段用双引号包裹，防止逗号等特殊字符影响
    lines.push(`"${name}",${count},"${path}"`);
  }
  
  const csvContent = lines.join('\r\n');
  
  // 添加 UTF-8 BOM，确保 Excel 正确识别中文编码
  const BOM = '\uFEFF';
  const content = BOM + csvContent;

  // 首选：文件保存对话（支持的浏览器）
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: '宇宙朋友101_票数统计.csv',
        types: [{ 
          description: 'Excel 表格', 
          accept: { 'text/csv': ['.csv'] } 
        }]
      });
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();
      return;
    } catch (e) {
      // 用户取消了保存，不报错
      if (e.name === 'AbortError') return;
      throw e;
    }
  }

  // 回退：触发下载
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = '宇宙朋友101_票数统计.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ==== 7) 页面启动 ====
document.addEventListener('DOMContentLoaded', () => {
  // 1) 首次扫描目录并渲染
  scanLocalVideos().then(() => displayRandomVideos());
  updateGridHeightToFitScreen();
  // 监听窗口尺寸变化
  window.addEventListener('resize', updateGridHeightToFitScreen);
  // 手动刷新按钮
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      await scanLocalVideos();
      displayRandomVideos();
      showToast('已刷新视频列表');
    });
  }
  // 每60秒自动检测一次新增/删除
  setInterval(async () => {
    const before = JSON.stringify(ALL_VIDEOS);
    await scanLocalVideos();
    const after = JSON.stringify(ALL_VIDEOS);
    if (before !== after) {
      displayRandomVideos();
      showToast('检测到新视频，已刷新列表');
    }
  }, 60000);
});

// ==== 目录扫描（本地文件方案）====
// 说明：纯本地文件无法直接读取目录，这里采用“按编号探测”的方式：
// 依次尝试 video/1.webm..video/60.webm，使用 <video> 的 canplay & error 结果判断存在性。
// 这样无需服务器即可做到“实时检测新增视频”。
async function scanLocalVideos(maxIndex = 999) {
  const candidates = [];
  for (let i = 1; i <= maxIndex; i++) {
    candidates.push(`video/${i}.webm`);
  }

  const exists = await filterExistingVideos(candidates);
  if (exists.length === 0) {
    // 保底：保留原有列表不清空，避免页面空白
    return ALL_VIDEOS;
  }
  ALL_VIDEOS = exists;
  return ALL_VIDEOS;
}

function filterExistingVideos(paths) {
  // 并发探测每个视频是否可加载
  const checks = paths.map(src => probeVideo(src).then(ok => ok ? src : null));
  return Promise.all(checks).then(list => list.filter(Boolean));
}

function probeVideo(src, timeoutMs = 3000) {
  return new Promise(resolve => {
    const video = document.createElement('video');
    let settled = false;
    const done = (ok) => { if (!settled) { settled = true; cleanup(); resolve(ok); } };
    const cleanup = () => {
      video.src = '';
      video.removeAttribute('src');
      video.load();
    };
    const timer = setTimeout(() => done(false), timeoutMs);
    video.preload = 'metadata';
    video.muted = true;
    video.src = src;
    video.onloadeddata = () => { clearTimeout(timer); done(true); };
    video.onerror = () => { clearTimeout(timer); done(false); };
  });
}
