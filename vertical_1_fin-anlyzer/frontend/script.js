/* ═══════════════════════════════════════════════════════════════════
   Financial Command Center — script.js
   All API calls, DOM manipulation, Chart.js logic, HITL UI.
   ═══════════════════════════════════════════════════════════════════ */

const API = '';  // Same origin — FastAPI serves this file

/* ── Cached state ──────────────────────────────────────────────────── */
let _assets    = [];
let _payables  = [];
let _receivables = [];
let _chart     = null;

/* ── Helpers ──────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

function fmt(n) {
  if (n === undefined || n === null || n === '—') return '—';
  const num = parseFloat(n);
  if (isNaN(num)) return '—';
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDate(d) {
  if (!d) return '—';
  const dt = new Date(d);
  if (isNaN(dt)) return '—';
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function isOverdue(d) {
  if (!d) return false;
  return new Date(d) < new Date();
}

function showToast(msg, type = '') {
  const t = $('toast');
  t.textContent = msg;
  t.className   = 'toast' + (type ? ` ${type}` : '');
  t.classList.remove('hidden', 'fade-out');
  setTimeout(() => {
    t.classList.add('fade-out');
    setTimeout(() => t.classList.add('hidden'), 300);
  }, 3200);
}

function setStatus(state) {
  const dot  = $('statusDot');
  const text = $('statusText');
  dot.className  = 'status-dot ' + (state === 'ok' ? 'ok' : state === 'err' ? 'err' : '');
  text.textContent = state === 'ok' ? 'connected' : state === 'err' ? 'error' : 'connecting';
}

function liquidityPips(score) {
  let html = '<div class="liq-pips">';
  for (let i = 1; i <= 5; i++) {
    html += `<div class="liq-pip${i <= score ? ' on' : ''}"></div>`;
  }
  return html + '</div>';
}

/* ── Tab Switching ────────────────────────────────────────────────── */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    $('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'ledger') renderAssetsTable();
  });
});

/* ── Dashboard Data ───────────────────────────────────────────────── */
async function loadDashboard() {
  try {
    const res  = await fetch(`${API}/api/dashboard`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    _assets      = data.assets      || [];
    _payables    = data.payables    || [];
    _receivables = data.receivables || [];

    setStatus('ok');
    renderSummary(data.summary);
    renderChart(data.projection);
    renderPayables(_payables);
    renderReceivables(_receivables);
    renderAssetsTable();
  } catch (err) {
    setStatus('err');
    console.error('Dashboard load failed:', err);
  }
}

function renderSummary(s) {
  if (!s) return;
  $('sumAssets').textContent      = fmt(s.total_assets);
  $('sumPayables').textContent    = fmt(s.total_payables);
  $('sumReceivables').textContent = fmt(s.total_receivables);
  const net = (s.total_assets || 0) - (s.total_payables || 0) + (s.total_receivables || 0);
  const el = $('sumNet');
  el.textContent = fmt(net);
  el.style.color = net >= 0 ? 'var(--up)' : 'var(--down)';
}

function renderChart(projection) {
  if (!projection || !projection.length) {
    $('chartNote').textContent = 'no projection data';
    return;
  }

  const labels = projection.map(p => p.date);
  const values = projection.map(p => p.balance);

  const minVal = Math.min(...values);
  $('chartNote').textContent = `min: ${fmt(minVal)} in 30 days`;

  const ctx = $('projectionChart').getContext('2d');

  if (_chart) { _chart.destroy(); }

  // Gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, 280);
  grad.addColorStop(0,   'rgba(17,17,16,.12)');
  grad.addColorStop(1,   'rgba(17,17,16,.00)');

  _chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: '#111110',
        borderWidth: 1.5,
        backgroundColor: grad,
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: '#111110',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111110',
          titleColor: '#a1a19b',
          bodyColor: '#ffffff',
          padding: 10,
          cornerRadius: 6,
          titleFont: { family: "'DM Mono', monospace", size: 10 },
          bodyFont:  { family: "'DM Mono', monospace", size: 12 },
          callbacks: {
            label: ctx => fmt(ctx.parsed.y),
          }
        }
      },
      scales: {
        x: {
          grid:  { display: false },
          ticks: {
            color: '#a1a19b',
            font:  { family: "'DM Mono', monospace", size: 9 },
            maxTicksLimit: 8,
            maxRotation: 0,
          },
          border: { display: false },
        },
        y: {
          grid:  { color: '#e2e2de', lineWidth: 1 },
          ticks: {
            color: '#a1a19b',
            font:  { family: "'DM Mono', monospace", size: 9 },
            maxTicksLimit: 5,
            callback: v => {
              if (Math.abs(v) >= 100000) return '₹' + (v/100000).toFixed(1) + 'L';
              if (Math.abs(v) >= 1000)   return '₹' + (v/1000).toFixed(0) + 'K';
              return '₹' + v;
            }
          },
          border: { display: false },
        }
      }
    }
  });
}

