/* admin.js — Admin dashboard logic */

let allTransactions = [];

async function init() {
  const payload = requireAdmin();
  if (!payload) return;

  document.getElementById('adminName').textContent = 'Admin';

  // Sidebar section switching
  document.querySelectorAll('.nav-item[data-section]').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const target = item.dataset.section;
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      document.querySelectorAll('section[id^="section-"]').forEach(s => s.style.display = 'none');
      document.getElementById(`section-${target}`).style.display = '';
      if (target === 'users') loadUsers();
      if (target === 'transactions') loadTransactions();
    });
  });

  // Load stats on start
  loadStats();
}

async function loadStats() {
  try {
    const data = await apiGet('/api/admin/stats');
    document.getElementById('statUsers').textContent = data.total_users.toLocaleString();
    document.getElementById('statVolume').textContent = formatCurrency(data.total_volume);
    document.getElementById('statTxns').textContent = data.total_transactions.toLocaleString();
  } catch (err) {
    console.error('Stats load failed:', err);
  }
}

async function loadUsers() {
  const tbody = document.getElementById('usersBody');
  tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Loading…</td></tr>';
  try {
    const users = await apiGet('/api/admin/users');
    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No users found.</td></tr>';
      return;
    }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${escHtml(u.full_name)}</td>
        <td>${escHtml(u.email)}</td>
        <td style="font-family:monospace;font-size:0.85rem">${u.account_number || '–'}</td>
        <td>${formatCurrency(u.balance)}</td>
        <td>${u.is_admin ? '<span class="badge badge-info">Admin</span>' : '<span class="badge badge-muted">User</span>'}</td>
        <td>${formatDate(u.created_at)}</td>
        <td>
          ${u.is_admin ? '<span style="color:var(--text-muted);font-size:0.8rem">–</span>' :
            `<button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id}, this)">Delete</button>`}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">Failed to load users.</td></tr>`;
  }
}

async function deleteUser(userId, btn) {
  if (!confirm('Are you sure you want to permanently delete this user and their account?')) return;
  btn.disabled = true;
  btn.textContent = '…';
  try {
    await apiDelete(`/api/admin/users/${userId}`);
    const row = btn.closest('tr');
    row.style.opacity = '0';
    row.style.transition = 'opacity 0.3s';
    setTimeout(() => row.remove(), 300);
    // Refresh stats
    loadStats();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
    btn.textContent = 'Delete';
  }
}

async function loadTransactions() {
  const tbody = document.getElementById('txnsBody');
  tbody.innerHTML = '<tr><td colspan="8" class="empty-state">Loading…</td></tr>';
  try {
    allTransactions = await apiGet('/api/admin/transactions');
    renderTransactions();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Failed to load transactions.</td></tr>`;
  }
}

function renderTransactions() {
  const typeF   = document.getElementById('typeFilter').value;
  const statusF = document.getElementById('statusFilter').value;
  const tbody   = document.getElementById('txnsBody');

  const filtered = allTransactions.filter(tx => {
    if (typeF   && tx.transaction_type !== typeF)   return false;
    if (statusF && tx.status           !== statusF) return false;
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No transactions match the selected filters.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(tx => `
    <tr>
      <td>${formatDate(tx.created_at)}</td>
      <td>${typeBadge(tx.transaction_type)}</td>
      <td style="font-family:monospace;font-size:0.82rem">${tx.sender_account_number || '–'}</td>
      <td style="font-family:monospace;font-size:0.82rem">${tx.receiver_account_number || '–'}</td>
      <td style="font-weight:600">${formatCurrency(tx.amount)}</td>
      <td>${escHtml(tx.description || '–')}</td>
      <td>${statusBadge(tx.status)}</td>
      <td style="font-family:monospace;font-size:0.75rem;color:var(--text-muted)">${tx.reference_code}</td>
    </tr>
  `).join('');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
  init();

  // Wire up filters
  document.getElementById('typeFilter')?.addEventListener('change', renderTransactions);
  document.getElementById('statusFilter')?.addEventListener('change', renderTransactions);
});
