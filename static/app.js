/**
 * LooniePulse FX - Frontend Application Logic
 * Reactive Dashboard, Dynamic Chart Studio, Transfer Calculator, & Alert Engine
 */

let fxChartInstance = null;
let currentPeriod = '1y';
let currentAmount = 50000;

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  setupEventListeners();
  // Auto-sync rates every 15 seconds
  setInterval(syncRates, 15000);
});

async function initApp() {
  await Promise.all([
    syncRates(),
    loadRecommendation(currentAmount),
    loadHistoricalChart(currentPeriod),
    loadAlerts()
  ]);
}

function setupEventListeners() {
  // Sync button
  document.getElementById('btnRefreshRates').addEventListener('click', async () => {
    const btn = document.getElementById('btnRefreshRates');
    btn.disabled = true;
    await syncRates();
    await loadRecommendation(currentAmount);
    setTimeout(() => { btn.disabled = false; }, 1000);
  });

  // Test macOS Alert
  document.getElementById('btnTestNotify').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/alerts/test', { method: 'POST' });
      const data = await res.json();
      playNotificationSound();
      showToast("🎯 Alert Dispatched to macOS Notification Center!");
    } catch (e) {
      console.error("Failed to send test notification", e);
    }
  });

  // Amount input
  const amountInput = document.getElementById('transferAmountInput');
  amountInput.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value) || 1000;
    currentAmount = val;
    updateActiveChip(val);
    loadRecommendation(val);
  });

  // Quick Amount Chips
  document.querySelectorAll('.btn-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseFloat(btn.dataset.amount);
      currentAmount = val;
      amountInput.value = val;
      updateActiveChip(val);
      loadRecommendation(val);
    });
  });

  // Timeframe buttons for chart
  document.querySelectorAll('.btn-timeframe').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-timeframe').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period;
      loadHistoricalChart(currentPeriod);
    });
  });

  // Notification channel select
  document.getElementById('channelSelect').addEventListener('change', (e) => {
    const webhookGroup = document.getElementById('webhookInputGroup');
    if (e.target.value === 'webhook' || e.target.value === 'all') {
      // Show if webhook is explicitly needed
      webhookGroup.style.display = e.target.value === 'webhook' ? 'flex' : 'none';
    } else {
      webhookGroup.style.display = 'none';
    }
  });

  // Add Alert Form
  document.getElementById('addAlertForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const targetRate = parseFloat(document.getElementById('targetRateInput').value);
    const targetType = document.getElementById('targetTypeSelect').value;
    const channel = document.getElementById('channelSelect').value;
    const webhookUrl = document.getElementById('webhookUrlInput').value;

    try {
      const res = await fetch('/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_rate: targetRate,
          target_type: targetType,
          comparison: '>=',
          channel: channel,
          webhook_url: webhookUrl
        })
      });
      if (res.ok) {
        showToast(`✅ Alert activated for ${targetType.toUpperCase()} >= ${targetRate.toFixed(4)}`);
        loadAlerts();
      }
    } catch (err) {
      console.error("Failed to add alert", err);
    }
  });
}

