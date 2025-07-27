// Configuration globale
const config = {
    refreshInterval: 5000,
    chartTheme: {
        paper_bgcolor: '#212529',
        plot_bgcolor: '#343a40',
        font: { color: '#ffffff' },
        xaxis: {
            gridcolor: '#495057',
            zerolinecolor: '#495057'
        },
        yaxis: {
            gridcolor: '#495057',
            zerolinecolor: '#495057'
        }
    }
};

let refreshTimer;
let isConnected = false;

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return 'N/A';
    return parseFloat(num).toFixed(decimals);
}

function formatCurrency(num, decimals = 2) {
    if (num === null || num === undefined) return '$0.00';
    return '$' + parseFloat(num).toFixed(decimals);
}

function formatPercentage(num, decimals = 1) {
    if (num === null || num === undefined) return '0.0%';
    return parseFloat(num).toFixed(decimals) + '%';
}

function getColorClass(value) {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return 'text-muted';
}

function showNotification(message, type = 'info') {
    const toast = document.getElementById('notification-toast');
    const toastMessage = document.getElementById('toast-message');
    const toastHeader = toast.querySelector('.toast-header');
    const colors = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    };
    toastHeader.className = `toast-header ${colors[type] || colors.info}`;
    toastMessage.textContent = message;
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    const lastUpdateElement = document.getElementById('last-update');
    if (connected) {
        statusElement.textContent = 'Connected';
        statusElement.className = 'badge bg-success me-2';
        lastUpdateElement.textContent = new Date().toLocaleTimeString();
        isConnected = true;
    } else {
        statusElement.textContent = 'Disconnected';
        statusElement.className = 'badge bg-danger me-2';
        isConnected = false;
    }
}

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        updateConnectionStatus(false);
        throw error;
    }
}

