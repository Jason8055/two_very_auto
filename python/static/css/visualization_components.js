// Two Very Auto v2.0 - 실시간 시각화 컴포넌트
// Chart.js 기반 동적 차트 및 대시보드 컴포넌트

class VisualizationManager {
    constructor() {
        this.charts = new Map();
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Chart.js 기본 설정
        Chart.defaults.font.family = "'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = 'var(--text-primary)';
        Chart.defaults.borderColor = 'var(--border-primary)';
        
        this.init();
    }
    
    async init() {
        console.log('📊 시각화 매니저 초기화 시작');
        
        // WebSocket 연결
        await this.connectWebSocket();
        
        // 차트 컨테이너 설정
        this.setupChartContainers();
        
        // 이벤트 리스너 설정
        this.setupEventListeners();
        
        console.log('✅ 시각화 매니저 초기화 완료');
    }
    
    async connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/charts`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('🔗 차트 WebSocket 연결됨');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.showConnectionStatus('connected');
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 차트 WebSocket 연결 해제');
                this.isConnected = false;
                this.showConnectionStatus('disconnected');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ 차트 WebSocket 오류:', error);
                this.showConnectionStatus('error');
            };
            
        } catch (error) {
            console.error('WebSocket 연결 실패:', error);
            this.showConnectionStatus('error');
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('🚫 최대 재연결 시도 횟수 초과');
            return;
        }
        
        this.reconnectAttempts++;
        const delay = Math.pow(2, this.reconnectAttempts) * 1000; // 지수 백오프
        
        console.log(`🔄 ${delay/1000}초 후 재연결 시도 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial_charts':
                this.initializeAllCharts(data.charts);
                break;
                
            case 'chart_update':
                this.updateChart(data.chart_type, data.data);
                break;
                
            case 'game_update':
                this.handleGameUpdate(data);
                break;
                
            case 'system_update':
                this.updateSystemMetrics(data);
                break;
                
            case 'alert':
                this.handleAlert(data.alert);
                break;
                