function updateActiveChip(val) {
  document.querySelectorAll('.btn-chip').forEach(btn => {
    if (parseFloat(btn.dataset.amount) === val) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

async function syncRates() {
  try {
    const res = await fetch('/api/rates/current');
    const data = await res.json();

    const spot = data.spot_cadusd;
    const tdRetail = data.td_bank.retail_rate;
    const tdSpread = data.td_bank.spread_pct;
    const tdCost10k = data.td_bank.spread_per_10k_cad;
    const norbert = data.alternatives.norberts_gambit.effective_rate_raw;

    document.getElementById('spotRateDisplay').textContent = spot.toFixed(4);
    document.getElementById('spotInverseDisplay').textContent = `1 USD = ${data.spot_usdcad.toFixed(4)} CAD`;
    document.getElementById('spotSource').textContent = data.source;

    document.getElementById('tdRetailRateDisplay').textContent = tdRetail.toFixed(4);
    document.getElementById('tdSpreadTag').textContent = `-${tdSpread.toFixed(2)}% Spread`;
    document.getElementById('tdCostPer10k').textContent = `Spread Loss: ~$${tdCost10k.toFixed(0)} USD / $10k CAD`;

    document.getElementById('norbertRateDisplay').textContent = norbert.toFixed(4);
    
    // Animate subtle live pulse
    const pill = document.getElementById('liveStatusPill');
    pill.style.opacity = '0.7';
    setTimeout(() => { pill.style.opacity = '1'; }, 300);

  } catch (e) {
    console.error("Error syncing rates:", e);
  }
}

async function loadRecommendation(amount) {
  try {
    const res = await fetch(`/api/recommendation?amount=${amount}`);
    const data = await res.json();

    // Verdict Banner
    const pill = document.getElementById('verdictPill');
    pill.textContent = data.verdict_badge;
    if (data.feasibility_score < 40) {
      pill.className = 'verdict-pill badge-danger';
    } else if (data.feasibility_score < 70) {
      pill.className = 'verdict-pill badge-warning';
    } else {
      pill.className = 'verdict-pill badge-success';
    }

    document.getElementById('feasibilityMeterFill').style.width = `${data.feasibility_score}%`;
    document.getElementById('feasibilityScore').textContent = `${data.feasibility_score} / 100`;

    document.getElementById('verdictTitle').textContent = `Rate Assessment (${data.current_rates.spot_cadusd.toFixed(4)} CAD/USD): ${data.verdict_badge}`;
    document.getElementById('verdictDesc').textContent = data.verdict_summary;
    document.getElementById('verdictAdvice').textContent = data.action_advice;

    // Percentile Widget
    const p10 = data.percentiles.percentile_10y;
    document.getElementById('percentile10yDisplay').textContent = `${p10}%`;
    document.getElementById('percentileSubText').textContent = `CAD lower only ${p10}% of past decade (10Y Range: ${data.percentiles.stats_10y.min.toFixed(2)} - ${data.percentiles.stats_10y.max.toFixed(2)})`;

    // Norbert savings headline
    const bestCh = data.channel_comparison.find(c => c.is_recommended);
    if (bestCh) {
      document.getElementById('norbertSavingsHeader').textContent = `Save +$${bestCh.savings_vs_td_retail.toLocaleString('en-US', {maximumFractionDigits: 0})} USD on $${amount.toLocaleString('en-US')} CAD`;
    }

    // Channel Comparison Table
    renderChannelTable(data.channel_comparison, amount, data.current_rates.spot_cadusd);

    // Target Ladder
    renderTargetLadder(data.target_ladder);

    // Macro Drivers
    renderMacroDrivers(data.macro_drivers);

  } catch (e) {
    console.error("Error loading recommendations:", e);
  }
}

function renderChannelTable(channels, amount, spot) {
  const tbody = document.getElementById('channelTableBody');
  tbody.innerHTML = '';

  channels.forEach(ch => {
    const tr = document.createElement('tr');
    if (ch.is_recommended) {
      tr.className = 'row-recommended';
    }

    const starBadge = ch.is_recommended ? '<span class="rec-star-badge">⭐ BEST VALUE</span>' : '';
    const gainClass = ch.savings_vs_td_retail > 0 ? 'text-success font-weight-bold' : 'text-muted';
    const gainText = ch.savings_vs_td_retail > 0 
      ? `+$${ch.savings_vs_td_retail.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})} USD`
      : 'Baseline (0)';

    tr.innerHTML = `
      <td class="channel-name-cell">
        <span>${ch.channel}</span>
        ${starBadge}
      </td>
      <td class="mono-cell">${ch.effective_rate.toFixed(4)}</td>
      <td class="mono-cell highlight-green">$${ch.usd_received.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td class="mono-cell text-danger">-$${ch.spread_cost_usd.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
      <td class="mono-cell ${gainClass}">${gainText}</td>
      <td><span class="source-tag">${ch.settlement_time}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderTargetLadder(ladder) {
  const container = document.getElementById('targetLadderList');
  container.innerHTML = '';

  ladder.forEach(item => {
    const div = document.createElement('div');
    div.className = 'ladder-item';
    div.innerHTML = `
      <div>
        <div class="ladder-tier">${item.tier}</div>
        <div class="ladder-prob">${item.probability} • Horizon: ${item.horizon}</div>
      </div>
      <div class="ladder-rates">
        <div class="ladder-spot">${item.spot_rate.toFixed(4)} USD</div>
        <div class="ladder-usd">TD Yield: $${item.usd_received_td.toLocaleString('en-US')}</div>
      </div>
    `;
    container.appendChild(div);
  });
}

function renderMacroDrivers(drivers) {
  const container = document.getElementById('macroDriversList');
  container.innerHTML = '';

  drivers.forEach(d => {
    const div = document.createElement('div');
    div.className = 'macro-card';
    div.innerHTML = `
      <div class="macro-header">
        <span class="macro-title">${d.driver}</span>
        <span class="macro-status badge-neutral">${d.status}</span>
      </div>
      <p class="macro-detail">${d.detail}</p>
    `;
    container.appendChild(div);
  });
}

async function loadHistoricalChart(period) {
  try {
    const res = await fetch(`/api/rates/history?period=${period}`);
    const data = await res.json();
    const history = data.history;

    const labels = history.map(h => h.date);
    const spotData = history.map(h => h.spot);
    const tdData = history.map(h => h.td_retail);

    const ctx = document.getElementById('fxTrendChart').getContext('2d');

    if (fxChartInstance) {
      fxChartInstance.destroy();
    }

    fxChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Interbank Spot (CAD/USD)',
            data: spotData,
            borderColor: 'hsl(190, 85%, 48%)',
            backgroundColor: 'hsla(190, 85%, 48%, 0.08)',
            borderWidth: 2,
            pointRadius: period === '1m' ? 3 : 0,
            fill: true,
            tension: 0.2
          },
          {
            label: 'TD Retail Rate (-2.65%)',
            data: tdData,
            borderColor: 'hsl(352, 85%, 60%)',
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointRadius: 0,
            fill: false,
            tension: 0.2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'hsl(220, 24%, 12%)',
            titleColor: 'hsl(210, 30%, 96%)',
            bodyColor: 'hsl(215, 16%, 72%)',
            borderColor: 'hsl(217, 18%, 28%)',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: function(context) {
                return `${context.dataset.label}: ${context.parsed.y.toFixed(4)} USD`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: 'hsla(217, 18%, 20%, 0.4)' },
            ticks: { color: 'hsl(215, 14%, 52%)', maxTicksLimit: 8 }
          },
          y: {
            grid: { color: 'hsla(217, 18%, 20%, 0.4)' },
            ticks: {
              color: 'hsl(215, 14%, 52%)',
              callback: function(value) { return value.toFixed(3); }
            }
          }
        }
      }
    });

  } catch (e) {
    console.error("Error loading chart:", e);
  }
}

async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts');
    const data = await res.json();
    const container = document.getElementById('activeRulesList');
    container.innerHTML = '';

    if (!data.alerts || data.alerts.length === 0) {
      container.innerHTML = '<div class="text-muted" style="font-size:0.85rem; padding:10px;">No alert triggers configured.</div>';
      return;
    }

    data.alerts.forEach(a => {
      const row = document.createElement('div');
      row.className = 'rule-row';
      const statusIcon = a.is_active ? '🟢' : '⚪ (Triggered)';
      row.innerHTML = `
        <div>
          <span class="rule-desc">${a.target_type.toUpperCase()} ${a.comparison} ${a.target_rate.toFixed(4)}</span>
          <span class="source-tag" style="margin-left: 8px;">${statusIcon}</span>
        </div>
        <div class="rule-actions">
          <button class="btn-icon" onclick="deleteAlertRule(${a.id})" title="Delete rule">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      `;
      container.appendChild(row);
    });

  } catch (e) {
    console.error("Error loading alerts:", e);
  }
}

async function deleteAlertRule(id) {
  try {
    await fetch('/api/alerts/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: id })
    });
    loadAlerts();
  } catch (e) {
    console.error("Failed to delete alert", e);
  }
}

async function simulateSpike(rate) {
  try {
    const res = await fetch('/api/simulate-rate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spot_rate: rate })
    });
    const data = await res.json();
    playNotificationSound();
    
    if (data.triggered_alerts && data.triggered_alerts.length > 0) {
      showToast(`🚨 RATE SPIKE! Triggered ${data.triggered_alerts.length} Alert(s) at ${rate.toFixed(4)} USD!`);
    } else {
      showToast(`🧪 Simulated Rate at ${rate.toFixed(4)} USD (No threshold crossed).`);
    }
    loadAlerts();
    syncRates();
  } catch (e) {
    console.error("Simulation error", e);
  }
}

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.12); // A5
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {}
}

function showToast(msg) {
  let toast = document.getElementById('appToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'appToast';
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.right = '24px';
    toast.style.backgroundColor = 'hsl(218, 22%, 16%)';
    toast.style.color = 'hsl(210, 30%, 96%)';
    toast.style.border = '1px solid hsl(190, 85%, 48%)';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '8px';
    toast.style.boxShadow = '0 8px 24px rgba(0,0,0,0.6)';
    toast.style.zIndex = '9999';
    toast.style.fontSize = '0.9rem';
    toast.style.fontWeight = '600';
    toast.style.transition = 'opacity 0.3s ease';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}