/* ── Payables list ────────────────────────────────────────────────── */
function renderPayables(payables) {
  const list = $('payablesList');
  $('payableCount').textContent = payables.length;

  if (!payables.length) {
    list.innerHTML = '<div class="empty-state">No pending payables</div>';
    return;
  }

  const sorted = [...payables].sort((a, b) => new Date(a.due_date) - new Date(b.due_date));

  list.innerHTML = sorted.map(p => {
    const overdue = isOverdue(p.due_date);
    return `
      <div class="list-item">
        <div class="list-left">
          <span class="list-name">${esc(p.creditor)}</span>
          <span class="list-meta ${overdue ? 'overdue' : ''}">Due ${fmtDate(p.due_date)}${p.penalty_fee > 0 ? ` · penalty ${fmt(p.penalty_fee)}` : ''}</span>
        </div>
        <div class="list-right">
          <span class="list-amount red">${fmt(p.amount)}</span>
          <button class="btn-sm" onclick="openPayModal('${p.id}')">Pay</button>
        </div>
      </div>`;
  }).join('');
}

/* ── Receivables list ─────────────────────────────────────────────── */
function renderReceivables(receivables) {
  const list = $('receivablesList');
  $('receivableCount').textContent = receivables.length;

  if (!receivables.length) {
    list.innerHTML = '<div class="empty-state">No pending receivables</div>';
    return;
  }

  const sorted = [...receivables].sort((a, b) => new Date(a.expected_date) - new Date(b.expected_date));

  list.innerHTML = sorted.map(r => {
    const badgeClass = { High: 'badge-high', Med: 'badge-med', Low: 'badge-low' }[r.confidence] || 'badge-med';
    return `
      <div class="list-item">
        <div class="list-left">
          <span class="list-name">${esc(r.source)}</span>
          <span class="list-meta">Expected ${fmtDate(r.expected_date)}</span>
        </div>
        <div class="list-right">
          <span class="badge ${badgeClass}">${r.confidence}</span>
          <span class="list-amount green">${fmt(r.amount)}</span>
          <button class="btn-sm" onclick="openRecModal('${r.id}')">Receive</button>
        </div>
      </div>`;
  }).join('');
}

/* ── Assets Table ─────────────────────────────────────────────────── */
function renderAssetsTable() {
  const tbody = $('assetsTable');
  if (!_assets.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No assets recorded</td></tr>';
    return;
  }

  tbody.innerHTML = _assets.map(a => `
    <tr>
      <td>${esc(a.name)}</td>
      <td><span class="badge badge-paid">${esc(a.type)}</span></td>
      <td class="mono">${fmt(a.value)}</td>
      <td>${liquidityPips(a.liquidity_score)}</td>
    </tr>`).join('');
}

/* ── Pay Modal ────────────────────────────────────────────────────── */
let _activePayableId   = null;
let _activePayableAmt  = 0;

function _getUsedAssetIds(excludeRow) {
  return Array.from($('allocationContainer').querySelectorAll('.allocation-row'))
    .filter(r => r !== excludeRow)
    .map(r => r.querySelector('.allocation-asset').value);
}

function _redistributeAmounts() {
  const rows = Array.from($('allocationContainer').querySelectorAll('.allocation-row'));
  if (!rows.length) return;
  const each = (_activePayableAmt / rows.length).toFixed(2);
  // Distribute evenly; last row gets the remainder to avoid rounding drift
  let assigned = 0;
  rows.forEach((row, i) => {
    const inp = row.querySelector('.allocation-amount');
    if (i < rows.length - 1) {
      inp.value = each;
      assigned += parseFloat(each);
    } else {
      inp.value = (_activePayableAmt - assigned).toFixed(2);
    }
  });
}

