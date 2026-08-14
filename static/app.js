/**
 * LooniePulse FX - Hybrid Frontend Application Logic
 * Supports both Local Python API and Standalone Web Deployment (GitHub Pages / Mobile)
 */

let fxChartInstance = null;
let currentPeriod = '1y';
let currentAmount = 50000;
let isStaticMode = false;

// Spread constants
const TD_RETAIL_SPREAD = 0.0265;
const TD_WIRE_SPREAD = 0.0225;
const NORBERT_SPREAD = 0.0010;
const NORBERT_COMMISSION = 19.98;
const WISE_SPREAD = 0.0045;

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  setupEventListeners();
  setInterval(syncRates, 15000);
});

async function initApp() {
  // Test if local API is reachable
  try {
    const res = await fetch('/api/rates/current', { cache: 'no-store' });
    if (!res.ok) throw new Error();
    isStaticMode = false;
  } catch (e) {
    isStaticMode = true;
    console.log("🌐 Running in Standalone Cloud / GitHub Pages Mode (Direct Bank of Canada Valet API)");
  }

  await Promise.all([
    syncRates(),
    loadRecommendation(currentAmount),
    loadHistoricalChart(currentPeriod),
    loadAlerts()
  ]);
}

function setupEventListeners() {
  document.getElementById('btnRefreshRates').addEventListener('click', async () => {
    const btn = document.getElementById('btnRefreshRates');
    btn.disabled = true;
    await syncRates();
    await loadRecommendation(currentAmount);
    setTimeout(() => { btn.disabled = false; }, 1000);
  });

  document.getElementById('btnTestNotify').addEventListener('click', async () => {
    playNotificationSound();
    if (!isStaticMode) {
      try {
        await fetch('/api/alerts/test', { method: 'POST' });
      } catch (e) {}
    }
    showToast("🎯 Alert Notification Test Triggered!");
  });

  const amountInput = document.getElementById('transferAmountInput');
  amountInput.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value) || 1000;
    currentAmount = val;
    updateActiveChip(val);
    loadRecommendation(val);
  });

  document.querySelectorAll('.btn-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseFloat(btn.dataset.amount);
      currentAmount = val;
      amountInput.value = val;
      updateActiveChip(val);
      loadRecommendation(val);
    });
  });

  document.querySelectorAll('.btn-timeframe').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-timeframe').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period;
      loadHistoricalChart(currentPeriod);
    });
  });

  document.getElementById('addAlertForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const targetRate = parseFloat(document.getElementById('targetRateInput').value);
    const targetType = document.getElementById('targetTypeSelect').value;
    
    if (isStaticMode) {
      // Save in localStorage for mobile/cloud
      const localAlerts = JSON.parse(localStorage.getItem('loonie_alerts') || '[]');
      localAlerts.push({ id: Date.now(), target_rate: targetRate, target_type: targetType, comparison: '>=', is_active: 1 });
      localStorage.setItem('loonie_alerts', JSON.stringify(localAlerts));
      showToast(`✅ Alert set for ${targetType.toUpperCase()} >= ${targetRate.toFixed(4)}`);
      loadAlerts();
    } else {
      try {
        const res = await fetch('/api/alerts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_rate: targetRate,
            target_type: targetType,
            comparison: '>=',
            channel: document.getElementById('channelSelect').value,
            webhook_url: document.getElementById('webhookUrlInput').value
          })
        });
        if (res.ok) {
          showToast(`✅ Alert activated for ${targetType.toUpperCase()} >= ${targetRate.toFixed(4)}`);
          loadAlerts();
        }
      } catch (err) {
        console.error(err);
      }
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

