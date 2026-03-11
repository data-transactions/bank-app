/* dashboard.js — User dashboard logic */

let currentAccount = null;

async function init() {
  const payload = requireAuth();
  if (!payload) return;

  // Load account + transactions
  await Promise.all([loadAccount(), loadTransactions()]);

  // Sidebar nav
  setupNav();
  // Tab switching (deposit/withdraw/transfer)
  setupTabs();
  // Forms
  setupForms();
}

async function loadAccount() {
  try {
    currentAccount = await apiGet('/api/accounts/me');
    document.getElementById('balance').textContent = formatCurrency(currentAccount.balance);
    document.getElementById('accountNumber').textContent = maskAccount(currentAccount.account_number);
  } catch (err) {
    console.error('Account load failed:', err);
  }
}

// Load user name from JWT
function loadUserName() {
  // name comes from a separate call but we can use token
  const payload = parseJwt(getToken());
  // We'll fetch from the account owner's name via admin endpoint isn't available
  // Use a separate GET /api/accounts/me which returns account data only
  // So we grab name from JWT sub only — need a /api/users/me endpoint
  // Fall back to email prefix
  document.getElementById('userName').textContent = 'there';
}

async function loadTransactions() {
  const tbody = document.getElementById('txBody');
  try {
    const txs = await apiGet('/api/transactions/?limit=20');
    if (!txs.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No transactions yet. Make your first deposit!</td></tr>';
      return;
    }
    tbody.innerHTML = txs.map(tx => {
      const isCredit = tx.receiver_account_id === currentAccount?.id;
      const sign = (tx.transaction_type === 'deposit' || isCredit) ? '+' : '-';
      const color = sign === '+' ? 'var(--success)' : 'var(--danger)';
      return `<tr>
        <td>${formatDate(tx.created_at)}</td>
        <td>${typeBadge(tx.transaction_type)}</td>
        <td>${tx.description || '–'}</td>
        <td style="color:${color};font-weight:600">${sign}${formatCurrency(tx.amount)}</td>
        <td>${statusBadge(tx.status)}</td>
      </tr>`;
    }).join('');
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Failed to load transactions.</td></tr>';
  }
}

function maskAccount(num) {
  if (!num) return '––––––––––';
  return num.slice(0, 2) + '•'.repeat(num.length - 4) + num.slice(-4);
}

function setupNav() {
  const items = document.querySelectorAll('.nav-item[href]');
  items.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      items.forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      const target = item.getAttribute('href').replace('#', '');
      if (target === 'overview' || target === 'transactions') {
        document.getElementById('section-overview').style.display = '';
        document.getElementById('section-transfer').style.display = 'none';
      } else {
        document.getElementById('section-overview').style.display = 'none';
        document.getElementById('section-transfer').style.display = '';
      }
    });
  });
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`)?.classList.add('active');
    });
  });
}

function setupForms() {
  // Deposit
  document.getElementById('depositForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('depBtn');
    const errBox = document.getElementById('depError');
    const sucBox = document.getElementById('depSuccess');
    hideAlert(errBox); hideAlert(sucBox);
    const amount = parseFloat(document.getElementById('depAmount').value);
    if (!amount || amount <= 0) { showAlert(errBox, 'Enter a valid amount.'); return; }
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    try {
      const res = await apiPost('/api/transactions/deposit', { amount });
      showAlert(sucBox, `Deposited ${formatCurrency(amount)}. New balance: ${formatCurrency(res.balance_after)}`, 'success');
      document.getElementById('depAmount').value = '';
      currentAccount.balance = res.balance_after;
      document.getElementById('balance').textContent = formatCurrency(res.balance_after);
      await loadTransactions();
    } catch (err) {
      showAlert(errBox, err.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Deposit';
    }
  });

  // Withdraw
  document.getElementById('withdrawForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('wdBtn');
    const errBox = document.getElementById('wdError');
    const sucBox = document.getElementById('wdSuccess');
    hideAlert(errBox); hideAlert(sucBox);
    const amount = parseFloat(document.getElementById('wdAmount').value);
    if (!amount || amount <= 0) { showAlert(errBox, 'Enter a valid amount.'); return; }
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    try {
      const res = await apiPost('/api/transactions/withdraw', { amount });
      showAlert(sucBox, `Withdrew ${formatCurrency(amount)}. New balance: ${formatCurrency(res.balance_after)}`, 'success');
      document.getElementById('wdAmount').value = '';
      currentAccount.balance = res.balance_after;
      document.getElementById('balance').textContent = formatCurrency(res.balance_after);
      await loadTransactions();
    } catch (err) {
      showAlert(errBox, err.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Withdraw';
    }
  });

  // Transfer
  document.getElementById('transferForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('trBtn');
    const errBox = document.getElementById('trError');
    const sucBox = document.getElementById('trSuccess');
    hideAlert(errBox); hideAlert(sucBox);
    const receiver_account_number = document.getElementById('trAccount').value.trim();
    const amount = parseFloat(document.getElementById('trAmount').value);
    const description = document.getElementById('trDesc').value.trim() || null;
    if (!receiver_account_number) { showAlert(errBox, 'Enter a recipient account number.'); return; }
    if (!amount || amount <= 0) { showAlert(errBox, 'Enter a valid amount.'); return; }
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>';
    try {
      const res = await apiPost('/api/transactions/transfer', { receiver_account_number, amount, description });
      showAlert(sucBox, `Sent ${formatCurrency(amount)} to ${receiver_account_number}. Balance: ${formatCurrency(res.balance_after)}`, 'success');
      document.getElementById('trAccount').value = '';
      document.getElementById('trAmount').value = '';
      document.getElementById('trDesc').value = '';
      currentAccount.balance = res.balance_after;
      document.getElementById('balance').textContent = formatCurrency(res.balance_after);
    } catch (err) {
      showAlert(errBox, err.message);
    } finally {
      btn.disabled = false; btn.textContent = 'Send Money';
    }
  });
}

document.addEventListener('DOMContentLoaded', init);