function _refreshAssetOptions() {
  // For each row, grey-out / disable options already chosen by OTHER rows
  const rows = Array.from($('allocationContainer').querySelectorAll('.allocation-row'));
  rows.forEach(row => {
    const sel  = row.querySelector('.allocation-asset');
    const used = _getUsedAssetIds(row);
    Array.from(sel.options).forEach(opt => {
      opt.disabled = used.includes(opt.value);
    });
    // If current selection became disabled, jump to first available
    if (sel.options[sel.selectedIndex]?.disabled) {
      const first = Array.from(sel.options).find(o => !o.disabled);
      if (first) sel.value = first.value;
    }
  });
}

function _buildAllocationRow() {
  const row = document.createElement('div');
  row.className = 'allocation-row';
  row.style.cssText = 'display:flex;gap:8px;margin-bottom:6px;align-items:center;';

  const sel = document.createElement('select');
  sel.className = 'field-input allocation-asset';
  sel.style.flex = '1';
  sel.innerHTML = _assets.map(a =>
    `<option value="${a.id}">${esc(a.name)} (${fmt(a.value)})</option>`
  ).join('');
  sel.addEventListener('change', () => _refreshAssetOptions());

  const inp = document.createElement('input');
  inp.type = 'number';
  inp.className = 'field-input allocation-amount';
  inp.placeholder = 'Amount';
  inp.min = '0.01';
  inp.step = '0.01';
  inp.style.cssText = 'width:110px;flex-shrink:0;';

  const del = document.createElement('button');
  del.textContent = '✕';
  del.className = 'btn-ghost';
  del.style.cssText = 'flex-shrink:0;padding:4px 8px;';
  del.addEventListener('click', () => {
    row.remove();
    const container = $('allocationContainer');
    if (container.children.length === 0) {
      container.appendChild(_buildAllocationRow());
    }
    _refreshAssetOptions();
    _redistributeAmounts();
  });

  row.appendChild(sel);
  row.appendChild(inp);
  row.appendChild(del);
  return row;
}

function _addAllocationRow() {
  // Only allow as many splits as there are distinct assets
  const rows = $('allocationContainer').querySelectorAll('.allocation-row');
  if (rows.length >= _assets.length) {
    showToast('No more assets available to split across', 'error');
    return;
  }
  $('allocationContainer').appendChild(_buildAllocationRow());
  _refreshAssetOptions();
  _redistributeAmounts();
}

function openPayModal(payableId) {
  _activePayableId  = payableId;
  const p = _payables.find(x => x.id === payableId);
  if (!p) return;
  _activePayableAmt = p.amount;

  $('modalPayDetail').innerHTML = `
    <strong>${esc(p.creditor)}</strong>
    <span class="modal-amount">${fmt(p.amount)}</span>
    <span style="font-size:11px;color:var(--ink-3);font-family:var(--font-mono)">Due ${fmtDate(p.due_date)}</span>`;

  const container = $('allocationContainer');
  container.innerHTML = '';
  const firstRow = _buildAllocationRow();
  firstRow.querySelector('.allocation-amount').value = p.amount.toFixed(2);
  container.appendChild(firstRow);

  $('modalError').classList.add('hidden');
  $('payModal').classList.remove('hidden');
}

$('addSplitBtn').addEventListener('click', _addAllocationRow);
$('closePayModal').addEventListener('click',  () => $('payModal').classList.add('hidden'));
$('cancelPayModal').addEventListener('click', () => $('payModal').classList.add('hidden'));