async function controlAgent(action) {
    try {
        const response = await fetch('/api/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        const result = await response.json();
        if (response.ok) {
            showNotification(`Action ${action} executée avec succès`, 'success');
        } else {
            showNotification(`Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showNotification(`Erreur réseau: ${error.message}`, 'error');
    }
}

async function updateMetrics() {
    try {
        const metrics = await fetchAPI('/api/metrics');
        updateConnectionStatus(true);
        const cardsHtml = `
            <div class="col-md-2">
                <div class="card bg-dark border-success">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-wallet text-success"></i> Balance
                        </h5>
                        <h3 class="card-text">${formatCurrency(metrics.balance)}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-dark border-${metrics.daily_pnl >= 0 ? 'success' : 'danger'}">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-chart-line"></i> PnL Jour
                        </h5>
                        <h3 class="card-text ${getColorClass(metrics.daily_pnl)}">${formatCurrency(metrics.daily_pnl)}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-dark border-info">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-percentage"></i> Win Rate
                        </h5>
                        <h3 class="card-text text-info">${formatPercentage(metrics.win_rate)}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-dark border-warning">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-chart-pie"></i> Positions
                        </h5>
                        <h3 class="card-text text-warning">${metrics.open_positions}</h3>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-dark border-${metrics.status === 'active' ? 'success' : 'secondary'}">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-power-off"></i> Status
                        </h5>
                        <h3 class="card-text ${metrics.status === 'active' ? 'text-success' : 'text-secondary'}">
                            ${metrics.status.toUpperCase()}
                        </h3>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card bg-dark border-primary">
                    <div class="card-body text-center">
                        <h5 class="card-title">
                            <i class="fas fa-lever"></i> Levier
                        </h5>
                        <h3 class="card-text text-primary">x${metrics.leverage}</h3>
                    </div>
                </div>
            </div>`;
        document.getElementById('metrics-cards').innerHTML = cardsHtml;
    } catch (error) {
        console.error('Error updating metrics:', error);
    }
}

async function updateEquityChart() {
    try {
        const equityData = await fetchAPI('/api/equity_curve?hours=24');
        if (equityData.length === 0) return;
        const trace = {
            x: equityData.map(p => p.timestamp),
            y: equityData.map(p => p.equity),
            type: 'scatter',
            mode: 'lines',
            name: 'Equity',
            line: { color: '#28a745', width: 2 }
        };
        const layout = {
            ...config.chartTheme,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { ...config.chartTheme.xaxis, title: 'Time' },
            yaxis: { ...config.chartTheme.yaxis, title: 'USDT' },
            showlegend: false
        };
        Plotly.newPlot('equity-chart', [trace], layout, { responsive: true });
    } catch (error) {
        console.error('Error updating equity chart:', error);
    }
}

async function updatePerformanceChart() {
    try {
        const data = await fetchAPI('/api/performance?days=7');
        if (data.length === 0) return;
        const trace = {
            x: data.map(p => p.date),
            y: data.map(p => p.pnl),
            type: 'bar',
            name: 'PnL Quotidien',
            marker: { color: data.map(p => p.pnl >= 0 ? '#28a745' : '#dc3545') }
        };
        const layout = {
            ...config.chartTheme,
            margin: { l: 60, r: 20, t: 20, b: 40 },
            xaxis: { ...config.chartTheme.xaxis, title: 'Date' },
            yaxis: { ...config.chartTheme.yaxis, title: 'PnL (USDT)' },
            showlegend: false
        };
        Plotly.newPlot('performance-chart', [trace], layout, { responsive: true });
    } catch (error) {
        console.error('Error updating performance chart:', error);
    }
}

async function updatePositions() {
    try {
        const positions = await fetchAPI('/api/positions');
        const tbody = document.getElementById('positions-tbody');
        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Aucune position</td></tr>';
            return;
        }
        const rows = positions.map(pos => `
            <tr>
                <td>${pos.symbol}</td>
                <td><span class="badge bg-${pos.side === 'LONG' ? 'success' : 'danger'}">${pos.side}</span></td>
                <td>${formatNumber(pos.size, 4)}</td>
                <td>${formatCurrency(pos.entry_price)}</td>
                <td class="${getColorClass(pos.unrealized_pnl)}">${formatCurrency(pos.unrealized_pnl)}</td>
                <td class="${getColorClass(pos.unrealized_pnl_pct)}">${formatPercentage(pos.unrealized_pnl_pct)}</td>
            </tr>
        `).join('');
        tbody.innerHTML = rows;
    } catch (error) {
        console.error('Error updating positions:', error);
    }
}

async function updateTrades() {
    try {
        const trades = await fetchAPI('/api/trades?limit=10');
        const tbody = document.getElementById('trades-tbody');
        if (trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Aucun trade</td></tr>';
            return;
        }
        const rows = trades.map(t => {
            const exitTime = new Date(t.exit_time).toLocaleTimeString();
            return `
                <tr>
                    <td>${exitTime}</td>
                    <td><span class="badge bg-${t.side === 'LONG' ? 'success' : 'danger'}">${t.side}</span></td>
                    <td>${formatCurrency(t.entry_price)}</td>
                    <td>${formatCurrency(t.exit_price)}</td>
                    <td class="${getColorClass(t.pnl)}">${formatCurrency(t.pnl)}</td>
                    <td class="${getColorClass(t.pnl_pct)}">${formatPercentage(t.pnl_pct)}</td>
                </tr>
            `;
        }).join('');
        tbody.innerHTML = rows;
    } catch (error) {
        console.error('Error updating trades:', error);
    }
}

async function updateLogs() {
    try {
        const logs = await fetchAPI('/api/logs?lines=50');
        const container = document.getElementById('logs-container');
        if (logs.length === 0) {
            container.innerHTML = '<div class="text-muted">Aucun log disponible</div>';
            return;
        }
        const logsHtml = logs.map(log => {
            const time = new Date(log.timestamp).toLocaleTimeString();
            const levelColors = { INFO: 'text-info', WARNING: 'text-warning', ERROR: 'text-danger', DEBUG: 'text-secondary' };
            return `
                <div class="log-entry">
                    <span class="text-muted">[${time}]</span>
                    <span class="${levelColors[log.level] || 'text-light'}">${log.level}</span>
                    <span class="text-light">: ${log.message}</span>
                </div>
            `;
        }).join('');
        container.innerHTML = logsHtml;
        container.scrollTop = container.scrollHeight;
    } catch (error) {
        console.error('Error updating logs:', error);
    }
}

async function refreshDashboard() {
    await Promise.all([
        updateMetrics(),
        updateEquityChart(),
        updatePerformanceChart(),
        updatePositions(),
        updateTrades(),
        updateLogs()
    ]);
}

function startRefreshTimer() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(refreshDashboard, config.refreshInterval);
}

function stopRefreshTimer() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    refreshDashboard();
    startRefreshTimer();
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            stopRefreshTimer();
        } else {
            startRefreshTimer();
            refreshDashboard();
        }
    });
    window.addEventListener('resize', function() {
        setTimeout(() => {
            Plotly.Plots.resize('equity-chart');
            Plotly.Plots.resize('performance-chart');
        }, 100);
    });
});

window.addEventListener('beforeunload', function() {
    stopRefreshTimer();
});