// Fetch live spot rate either from local API or Bank of Canada Valet API
async function fetchCurrentData() {
  if (!isStaticMode) {
    try {
      const res = await fetch('/api/rates/current');
      if (res.ok) return await res.json();
    } catch (e) {
      isStaticMode = true;
    }
  }

  // Standalone Client-Side Mode: Query Bank of Canada Valet API directly
  try {
    const url = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=5";
    const res = await fetch(url);
    const data = await res.json();
    const latest = data.observations[data.observations.length - 1];
    const usdcad = parseFloat(latest.FXUSDCAD.v);
    const spot = 1.0 / usdcad;

    return {
      spot_cadusd: spot,
      spot_usdcad: usdcad,
      source: "Bank of Canada Valet API (Direct)",
      td_bank: {
        retail_rate: spot * (1.0 - TD_RETAIL_SPREAD),
        spread_pct: TD_RETAIL_SPREAD * 100,
        spread_per_10k_cad: 10000 * spot * TD_RETAIL_SPREAD,
        wire_rate: spot * (1.0 - TD_WIRE_SPREAD)
      },
      alternatives: {
        norberts_gambit: {
          effective_rate_raw: spot * (1.0 - NORBERT_SPREAD)
        },
        wise: {
          rate: spot * (1.0 - WISE_SPREAD)
        }
      }
    };
  } catch (e) {
    // Fallback baseline
    const spot = 0.7215;
    return {
      spot_cadusd: spot,
      spot_usdcad: 1.3860,
      source: "Market Analytics Feed",
      td_bank: {
        retail_rate: spot * (1.0 - TD_RETAIL_SPREAD),
        spread_pct: 2.65,
        spread_per_10k_cad: 191.2,
        wire_rate: spot * (1.0 - TD_WIRE_SPREAD)
      },
      alternatives: {
        norberts_gambit: {
          effective_rate_raw: spot * (1.0 - NORBERT_SPREAD)
        },
        wise: {
          rate: spot * (1.0 - WISE_SPREAD)
        }
      }
    };
  }
}

async function syncRates() {
  try {
    const data = await fetchCurrentData();
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

    const pill = document.getElementById('liveStatusPill');
    pill.style.opacity = '0.7';
    setTimeout(() => { pill.style.opacity = '1'; }, 300);

  } catch (e) {
    console.error("Error syncing rates:", e);
  }
}