$('confirmPayBtn').addEventListener('click', async () => {
  const btn = $('confirmPayBtn');
  btn.disabled = true;
  $('modalError').classList.add('hidden');
  try {
    // Scrape allocation rows
    const rows = $('allocationContainer').querySelectorAll('.allocation-row');
    const allocations = [];
    for (const row of rows) {
      const asset_id = row.querySelector('.allocation-asset').value;
      const amount   = parseFloat(row.querySelector('.allocation-amount').value);
      if (!asset_id || isNaN(amount) || amount <= 0) {
        const err = $('modalError');
        err.textContent = 'Please fill in all allocation rows with valid amounts.';
        err.classList.remove('hidden');
        return;
      }
      allocations.push({ asset_id, amount });
    }

    const res = await fetch(`${API}/api/process_payment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payable_id: _activePayableId, allocations })
    });
    const data = await res.json();
    if (!res.ok) {
      const err = $('modalError');
      err.textContent = data.detail || 'Payment failed';
      err.classList.remove('hidden');
      return;
    }
    $('payModal').classList.add('hidden');
    const splitMsg = data.splits > 1 ? ` across ${data.splits} assets` : '';
    showToast(`Payment of ${fmt(data.total_paid)} processed${splitMsg}`, 'success');
    await loadDashboard();
  } catch (e) {
    showToast('Network error', 'error');
  } finally {
    btn.disabled = false;
  }
});

/* ── Receive Modal ────────────────────────────────────────────────── */
let _activeReceivableId = null;

function openRecModal(receivableId) {
  _activeReceivableId = receivableId;
  const r = _receivables.find(x => x.id === receivableId);
  if (!r) return;

  $('modalRecDetail').innerHTML = `
    <strong>${esc(r.source)}</strong>
    <span class="modal-amount">${fmt(r.amount)}</span>
    <span style="font-size:11px;color:var(--ink-3);font-family:var(--font-mono)">Expected ${fmtDate(r.expected_date)}</span>`;

  const sel = $('modalRecAssetSelect');
  sel.innerHTML = _assets.map(a =>
    `<option value="${a.id}">${esc(a.name)} (${fmt(a.value)})</option>`
  ).join('');

  $('modalRecError').classList.add('hidden');
  $('recModal').classList.remove('hidden');
}

$('closeRecModal').addEventListener('click',  () => $('recModal').classList.add('hidden'));
$('cancelRecModal').addEventListener('click', () => $('recModal').classList.add('hidden'));

$('confirmRecBtn').addEventListener('click', async () => {
  const btn = $('confirmRecBtn');
  btn.disabled = true;
  $('modalRecError').classList.add('hidden');
  try {
    const res = await fetch(`${API}/api/process_income`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        receivable_id: _activeReceivableId,
        asset_id:      $('modalRecAssetSelect').value,
      })
    });
    const data = await res.json();
    if (!res.ok) {
      const err = $('modalRecError');
      err.textContent = data.detail || 'Income recording failed';
      err.classList.remove('hidden');
      return;
    }
    $('recModal').classList.add('hidden');
    showToast('Income recorded · new balance ' + fmt(data.new_balance), 'success');
    await loadDashboard();
  } catch (e) {
    showToast('Network error', 'error');
  } finally {
    btn.disabled = false;
  }
});

/* ── Entry Type Toggle ────────────────────────────────────────────── */
$('entryType').addEventListener('change', function () {
  ['asset', 'payable', 'receivable'].forEach(t => {
    $('fields-' + t).classList.toggle('hidden', t !== this.value);
  });
});

/* ── Add Entry Form ───────────────────────────────────────────────── */
$('submitEntry').addEventListener('click', async () => {
  const type = $('entryType').value;
  const err  = $('formError');
  err.classList.add('hidden');

  let data = {};

  if (type === 'asset') {
    const name  = $('asset-name').value.trim();
    const value = parseFloat($('asset-value').value);
    const liq   = parseInt($('asset-liquidity').value);
    if (!name)          return showFieldError('Asset name is required');
    if (isNaN(value))   return showFieldError('Valid value is required');
    if (liq < 1 || liq > 5 || isNaN(liq)) return showFieldError('Liquidity score must be 1–5');
    data = { name, type: $('asset-type').value, value, liquidity_score: liq };
  }

  else if (type === 'payable') {
    const creditor = $('payable-creditor').value.trim();
    const amount   = parseFloat($('payable-amount').value);
    const due      = $('payable-due').value;
    const penalty  = parseFloat($('payable-penalty').value) || 0;
    if (!creditor)      return showFieldError('Creditor is required');
    if (isNaN(amount))  return showFieldError('Valid amount is required');
    if (!due)           return showFieldError('Due date is required');
    data = { creditor, amount, due_date: new Date(due).toISOString(), penalty_fee: penalty };
  }

  else if (type === 'receivable') {
    const source  = $('rec-source').value.trim();
    const amount  = parseFloat($('rec-amount').value);
    const expDate = $('rec-date').value;
    if (!source)        return showFieldError('Source is required');
    if (isNaN(amount))  return showFieldError('Valid amount is required');
    if (!expDate)       return showFieldError('Expected date is required');
    data = {
      source, amount,
      expected_date: new Date(expDate).toISOString(),
      confidence: $('rec-confidence').value
    };
  }

  const btn = $('submitEntry');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  try {
    const res = await fetch(`${API}/api/add_entry`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ entry_type: type, data })
    });
    const result = await res.json();
    if (!res.ok) {
      showFieldError(result.detail || 'Failed to add entry');
      return;
    }
    showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} added`, 'success');
    clearForm(type);
    await loadDashboard();
  } catch (e) {
    showFieldError('Network error — is the server running?');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Add Entry';
  }
});

