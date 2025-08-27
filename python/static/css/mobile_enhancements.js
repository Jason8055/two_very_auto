// Two Very Auto v2.0 - 모바일 향상 기능
// PWA 모바일 최적화 및 네이티브 앱 수준 UX 제공

class MobileEnhancements {
    constructor() {
        this.isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        this.isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        this.isAndroid = /Android/.test(navigator.userAgent);
        this.currentTheme = 'auto';
        
        // 진동 지원 여부
        this.supportsVibration = 'vibrate' in navigator;
        
        // 알림 권한 상태
        this.notificationPermission = 'default';
        
        // 터치 제스처 상태
        this.touchStartY = 0;
        this.isPullToRefreshEnabled = true;
        
        this.init();
        console.log('📱 Mobile Enhancements initialized');
    }
    
    init() {
        this.setupThemeSystem();
        this.setupVibrationFeedback();
        this.setupPullToRefresh();
        this.setupTouchOptimizations();
        this.setupNotificationPermission();
        this.setupPWABehaviors();
        this.setupSafeArea();
        this.setupNetworkAwareness();
    }
    
    // =====================================
    // 테마 시스템
    // =====================================
    setupThemeSystem() {
        // 저장된 테마 설정 로드
        this.currentTheme = localStorage.getItem('theme') || 'auto';
        this.applyTheme(this.currentTheme);
        
        // 테마 토글 버튼 추가
        this.addThemeToggle();
        
        // 시스템 테마 변경 감지
        window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
            if (this.currentTheme === 'auto') {
                this.applyTheme('auto');
            }
        });
    }
    
    addThemeToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'theme-toggle';
        toggle.setAttribute('aria-label', '테마 전환');
        toggle.innerHTML = `
            <svg class="light-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <svg class="dark-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
            </svg>
            <svg class="auto-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
            </svg>
        `;
        
        toggle.addEventListener('click', () => {
            this.cycleTheme();
            this.vibrate('light');
        });
        
        document.body.appendChild(toggle);
    }
    
    cycleTheme() {
        const themes = ['light', 'dark', 'auto'];
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        
        this.currentTheme = themes[nextIndex];
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
        
        // 테마 변경 알림
        this.showToast(`🎨 ${this.getThemeName(this.currentTheme)} 테마로 변경되었습니다`);
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // 메타 테마 색상 업데이트
        const themeColorMeta = document.querySelector('meta[name="theme-color"]');
        if (themeColorMeta) {
            if (theme === 'dark' || (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                themeColorMeta.content = '#0f1419';
            } else {
                themeColorMeta.content = '#4f46e5';
            }
        }
    }
    
    getThemeName(theme) {
        const names = {
            'light': '라이트',
            'dark': '다크',  
            'auto': '자동'
        };
        return names[theme] || '자동';
    }
    
    // =====================================
    // 진동 피드백
    // =====================================
    setupVibrationFeedback() {
        if (!this.supportsVibration) {
            console.log('📱 Vibration not supported');
            return;
        }
        
        // 페어 알림에 진동 추가
        window.addEventListener('pair-detected', (event) => {
            this.vibrate('success');
        });
        
        // 버튼 클릭에 경량 진동
        document.addEventListener('click', (event) => {
            if (event.target.matches('button, .btn, .clickable')) {
                this.vibrate('light');
            }
        });
    }
    
    vibrate(type = 'light') {
        if (!this.supportsVibration) return;
        
        const patterns = {
            'light': [50],                    // 경량 진동
            'medium': [100],                  // 중간 진동
            'strong': [200],                  // 강한 진동
            'success': [100, 50, 100],        // 성공 패턴
            'error': [200, 100, 200, 100, 200], // 오류 패턴
            'notification': [100, 50, 100, 50, 100] // 알림 패턴
        };
        
        const pattern = patterns[type] || patterns['light'];
        navigator.vibrate(pattern);
    }
    
    // =====================================
    // Pull-to-Refresh 기능
    // =====================================
    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let pulling = false;
        const threshold = 100;
        
        // Pull-to-refresh 인디케이터 생성
        const refreshIndicator = document.createElement('div');
        refreshIndicator.className = 'pull-refresh-indicator';
        refreshIndicator.innerHTML = `
            <div class="refresh-spinner">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <polyline points="23 4 23 10 17 10"></polyline>
                    <polyline points="1 20 1 14 7 14"></polyline>
                    <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
            </div>
            <div class="refresh-text">새로고침하려면 당겨주세요</div>
        `;
        
        // 스타일 추가
        const style = document.createElement('style');
        style.textContent = `
            .pull-refresh-indicator {
                position: fixed;
                top: -80px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 1000;
                
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                
                padding: 16px;
                background: var(--card-bg);
                border-radius: 12px;
                box-shadow: var(--shadow-lg);
                
                transition: transform 0.3s ease;
                color: var(--text-primary);
            }
            
            .refresh-spinner svg {
                animation: spin 1s linear infinite;
            }
            
            .refresh-text {
                font-size: 0.75rem;
                white-space: nowrap;
            }
            
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            .pulling .pull-refresh-indicator {
                transform: translateX(-50%) translateY(0);
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(refreshIndicator);
        
        // 터치 이벤트 처리
        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0 && this.isPullToRefreshEnabled) {
                startY = e.touches[0].clientY;
                pulling = false;
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (startY === 0) return;
            
            currentY = e.touches[0].clientY;
            const pullDistance = currentY - startY;
            
            if (pullDistance > 0 && window.scrollY === 0) {
                pulling = true;
                const progress = Math.min(pullDistance / threshold, 1);
                
                document.body.classList.toggle('pulling', progress > 0.3);
                refreshIndicator.style.transform = `translateX(-50%) translateY(${Math.min(pullDistance * 0.5, 50)}px)`;
                
                if (progress >= 1) {
                    refreshIndicator.querySelector('.refresh-text').textContent = '놓으면 새로고침';
                } else {
                    refreshIndicator.querySelector('.refresh-text').textContent = '새로고침하려면 당겨주세요';
                }
            }
        }, { passive: true });
        
        document.addEventListener('touchend', () => {
            if (pulling) {
                const pullDistance = currentY - startY;
                
                if (pullDistance >= threshold) {
                    this.performRefresh();
                } else {
                    this.cancelPullRefresh();
                }
            }
            
            startY = 0;
            currentY = 0;
            pulling = false;
        });
    }
    
    async performRefresh() {
        const refreshIndicator = document.querySelector('.pull-refresh-indicator');
        refreshIndicator.querySelector('.refresh-text').textContent = '새로고침 중...';
        
        this.vibrate('medium');
        
        try {
            // 데이터 새로고침 API 호출
            const response = await fetch('/api/data', {
                method: 'GET',
                headers: { 'Cache-Control': 'no-cache' }
            });
            
            if (response.ok) {
                // 성공적인 새로고침
                window.location.reload();
            } else {
                throw new Error('새로고침 실패');
            }
        } catch (error) {
            console.error('Pull-to-refresh failed:', error);
            this.showToast('🔄 새로고침에 실패했습니다', 'error');
            this.cancelPullRefresh();
        }
    }
    
    cancelPullRefresh() {
        const refreshIndicator = document.querySelector('.pull-refresh-indicator');
        document.body.classList.remove('pulling');
        refreshIndicator.style.transform = 'translateX(-50%) translateY(-80px)';
        refreshIndicator.querySelector('.refresh-text').textContent = '새로고침하려면 당겨주세요';
    }
    
    // =====================================
    // 터치 최적화
    // =====================================
    setupTouchOptimizations() {
        // 더블탭 줌 방지 (PWA에서는 불필요)
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (event) => {
            const now = new Date().getTime();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        // 터치 스타일 최적화
        document.documentElement.style.setProperty('-webkit-tap-highlight-color', 'transparent');
        document.documentElement.style.setProperty('touch-action', 'manipulation');
        
        // 스와이프 제스처 (향후 확장용)
        this.setupSwipeGestures();
    }
    
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });
        
        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const diffX = startX - endX;
            const diffY = startY - endY;
            
            // 수평 스와이프가 수직보다 큰 경우
            if (Math.abs(diffX) > Math.abs(diffY)) {
                if (Math.abs(diffX) > 50) { // 최소 스와이프 거리
                    if (diffX > 0) {
                        // 왼쪽으로 스와이프
                        this.onSwipeLeft();
                    } else {
                        // 오른쪽으로 스와이프
                        this.onSwipeRight();
                    }
                }
            }
            
            startX = 0;
            startY = 0;
        });
    }
    
    onSwipeLeft() {
        // 향후 확장: 다음 페이지, 메뉴 닫기 등
        console.log('👈 Swipe left detected');
    }
    
    onSwipeRight() {
        // 향후 확장: 이전 페이지, 메뉴 열기 등
        console.log('👉 Swipe right detected');
    }
    
    // =====================================
    // 웹 푸시 알림
    // =====================================
    async setupNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('📱 Notifications not supported');
            return;
        }
        
        this.notificationPermission = Notification.permission;
        
        if (this.notificationPermission === 'default') {
            // 알림 권한 요청 버튼 표시
            this.showNotificationPrompt();
        }
    }
    
    showNotificationPrompt() {
        const prompt = document.createElement('div');
        prompt.className = 'notification-prompt';
        prompt.innerHTML = `
            <div class="prompt-content">
                <div class="prompt-icon">🔔</div>
                <div class="prompt-text">
                    <h3>알림 받기</h3>
                    <p>페어 발생 시 즉시 알림을 받으시겠습니까?</p>
                </div>
                <div class="prompt-actions">
                    <button class="btn btn-outline" onclick="this.closest('.notification-prompt').remove()">나중에</button>
                    <button class="btn btn-primary" onclick="mobileEnhancements.requestNotificationPermission()">허용</button>
                </div>
            </div>
        `;
        
        // 스타일 추가
        if (!document.querySelector('#notification-prompt-style')) {
            const style = document.createElement('style');
            style.id = 'notification-prompt-style';
            style.textContent = `
                .notification-prompt {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    right: 20px;
                    z-index: 1060;
                    
                    background: var(--card-bg);
                    border: 1px solid var(--border-primary);
                    border-radius: 12px;
                    box-shadow: var(--shadow-xl);
                    
                    animation: slideUp 0.3s ease-out;
                }
                
                .prompt-content {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 16px;
                }
                
                .prompt-icon {
                    font-size: 1.5rem;
                    flex-shrink: 0;
                }
                
                .prompt-text {
                    flex: 1;
                }
                
                .prompt-text h3 {
                    font-size: 1rem;
                    margin-bottom: 4px;
                    color: var(--text-primary);
                }
                
                .prompt-text p {
                    font-size: 0.875rem;
                    color: var(--text-secondary);
                    margin-bottom: 12px;
                }
                
                .prompt-actions {
                    display: flex;
                    gap: 8px;
                }
                
                .prompt-actions .btn {
                    padding: 8px 16px;
                    font-size: 0.75rem;
                }
                
                @keyframes slideUp {
                    from {
                        transform: translateY(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(prompt);
        
        // 10초 후 자동 숨김
        setTimeout(() => {
            if (prompt.parentNode) {
                prompt.remove();
            }
        }, 10000);
    }
    
    async requestNotificationPermission() {
        try {
            const permission = await Notification.requestPermission();
            this.notificationPermission = permission;
            
            if (permission === 'granted') {
                this.showToast('🔔 알림이 활성화되었습니다!', 'success');
                this.vibrate('success');
                
                // 테스트 알림 발송
                setTimeout(() => {
                    this.showNotification('🎯 Two Very Auto', '알림이 성공적으로 설정되었습니다!');
                }, 1000);
            } else {
                this.showToast('⚠️ 알림이 거부되었습니다', 'warning');
            }
            
            // 프롬프트 제거
            document.querySelector('.notification-prompt')?.remove();
            
        } catch (error) {
            console.error('Notification permission error:', error);
            this.showToast('❌ 알림 설정에 실패했습니다', 'error');
        }
    }
    
    showNotification(title, body, options = {}) {
        if (this.notificationPermission !== 'granted') return;
        
        const defaultOptions = {
            body: body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/badge-72x72.png',
            tag: 'two-very-auto',
            requireInteraction: false,
            vibrate: [200, 100, 200],
            data: {
                timestamp: new Date().toISOString(),
                url: window.location.origin
            }
        };
        
        const notification = new Notification(title, { ...defaultOptions, ...options });
        
        notification.onclick = () => {
            window.focus();
            notification.close();
        };
        
        // 5초 후 자동 닫기
        setTimeout(() => {
            notification.close();
        }, 5000);
    }
    
    // =====================================
    // PWA 특화 기능
    // =====================================
    setupPWABehaviors() {
        // 스탠드얼론 모드 감지 및 UI 조정
        if (this.isStandalone) {
            document.body.classList.add('standalone-mode');
            console.log('📱 Running in standalone mode');
        }
        
        // 설치 프롬프트 처리
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt();
        });
        
        // 앱 설치 완료 감지
        window.addEventListener('appinstalled', () => {
            console.log('📱 App installed successfully');
            this.showToast('📱 앱이 성공적으로 설치되었습니다!', 'success');
            this.vibrate('success');
        });
        
        // 온라인/오프라인 상태 감지
        window.addEventListener('online', () => {
            this.showToast('🌐 인터넷에 연결되었습니다', 'success');
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.showToast('📶 오프라인 모드로 전환되었습니다', 'info');
        });
    }
    
    showInstallPrompt() {
        if (!this.deferredPrompt) return;
        
        const prompt = document.createElement('div');
        prompt.className = 'install-prompt';
        prompt.innerHTML = `
            <div class="install-content">
                <div class="install-icon">📱</div>
                <div class="install-text">
                    <h3>앱 설치</h3>
                    <p>더 빠른 접근을 위해 홈 화면에 앱을 추가하세요!</p>
                </div>
                <div class="install-actions">
                    <button class="btn btn-outline" onclick="this.closest('.install-prompt').remove()">닫기</button>
                    <button class="btn btn-primary" onclick="mobileEnhancements.installApp()">설치</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(prompt);
    }
    
    async installApp() {
        if (!this.deferredPrompt) return;
        
        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('📱 User accepted the install prompt');
        } else {
            console.log('📱 User dismissed the install prompt');
        }
        
        this.deferredPrompt = null;
        document.querySelector('.install-prompt')?.remove();
    }
    
    // =====================================
    // Safe Area 처리
    // =====================================
    setupSafeArea() {
        // iOS Safe Area 변수를 CSS 커스텀 속성으로 설정
        const setSafeAreaVars = () => {
            const root = document.documentElement;
            
            // Safe area inset 값들을 CSS 변수로 설정
            if (CSS.supports('padding-top: env(safe-area-inset-top)')) {
                root.style.setProperty('--safe-area-top', 'env(safe-area-inset-top)');
                root.style.setProperty('--safe-area-right', 'env(safe-area-inset-right)');
                root.style.setProperty('--safe-area-bottom', 'env(safe-area-inset-bottom)');
                root.style.setProperty('--safe-area-left', 'env(safe-area-inset-left)');
            } else {
                // 폴백 값
                root.style.setProperty('--safe-area-top', '0px');
                root.style.setProperty('--safe-area-right', '0px');
                root.style.setProperty('--safe-area-bottom', '0px');
                root.style.setProperty('--safe-area-left', '0px');
            }
        };
        
        setSafeAreaVars();
        
        // 화면 회전 시 재설정
        window.addEventListener('orientationchange', () => {
            setTimeout(setSafeAreaVars, 100);
        });
    }
    
    // =====================================
    // 네트워크 인식 기능
    // =====================================
    setupNetworkAwareness() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            const updateNetworkInfo = () => {
                const effectiveType = connection.effectiveType;
                const saveData = connection.saveData;
                
                // 저속 연결 시 최적화
                if (effectiveType === 'slow-2g' || effectiveType === '2g' || saveData) {
                    document.body.classList.add('low-bandwidth');
                    this.showToast('📶 저속 연결이 감지되어 최적화 모드로 전환합니다', 'info');
                } else {
                    document.body.classList.remove('low-bandwidth');
                }
            };
            
            updateNetworkInfo();
            connection.addEventListener('change', updateNetworkInfo);
        }
    }
    
    // =====================================
    // 오프라인 데이터 동기화
    // =====================================
    async syncOfflineData() {
        if ('serviceWorker' in navigator && navigator.onLine) {
            try {
                const registration = await navigator.serviceWorker.ready;
                if (registration.sync) {
                    await registration.sync.register('background-sync');
                    console.log('📱 Background sync registered');
                }
            } catch (error) {
                console.error('Background sync registration failed:', error);
            }
        }
    }
    
    // =====================================
    // 유틸리티 함수들
    // =====================================
    showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // 스타일이 없는 경우 추가
        if (!document.querySelector('#toast-style')) {
            const style = document.createElement('style');
            style.id = 'toast-style';
            style.textContent = `
                .toast {
                    position: fixed;
                    bottom: 100px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 1070;
                    
                    padding: 12px 20px;
                    border-radius: 8px;
                    
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: white;
                    
                    max-width: 90vw;
                    text-align: center;
                    
                    animation: toastSlide 0.3s ease-out;
                    box-shadow: var(--shadow-lg);
                }
                
                .toast-info { background: var(--info-color); }
                .toast-success { background: var(--success-color); }
                .toast-warning { background: var(--warning-color); }
                .toast-error { background: var(--error-color); }
                
                @keyframes toastSlide {
                    from {
                        transform: translateX(-50%) translateY(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(-50%) translateY(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'toastSlide 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
    
    // 화면 업데이트 강제 (iOS Safari 버그 해결)
    forceRepaint() {
        const dummy = document.createElement('div');
        dummy.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 1px;
            height: 1px;
            background: transparent;
            pointer-events: none;
        `;
        document.body.appendChild(dummy);
        setTimeout(() => dummy.remove(), 1);
    }
    
    // 디바이스 정보 수집
    getDeviceInfo() {
        return {
            isStandalone: this.isStandalone,
            isIOS: this.isIOS,
            isAndroid: this.isAndroid,
            supportsVibration: this.supportsVibration,
            notificationPermission: this.notificationPermission,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            screen: {
                width: screen.width,
                height: screen.height,
                orientation: screen.orientation?.type || 'unknown'
            }
        };
    }
}

// 전역 인스턴스 생성
let mobileEnhancements;

// DOM 로딩 완료 후 초기화
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        mobileEnhancements = new MobileEnhancements();
    });
} else {
    mobileEnhancements = new MobileEnhancements();
}

// 전역 접근을 위한 export
window.mobileEnhancements = mobileEnhancements;