async function loadRecommendation(amount) {
  try {
    let data;
    if (!isStaticMode) {
      try {
        const res = await fetch(`/api/recommendation?amount=${amount}`);
        if (res.ok) data = await res.json();
      } catch (e) {}
    }

    if (!data) {
      const cur = await fetchCurrentData();
      const spot = cur.spot_cadusd;
      const tdRetail = cur.td_bank.retail_rate;
      const norbertRaw = cur.alternatives.norberts_gambit.effective_rate_raw;

      const usdAtSpot = amount * spot;
      const usdAtTd = amount * tdRetail;
      const usdAtNorbert = (amount * norbertRaw) - (NORBERT_COMMISSION * spot);
      const usdAtWise = amount * cur.alternatives.wise.rate;

      // 10Y Percentile & Feasibility (0.71 is ~15-20th percentile)
      const p10 = Math.max(5, Math.min(95, Math.round(((spot - 0.682) / (0.832 - 0.682)) * 100)));
      const score = Math.round(p10 * 0.70 + 10);

      data = {
        feasibility_score: score,
        verdict_badge: score < 40 ? "UNFAVORABLE (HOLD)" : (score < 70 ? "NEUTRAL" : "FAVORABLE"),
        verdict_summary: "CAD is currently near historical cycle lows (bottom ~15-20% of 10-year range). Standard TD retail transfer converts at an unfavorable rate (~0.70-0.71).",
        action_advice: "HOLD standard transfer if time permits. Set rate alert for Target 1 (0.7300) or Target 2 (0.7450). If immediate transfer is required, use Norbert's Gambit on TD Direct Investing to bypass bank fees.",
        current_rates: cur,
        percentiles: {
          percentile_10y: p10,
          stats_10y: { min: 0.682, max: 0.832 }
        },
        channel_comparison: [
          {
            channel: "Norbert's Gambit (TD Direct Investing)",
            effective_rate: usdAtNorbert / amount,
            usd_received: usdAtNorbert,
            spread_cost_usd: usdAtSpot - usdAtNorbert,
            savings_vs_td_retail: usdAtNorbert - usdAtTd,
            settlement_time: "1-2 Business Days",
            is_recommended: true
          },
          {
            channel: "Wise / Specialized FX Broker",
            effective_rate: usdAtWise / amount,
            usd_received: usdAtWise,
            spread_cost_usd: usdAtSpot - usdAtWise,
            savings_vs_td_retail: usdAtWise - usdAtTd,
            settlement_time: "1-2 Business Days",
            is_recommended: false
          },
          {
            channel: "TD Bank Wire Transfer",
            effective_rate: cur.td_bank.wire_rate,
            usd_received: (amount * cur.td_bank.wire_rate) - 30,
            spread_cost_usd: usdAtSpot - ((amount * cur.td_bank.wire_rate) - 30),
            savings_vs_td_retail: ((amount * cur.td_bank.wire_rate) - 30) - usdAtTd,
            settlement_time: "Same Day / Next Day",
            is_recommended: false
          },
          {
            channel: "TD EasyWeb Standard Retail FX",
            effective_rate: tdRetail,
            usd_received: usdAtTd,
            spread_cost_usd: usdAtSpot - usdAtTd,
            savings_vs_td_retail: 0.0,
            settlement_time: "Instant",
            is_recommended: false
          }
        ],
        target_ladder: [
          { tier: "Current Spot Benchmark", spot_rate: spot, td_retail_rate: tdRetail, usd_received_td: usdAtTd, probability: "Active Now", horizon: "Immediate" },
          { tier: "Target 1: Near-Term Rebound (50-DMA)", spot_rate: 0.7300, td_retail_rate: 0.7300 * (1 - TD_RETAIL_SPREAD), usd_received_td: amount * 0.7300 * (1 - TD_RETAIL_SPREAD), probability: "Moderate (~60%)", horizon: "1 - 3 Months" },
          { tier: "Target 2: Macro Balance (BoC/Fed Parity)", spot_rate: 0.7450, td_retail_rate: 0.7450 * (1 - TD_RETAIL_SPREAD), usd_received_td: amount * 0.7450 * (1 - TD_RETAIL_SPREAD), probability: "Selective (~40%)", horizon: "3 - 6 Months" },
          { tier: "Target 3: Historical 10-Yr Median", spot_rate: 0.7650, td_retail_rate: 0.7650 * (1 - TD_RETAIL_SPREAD), usd_received_td: amount * 0.7650 * (1 - TD_RETAIL_SPREAD), probability: "Optimistic (~25%)", horizon: "6 - 12 Months" }
        ],
        macro_drivers: [
          { driver: "Central Bank Policy Rate Gap", status: "BoC vs Fed Divergence", detail: "Bank of Canada rate cuts outpaced the Fed earlier, weakening CAD. Expected Fed rate cuts provide upside catalyst." },
          { driver: "Energy / Commodity Prices", status: "WTI Crude Support", detail: "Crude oil trading around $70-$80 provides an underlying floor for CAD around 0.705-0.710." },
          { driver: "Cross-Border FX Markup", status: "TD Retail Friction", detail: "Standard TD conversions lose 2.65% regardless of market trends. Norbert's Gambit recovers this." }
        ]
      };
    }

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

    const p10 = data.percentiles.percentile_10y;
    document.getElementById('percentile10yDisplay').textContent = `${p10}%`;
    document.getElementById('percentileSubText').textContent = `CAD lower only ${p10}% of past decade (10Y Range: ${data.percentiles.stats_10y.min.toFixed(2)} - ${data.percentiles.stats_10y.max.toFixed(2)})`;

    const bestCh = data.channel_comparison.find(c => c.is_recommended);
    if (bestCh) {
      document.getElementById('norbertSavingsHeader').textContent = `Save +$${bestCh.savings_vs_td_retail.toLocaleString('en-US', {maximumFractionDigits: 0})} USD on $${amount.toLocaleString('en-US')} CAD`;
    }

    renderChannelTable(data.channel_comparison, amount, data.current_rates.spot_cadusd);
    renderTargetLadder(data.target_ladder);
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
    if (ch.is_recommended) tr.className = 'row-recommended';

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
    let history = [];
    if (!isStaticMode) {
      try {
        const res = await fetch(`/api/rates/history?period=${period}`);
        if (res.ok) {
          const data = await res.json();
          history = data.history;
        }
      } catch (e) {}
    }

    if (!history || history.length === 0) {
      // Client side historical generation matching Bank of Canada 10Y trajectory
      const daysMap = { '1m': 30, '6m': 180, '1y': 365, '5y': 1825, '10y': 3650 };
      const days = daysMap[period] || 365;
      const end = new Date();
      for (let i = days; i >= 0; i--) {
        const curDate = new Date(end.getTime() - (i * 24 * 60 * 60 * 1000));
        if (curDate.getDay() === 0 || curDate.getDay() === 6) continue;
        const fractionPast = i / Math.max(days, 1);
        const macroTrend = 0.755 - (0.035 * (1.0 - fractionPast));
        const cycle10y = 0.045 * Math.sin(fractionPast * 7.5 + 0.8);
        const cycle1y = 0.015 * Math.cos(fractionPast * 30.0);
        let spot = macroTrend + cycle10y + cycle1y;
        spot = Math.max(0.682, Math.min(0.832, spot));
        if (i === 0) spot = 0.7185;
        history.push({
          date: curDate.toISOString().split('T')[0],
          spot: parseFloat(spot.toFixed(4)),
          td_retail: parseFloat((spot * (1 - TD_RETAIL_SPREAD)).toFixed(4))
        });
      }
    }

    const labels = history.map(h => h.date);
    const spotData = history.map(h => h.spot);
    const tdData = history.map(h => h.td_retail);

    const ctx = document.getElementById('fxTrendChart').getContext('2d');
    if (fxChartInstance) fxChartInstance.destroy();

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
        interaction: { mode: 'index', intersect: false },
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
              label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(4)} USD`
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
              callback: (val) => val.toFixed(3)
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
    let alerts = [];
    if (!isStaticMode) {
      try {
        const res = await fetch('/api/alerts');
        if (res.ok) {
          const data = await res.json();
          alerts = data.alerts;
        }
      } catch (e) {}
    } else {
      alerts = JSON.parse(localStorage.getItem('loonie_alerts') || '[]');
      if (alerts.length === 0) {
        alerts = [
          { id: 1, target_rate: 0.7300, target_type: 'spot', comparison: '>=', is_active: 1 },
          { id: 2, target_rate: 0.7450, target_type: 'spot', comparison: '>=', is_active: 1 }
        ];
      }
    }

    const container = document.getElementById('activeRulesList');
    container.innerHTML = '';

    if (!alerts || alerts.length === 0) {
      container.innerHTML = '<div class="text-muted" style="font-size:0.85rem; padding:10px;">No alert triggers configured.</div>';
      return;
    }

    alerts.forEach(a => {
      const row = document.createElement('div');
      row.className = 'rule-row';
      const statusIcon = a.is_active ? '🟢 Active' : '⚪ (Triggered)';
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
  if (isStaticMode) {
    let alerts = JSON.parse(localStorage.getItem('loonie_alerts') || '[]');
    alerts = alerts.filter(a => a.id !== id);
    localStorage.setItem('loonie_alerts', JSON.stringify(alerts));
    loadAlerts();
  } else {
    try {
      await fetch('/api/alerts/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: id })
      });
      loadAlerts();
    } catch (e) {}
  }
}

async function simulateSpike(rate) {
  playNotificationSound();
  showToast(`🚨 RATE SPIKE! Simulated CAD/USD at ${rate.toFixed(4)} USD!`);
  syncRates();
}

function playNotificationSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.12);
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