function showFieldError(msg) {
  const err = $('formError');
  err.textContent = msg;
  err.classList.remove('hidden');
}

function clearForm(type) {
  if (type === 'asset') {
    $('asset-name').value = '';
    $('asset-value').value = '';
    $('asset-liquidity').value = '';
  } else if (type === 'payable') {
    $('payable-creditor').value = '';
    $('payable-amount').value = '';
    $('payable-due').value = '';
    $('payable-penalty').value = '';
  } else {
    $('rec-source').value = '';
    $('rec-amount').value = '';
    $('rec-date').value = '';
  }
}

/* ── AI Chat ──────────────────────────────────────────────────────── */
const chatMessages = $('chatMessages');
const chatInput    = $('chatInput');
const sendBtn      = $('sendBtn');

function appendMessage(role, content, isHtml = false) {
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if (isHtml) bubble.innerHTML = content;
  else        bubble.textContent = content;
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function appendThinking() {
  const div = document.createElement('div');
  div.className = 'chat-msg assistant';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble thinking';
  bubble.textContent = 'thinking…';
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg) return;

  chatInput.value = '';
  sendBtn.disabled = true;
  appendMessage('user', msg);
  const thinking = appendThinking();

  try {
    const res  = await fetch(`${API}/api/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, custom_instruction: (_systemPromptActive && _systemPromptCache) ? _systemPromptCache : '' })
    });
    const data = await res.json();
    thinking.remove();
    if (!res.ok) {
      appendMessage('assistant', `Error: ${data.detail || 'Unknown error'}`);
    } else {
      appendMessage('assistant', data.response || '(no response)');
    }
  } catch (e) {
    thinking.remove();
    appendMessage('assistant', 'Network error — is the backend running?');
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

/* ── Attach button → file picker ──────────────────────────────────── */
$('attachBtn').addEventListener('click', () => $('chatFileAttach').click());

$('chatFileAttach').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = ''; // reset so same file can be re-selected

  appendMessage('user', `📎 ${file.name}`);
  const thinking = appendThinking();
  thinking.querySelector('.msg-bubble').textContent = `Analyzing ${file.name}…`;

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch(`${API}/api/analyze_document`, { method: 'POST', body: form });
    const data = await res.json();
    thinking.remove();
    if (!res.ok) {
      appendMessage('assistant', `Analysis failed: ${data.detail || 'unknown error'}`);
      return;
    }
    renderHITLCard(data.extracted_data, data.pages_analysed);
  } catch (err) {
    thinking.remove();
    appendMessage('assistant', 'Document analysis failed — network error.');
  }
});

/* ── Prompt Toggle ────────────────────────────────────────────────── */
let _systemPromptActive = false;
let _systemPromptCache  = null;

const promptToggleBtn = $('promptToggleBtn');

promptToggleBtn.addEventListener('click', async () => {
  _systemPromptActive = !_systemPromptActive;
  promptToggleBtn.dataset.active = _systemPromptActive;
  promptToggleBtn.title = _systemPromptActive
    ? 'System prompt ON — click to disable'
    : 'System prompt OFF — click to enable';
  promptToggleBtn.style.opacity    = _systemPromptActive ? '1'   : '0.45';
  promptToggleBtn.style.background = _systemPromptActive ? 'var(--accent-blue, #3b82f6)' : '';
  promptToggleBtn.style.color      = _systemPromptActive ? '#fff' : '';
  promptToggleBtn.style.borderRadius= _systemPromptActive ? '6px' : '';

  if (_systemPromptActive && _systemPromptCache === null) {
    // Fetch once and cache
    try {
      const res = await fetch(`${API}/api/system_prompt`);
      _systemPromptCache = res.ok ? await res.text() : '';
    } catch { _systemPromptCache = ''; }
  }
  showToast(
    _systemPromptActive ? 'System prompt active' : 'System prompt disabled',
    _systemPromptActive ? 'success' : 'info'
  );
});

/* ── Drag & Drop Document Analysis ───────────────────────────────── */
const chatPanel  = document.querySelector('.chat-panel');
const dropOverlay = $('dropOverlay');

chatPanel.addEventListener('dragenter', e => {
  e.preventDefault();
  dropOverlay.classList.remove('hidden');
});

chatPanel.addEventListener('dragleave', e => {
  if (!chatPanel.contains(e.relatedTarget)) {
    dropOverlay.classList.add('hidden');
  }
});

chatPanel.addEventListener('dragover', e => {
  e.preventDefault();
  dropOverlay.classList.remove('hidden');
});

chatPanel.addEventListener('drop', async e => {
  e.preventDefault();
  dropOverlay.classList.add('hidden');

  const files = Array.from(e.dataTransfer.files);
  const file  = files[0];
  if (!file) return;

  const allowed = ['.pdf', '.png', '.jpg', '.jpeg', '.webp'];
  const ext     = '.' + file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('Unsupported file. Use PDF, PNG, JPG, or WEBP.', 'error');
    return;
  }

  appendMessage('user', `📎 ${file.name}`);
  const thinking = appendThinking();
  thinking.querySelector('.msg-bubble').textContent = `Analyzing ${file.name}…`;

  const form = new FormData();
  form.append('file', file);

  try {
    const res  = await fetch(`${API}/api/analyze_document`, { method: 'POST', body: form });
    const data = await res.json();
    thinking.remove();

    if (!res.ok) {
      appendMessage('assistant', `Analysis failed: ${data.detail || 'unknown error'}`);
      return;
    }

    renderHITLCard(data.extracted_data, data.pages_analysed);
  } catch (err) {
    thinking.remove();
    appendMessage('assistant', 'Document analysis failed — network error.');
  }
});

/* ── HITL Card ────────────────────────────────────────────────────── */
function renderHITLCard(extracted, pages) {
  const msg = document.createElement('div');
  msg.className = 'chat-msg assistant';

  const card = document.createElement('div');
  card.className = 'hitl-card';

  const title = document.createElement('div');
  title.className = 'hitl-title';
  title.textContent = `Extracted from ${pages} page${pages !== 1 ? 's' : ''} — review before saving`;

  const dataEl = document.createElement('pre');
  dataEl.className = 'hitl-data';
  dataEl.textContent = JSON.stringify(extracted, null, 2);

  const actions = document.createElement('div');
  actions.className = 'hitl-actions';

  const confirmBtn = document.createElement('button');
  confirmBtn.className = 'btn-sm';
  confirmBtn.textContent = 'Confirm & Save';

  const discardBtn = document.createElement('button');
  discardBtn.className = 'btn-sm-ghost';
  discardBtn.textContent = 'Discard';

  actions.appendChild(confirmBtn);
  actions.appendChild(discardBtn);
  card.appendChild(title);
  card.appendChild(dataEl);
  card.appendChild(actions);
  msg.appendChild(card);
  chatMessages.appendChild(msg);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Discard
  discardBtn.addEventListener('click', () => {
    msg.remove();
    appendMessage('assistant', 'Data discarded. Nothing was saved.');
  });

  // Confirm & Save all entries
  confirmBtn.addEventListener('click', async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Saving…';

    const errors   = [];
    const saved    = [];
    const entries  = [];

    for (const [type, items] of Object.entries(extracted)) {
      if (!Array.isArray(items)) continue;
      const knownTypes = ['payables', 'receivables', 'assets'];
      if (!knownTypes.includes(type)) continue;
      const singular = type === 'payables' ? 'payable' : type === 'receivables' ? 'receivable' : 'asset';
      for (const item of items) {
        entries.push({ entry_type: singular, data: item });
      }
    }

    for (const entry of entries) {
      try {
        const res = await fetch(`${API}/api/add_entry`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify(entry)
        });
        if (res.ok) {
          saved.push(entry.entry_type);
        } else {
          const d = await res.json();
          errors.push(`${entry.entry_type}: ${d.detail}`);
        }
      } catch (e) {
        errors.push(`${entry.entry_type}: network error`);
      }
    }

    msg.remove();

    if (saved.length) {
      const counts = saved.reduce((acc, t) => { acc[t] = (acc[t] || 0) + 1; return acc; }, {});
      const summary = Object.entries(counts).map(([t, n]) => `${n} ${t}(s)`).join(', ');
      appendMessage('assistant', `Saved: ${summary}.${errors.length ? ' Some errors: ' + errors.join('; ') : ''}`);
      await loadDashboard();
    } else {
      appendMessage('assistant', `Save failed: ${errors.join('; ')}`);
    }
  });
}

/* ── XSS escape ───────────────────────────────────────────────────── */
function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ── Init ─────────────────────────────────────────────────────────── */
loadDashboard();
// Refresh every 60 seconds
setInterval(loadDashboard, 60_000);