            default:
                console.log('알 수 없는 메시지 타입:', data.type);
        }
    }
    
    setupChartContainers() {
        const chartsHtml = `
            <div class="dashboard-grid">
                <!-- 실시간 메트릭 카드 -->
                <div class="metrics-row">
                    <div class="metric-card" id="total-games-card">
                        <div class="metric-icon">🎲</div>
                        <div class="metric-content">
                            <div class="metric-value" id="total-games">0</div>
                            <div class="metric-label">총 게임</div>
                        </div>
                        <div class="metric-trend" id="games-trend">+0</div>
                    </div>
                    
                    <div class="metric-card" id="total-pairs-card">
                        <div class="metric-icon">🎯</div>
                        <div class="metric-content">
                            <div class="metric-value" id="total-pairs">0</div>
                            <div class="metric-label">총 페어</div>
                        </div>
                        <div class="metric-trend" id="pairs-trend">+0</div>
                    </div>
                    
                    <div class="metric-card" id="pair-rate-card">
                        <div class="metric-icon">📊</div>
                        <div class="metric-content">
                            <div class="metric-value" id="pair-rate">0%</div>
                            <div class="metric-label">페어율</div>
                        </div>
                        <div class="metric-trend" id="rate-trend">+0%</div>
                    </div>
                    
                    <div class="metric-card" id="active-tables-card">
                        <div class="metric-icon">🏓</div>
                        <div class="metric-content">
                            <div class="metric-value" id="active-tables">0</div>
                            <div class="metric-label">활성 테이블</div>
                        </div>
                        <div class="metric-trend" id="tables-trend">+0</div>
                    </div>
                </div>
                
                <!-- 주요 차트 -->
                <div class="charts-row">
                    <div class="chart-container large">
                        <h3>페어 발생 타임라인</h3>
                        <canvas id="pair-timeline-chart"></canvas>
                        <div class="chart-loading" id="timeline-loading">데이터 로드 중...</div>
                    </div>
                    
                    <div class="chart-container medium">
                        <h3>시간별 통계</h3>
                        <canvas id="hourly-stats-chart"></canvas>
                        <div class="chart-loading" id="hourly-loading">데이터 로드 중...</div>
                    </div>
                </div>
                
                <!-- 추가 차트 -->
                <div class="charts-row">
                    <div class="chart-container medium">
                        <h3>테이블별 비교</h3>
                        <canvas id="table-comparison-chart"></canvas>
                        <div class="chart-loading" id="comparison-loading">데이터 로드 중...</div>
                    </div>
                    
                    <div class="chart-container small">
                        <h3>페어 타입 분포</h3>
                        <canvas id="pair-distribution-chart"></canvas>
                        <div class="chart-loading" id="distribution-loading">데이터 로드 중...</div>
                    </div>
                </div>
                
                <!-- 라이브 피드 -->
                <div class="live-feed-container">
                    <h3>실시간 활동</h3>
                    <div class="live-feed" id="live-feed">
                        <div class="feed-item placeholder">
                            <span class="feed-time">--:--</span>
                            <span class="feed-content">실시간 데이터를 기다리는 중...</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 차트 컨테이너를 페이지에 추가
        const container = document.getElementById('charts-container') || document.body;
        container.innerHTML = chartsHtml;
        
        // 스타일 추가
        this.addChartStyles();
    }
    
    addChartStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .dashboard-grid {
                display: grid;
                gap: 20px;
                padding: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .metrics-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }
            
            .metric-card {
                background: var(--card-bg);
                border: 1px solid var(--border-primary);
                border-radius: 12px;
                padding: 20px;
                display: flex;
                align-items: center;
                gap: 16px;
                transition: transform var(--transition-fast), box-shadow var(--transition-fast);
            }
            
            .metric-card:hover {
                transform: translateY(-2px);
                box-shadow: var(--shadow-lg);
            }
            
            .metric-icon {
                font-size: 2rem;
                flex-shrink: 0;
            }
            
            .metric-content {
                flex: 1;
            }
            
            .metric-value {
                font-size: 1.75rem;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1;
            }
            
            .metric-label {
                font-size: 0.875rem;
                color: var(--text-secondary);
                margin-top: 4px;
            }
            
            .metric-trend {
                font-size: 0.875rem;
                font-weight: 600;
                padding: 4px 8px;
                border-radius: 4px;
                background: var(--success-color);
                color: white;
            }
            
            .metric-trend.negative {
                background: var(--error-color);
            }
            
            .charts-row {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
            }
            
            .chart-container {
                background: var(--card-bg);
                border: 1px solid var(--border-primary);
                border-radius: 12px;
                padding: 20px;
                position: relative;
                min-height: 300px;
            }
            
            .chart-container.large {
                grid-column: 1 / -1;
                min-height: 400px;
            }
            
            .chart-container.medium {
                min-height: 350px;
            }
            
            .chart-container.small {
                min-height: 300px;
            }
            
            .chart-container h3 {
                margin-bottom: 16px;
                color: var(--text-primary);
                font-size: 1.125rem;
                font-weight: 600;
            }
            
            .chart-loading {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: var(--text-tertiary);
                font-size: 0.875rem;
            }
            
            .live-feed-container {
                background: var(--card-bg);
                border: 1px solid var(--border-primary);
                border-radius: 12px;
                padding: 20px;
            }
            
            .live-feed {
                max-height: 200px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .feed-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 12px;
                background: var(--bg-secondary);
                border-radius: 6px;
                font-size: 0.875rem;
                animation: slideIn 0.3s ease-out;
            }
            
            .feed-item.pair-alert {
                background: rgba(239, 68, 68, 0.1);
                border-left: 3px solid var(--error-color);
            }
            
            .feed-time {
                color: var(--text-tertiary);
                font-weight: 600;
                min-width: 60px;
            }
            
            .feed-content {
                color: var(--text-primary);
            }
            
            .connection-status {
                position: fixed;
                top: 20px;
                right: 80px;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                z-index: 1000;
                transition: all var(--transition-normal);
            }
            
            .connection-status.connected {
                background: rgba(16, 185, 129, 0.2);
                color: var(--success-color);
                border: 1px solid rgba(16, 185, 129, 0.3);
            }
            
            .connection-status.disconnected {
                background: rgba(239, 68, 68, 0.2);
                color: var(--error-color);
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
            
            .connection-status.error {
                background: rgba(245, 158, 11, 0.2);
                color: var(--warning-color);
                border: 1px solid rgba(245, 158, 11, 0.3);
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            @media (max-width: 768px) {
                .dashboard-grid {
                    padding: 16px;
                    gap: 16px;
                }
                
                .charts-row {
                    grid-template-columns: 1fr;
                }
                
                .chart-container {
                    min-height: 250px;
                }
                
                .metric-card {
                    padding: 16px;
                }
                
                .metric-value {
                    font-size: 1.5rem;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    initializeAllCharts(chartsData) {
        console.log('📊 모든 차트 초기화 시작');
        
        // 각 차트 초기화
        if (chartsData.timeline) {
            this.createChart('pair-timeline-chart', chartsData.timeline);
            document.getElementById('timeline-loading').style.display = 'none';
        }
        
        if (chartsData.hourly) {
            this.createChart('hourly-stats-chart', chartsData.hourly);
            document.getElementById('hourly-loading').style.display = 'none';
        }
        
        if (chartsData.comparison) {
            this.createChart('table-comparison-chart', chartsData.comparison);
            document.getElementById('comparison-loading').style.display = 'none';
        }
        
        if (chartsData.distribution) {
            this.createChart('pair-distribution-chart', chartsData.distribution);
            document.getElementById('distribution-loading').style.display = 'none';
        }
        
        // 메트릭 업데이트
        if (chartsData.metrics) {
            this.updateMetrics(chartsData.metrics);
        }
    }
    
    createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas not found: ${canvasId}`);
            return;
        }
        
        // 기존 차트가 있으면 파괴
        if (this.charts.has(canvasId)) {
            this.charts.get(canvasId).destroy();
        }
        
        // 테마에 따른 색상 조정
        this.applyThemeToChartConfig(config);
        
        // 차트 생성
        const chart = new Chart(canvas, config);
        this.charts.set(canvasId, chart);
        
        console.log(`📈 차트 생성 완료: ${canvasId}`);
    }
    
    applyThemeToChartConfig(config) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' ||
                      (document.documentElement.getAttribute('data-theme') === 'auto' && 
                       window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        const textColor = isDark ? '#f8fafc' : '#1e293b';
        const gridColor = isDark ? '#383c44' : '#e2e8f0';
        
        // 전역 색상 업데이트
        if (config.options && config.options.plugins && config.options.plugins.legend) {
            config.options.plugins.legend.labels = {
                ...config.options.plugins.legend.labels,
                color: textColor
            };
        }
        
        if (config.options && config.options.scales) {
            Object.keys(config.options.scales).forEach(scaleKey => {
                const scale = config.options.scales[scaleKey];
                scale.ticks = { ...scale.ticks, color: textColor };
                scale.grid = { ...scale.grid, color: gridColor };
                if (scale.title) {
                    scale.title.color = textColor;
                }
            });
        }
    }
    
    updateChart(chartType, data) {
        const chartMapping = {
            'timeline': 'pair-timeline-chart',
            'hourly': 'hourly-stats-chart',
            'comparison': 'table-comparison-chart',
            'distribution': 'pair-distribution-chart'
        };
        
        const canvasId = chartMapping[chartType];
        if (!canvasId || !this.charts.has(canvasId)) {
            console.warn(`차트를 찾을 수 없음: ${chartType}`);
            return;
        }
        
        const chart = this.charts.get(canvasId);
        
        // 데이터 업데이트
        chart.data = data.data;
        chart.options = { ...chart.options, ...data.options };
        
        // 테마 적용 후 업데이트
        this.applyThemeToChartConfig({ data: chart.data, options: chart.options });
        chart.update('active');
    }
    
    updateMetrics(metrics) {
        // 총 게임 수
        if (metrics.total_games !== undefined) {
            document.getElementById('total-games').textContent = metrics.total_games.toLocaleString();
        }
        
        // 총 페어 수
        if (metrics.total_pairs !== undefined) {
            document.getElementById('total-pairs').textContent = metrics.total_pairs.toLocaleString();
        }
        
        // 페어율
        if (metrics.pair_rate !== undefined) {
            document.getElementById('pair-rate').textContent = `${metrics.pair_rate}%`;
        }
        
        // 활성 테이블
        if (metrics.active_tables !== undefined) {
            document.getElementById('active-tables').textContent = metrics.active_tables;
        }
        
        console.log('📊 메트릭 업데이트 완료');
    }
    
    handleGameUpdate(data) {
        const game = data.game;
        const alerts = data.alerts || [];
        
        // 라이브 피드에 게임 정보 추가
        this.addToLiveFeed({
            time: new Date(game.timestamp).toLocaleTimeString(),
            content: `${game.table_name}: 게임 #${game.game_id}${game.has_pair ? ' 🎯 ' + game.pair_type : ''}`,
            isAlert: game.has_pair
        });
        
        // 알림 처리
        alerts.forEach(alert => this.handleAlert(alert));
        
        // 라이브 통계 업데이트
        if (data.live_stats) {
            this.updateMetrics(data.live_stats);
        }
    }
    
    updateSystemMetrics(data) {
        if (data.live_stats) {
            this.updateMetrics(data.live_stats);
        }
        
        // 테이블 개요 업데이트 등 추가 처리
        console.log('🔄 시스템 메트릭 업데이트');
    }
    
    handleAlert(alert) {
        // 라이브 피드에 알림 추가
        this.addToLiveFeed({
            time: new Date(alert.timestamp).toLocaleTimeString(),
            content: `🚨 ${alert.message}`,
            isAlert: true
        });
        
        // 브라우저 알림 (권한이 있는 경우)
        if (Notification.permission === 'granted') {
            new Notification('Two Very Auto 알림', {
                body: alert.message,
                icon: '/static/icons/icon-192x192.png',
                tag: 'pair-alert'
            });
        }
        
        // 진동 (모바일 기기)
        if ('vibrate' in navigator) {
            navigator.vibrate([200, 100, 200]);
        }
    }
    
    addToLiveFeed(feedItem) {
        const liveFeed = document.getElementById('live-feed');
        if (!liveFeed) return;
        
        // 기존 placeholder 제거
        const placeholder = liveFeed.querySelector('.placeholder');
        if (placeholder) {
            placeholder.remove();
        }
        
        // 새 피드 아이템 생성
        const feedElement = document.createElement('div');
        feedElement.className = `feed-item ${feedItem.isAlert ? 'pair-alert' : ''}`;
        feedElement.innerHTML = `
            <span class="feed-time">${feedItem.time}</span>
            <span class="feed-content">${feedItem.content}</span>
        `;
        
        // 맨 위에 추가
        liveFeed.insertBefore(feedElement, liveFeed.firstChild);
        
        // 최대 20개 항목 유지
        const items = liveFeed.querySelectorAll('.feed-item');
        if (items.length > 20) {
            items[items.length - 1].remove();
        }
    }
    
    showConnectionStatus(status) {
        let statusElement = document.querySelector('.connection-status');
        
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.className = 'connection-status';
            document.body.appendChild(statusElement);
        }
        
        statusElement.className = `connection-status ${status}`;
        
        const statusText = {
            'connected': '🟢 연결됨',
            'disconnected': '🔴 연결 끊김',
            'error': '🟡 오류'
        };
        
        statusElement.textContent = statusText[status] || '⚪ 알 수 없음';
    }
    
    setupEventListeners() {
        // 테마 변경 감지
        const observer = new MutationObserver(() => {
            // 모든 차트에 테마 적용
            this.charts.forEach((chart, canvasId) => {
                this.applyThemeToChartConfig({ data: chart.data, options: chart.options });
                chart.update('none');
            });
        });
        
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });
        
        // 미디어 쿼리 변경 감지 (auto 테마용)
        window.matchMedia('(prefers-color-scheme: dark)').addListener(() => {
            if (document.documentElement.getAttribute('data-theme') === 'auto') {
                this.charts.forEach((chart, canvasId) => {
                    this.applyThemeToChartConfig({ data: chart.data, options: chart.options });
                    chart.update('none');
                });
            }
        });
        
        // 창 크기 변경 시 차트 리사이즈
        window.addEventListener('resize', () => {
            this.charts.forEach(chart => {
                chart.resize();
            });
        });
    }
    
    // 공개 메서드
    refreshAllCharts() {
        console.log('🔄 모든 차트 새로고침');
        this.charts.forEach(chart => {
            chart.update('active');
        });
    }
    
    exportChartAsImage(chartType) {
        const chartMapping = {
            'timeline': 'pair-timeline-chart',
            'hourly': 'hourly-stats-chart',
            'comparison': 'table-comparison-chart',
            'distribution': 'pair-distribution-chart'
        };
        
        const canvasId = chartMapping[chartType];
        if (!canvasId || !this.charts.has(canvasId)) {
            console.warn(`차트를 찾을 수 없음: ${chartType}`);
            return;
        }
        
        const chart = this.charts.get(canvasId);
        const url = chart.toBase64Image();
        
        // 다운로드 링크 생성
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chartType}_chart_${new Date().toISOString().slice(0, 10)}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    destroy() {
        console.log('🗑️ 시각화 매니저 정리');
        
        // WebSocket 연결 종료
        if (this.websocket) {
            this.websocket.close();
        }
        
        // 모든 차트 파괴
        this.charts.forEach(chart => {
            chart.destroy();
        });
        this.charts.clear();
        
        // 연결 상태 표시 제거
        const statusElement = document.querySelector('.connection-status');
        if (statusElement) {
            statusElement.remove();
        }
    }
}

// 전역 인스턴스
let visualizationManager;

// DOM 로딩 완료 후 초기화
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        visualizationManager = new VisualizationManager();
    });
} else {
    visualizationManager = new VisualizationManager();
}

// 전역 접근을 위한 export
window.visualizationManager = visualizationManager;