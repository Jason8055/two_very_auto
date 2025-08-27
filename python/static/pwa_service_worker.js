/* ================================================
   Two Very Auto v2.0 - Enhanced PWA Service Worker
   SQLite + WebSocket + ML 기반 시스템
   ================================================ */

const CACHE_NAME = 'two-very-auto-v2-0';
const OFFLINE_URL = '/pwa_offline.html';
const DB_CACHE = 'two-very-auto-db-cache';

// 캐시할 정적 자원들 (v2.0)
const STATIC_CACHE_URLS = [
    '/',
    '/static/css/modern_design_system.css',
    '/static/css/modern_components.css',
    '/static/css/modern_sidebar.css',
    '/static/css/modern_charts.css',
    '/static/css/mobile_responsive.css',
    OFFLINE_URL
];

// 캐시할 API 경로들 (v2.0 - 새로운 엔드포인트)
const API_CACHE_URLS = [
    '/api/status',
    '/api/data',
    '/api/metrics',
    '/api/patterns/comprehensive'
];

// 실시간 데이터 캐시 (임시 저장용)
const REALTIME_CACHE_URLS = [
    '/api/table/',
    '/api/recent-pairs'
];

// 캐시하지 않을 경로들
const EXCLUDE_CACHE = [
    '/api/demo',
    '/api/notifications'
];

// Service Worker 설치
self.addEventListener('install', event => {
    console.log('[SW] Installing Service Worker v3.2');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Precaching static resources');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .then(() => {
                console.log('[SW] Static resources cached successfully');
                return self.skipWaiting(); // 즉시 활성화
            })
            .catch(error => {
                console.error('[SW] Precaching failed:', error);
            })
    );
});

// Service Worker 활성화
self.addEventListener('activate', event => {
    console.log('[SW] Activating Service Worker v3.2');
    
    event.waitUntil(
        Promise.all([
            // 오래된 캐시 정리
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => cacheName !== CACHE_NAME)
                        .map(cacheName => {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            }),
            // 모든 클라이언트에게 즉시 적용
            self.clients.claim()
        ])
    );
});

// 네트워크 요청 가로채기
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // 외부 도메인 요청은 패스
    if (url.origin !== location.origin) {
        return;
    }
    
    // POST 요청은 캐시하지 않음
    if (request.method !== 'GET') {
        return;
    }
    
    // 제외할 경로 확인
    if (EXCLUDE_CACHE.some(path => url.pathname.startsWith(path))) {
        return;
    }
    
    event.respondWith(
        handleRequest(request)
    );
});

// 요청 처리 함수
async function handleRequest(request) {
    const url = new URL(request.url);
    
    try {
        // API 요청 처리
        if (url.pathname.startsWith('/api/')) {
            return await handleApiRequest(request);
        }
        
        // 정적 자원 처리
        return await handleStaticRequest(request);
        
    } catch (error) {
        console.error('[SW] Request handling failed:', error);
        
        // HTML 페이지 요청에 대한 오프라인 페이지 제공
        if (request.mode === 'navigate') {
            return await caches.match(OFFLINE_URL) || 
                   new Response('앱이 오프라인 상태입니다.', {
                       status: 503,
                       headers: { 'Content-Type': 'text/plain; charset=utf-8' }
                   });
        }
        
        throw error;
    }
}

// API 요청 처리 (네트워크 우선, 캐시 백업)
async function handleApiRequest(request) {
    const cache = await caches.open(CACHE_NAME);
    
    try {
        // 네트워크에서 최신 데이터 가져오기
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // 성공적인 응답을 캐시에 저장
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.warn('[SW] Network failed for API request, trying cache:', request.url);
        
        // 네트워크 실패시 캐시된 데이터 반환
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            // 캐시된 데이터에 오프라인 헤더 추가
            const response = cachedResponse.clone();
            response.headers.set('X-Offline-Response', 'true');
            return response;
        }
        
        // 캐시도 없으면 오프라인 응답 반환
        return new Response(JSON.stringify({
            success: false,
            error: 'offline',
            message: '인터넷 연결을 확인해주세요.',
            cached: false
        }), {
            status: 503,
            headers: { 
                'Content-Type': 'application/json',
                'X-Offline-Response': 'true'
            }
        });
    }
}

// 정적 자원 처리 (캐시 우선, 네트워크 백업)
async function handleStaticRequest(request) {
    const cache = await caches.open(CACHE_NAME);
    
    // 먼저 캐시에서 찾기
    let cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
        // 백그라운드에서 최신 버전 확인 및 업데이트
        updateCacheInBackground(request, cache);
        return cachedResponse;
    }
    
    try {
        // 캐시에 없으면 네트워크에서 가져오기
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // 성공적인 응답을 캐시에 저장
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.warn('[SW] Network failed for static request:', request.url);
        
        // 네트워크 실패시 기본 응답
        if (request.mode === 'navigate') {
            return await cache.match(OFFLINE_URL) || 
                   new Response('페이지를 불러올 수 없습니다.', {
                       status: 503,
                       headers: { 'Content-Type': 'text/plain; charset=utf-8' }
                   });
        }
        
        throw error;
    }
}

// 백그라운드 캐시 업데이트
async function updateCacheInBackground(request, cache) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            await cache.put(request, networkResponse.clone());
            console.log('[SW] Background cache update successful:', request.url);
        }
        
    } catch (error) {
        console.log('[SW] Background cache update failed:', request.url);
    }
}

// 푸시 알림 수신
self.addEventListener('push', event => {
    console.log('[SW] Push notification received');
    
    if (!event.data) {
        return;
    }
    
    try {
        const data = event.data.json();
        const options = {
            body: data.message || '새로운 알림이 있습니다.',
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/badge-72x72.png',
            vibrate: [100, 50, 100],
            data: data.data || {},
            actions: [
                {
                    action: 'open',
                    title: '열기',
                    icon: '/static/icons/action-open.png'
                },
                {
                    action: 'dismiss',
                    title: '닫기',
                    icon: '/static/icons/action-close.png'
                }
            ],
            requireInteraction: data.persistent || false,
            renotify: true,
            tag: data.tag || 'default'
        };
        
        event.waitUntil(
            self.registration.showNotification(
                data.title || 'Two Very Auto',
                options
            )
        );
        
    } catch (error) {
        console.error('[SW] Push notification parsing failed:', error);
    }
});

// 알림 클릭 처리
self.addEventListener('notificationclick', event => {
    console.log('[SW] Notification clicked');
    
    event.notification.close();
    
    const action = event.action;
    const data = event.notification.data;
    
    if (action === 'dismiss') {
        return;
    }
    
    // 클릭시 앱 열기
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(clientList => {
            // 이미 열린 창이 있으면 포커스
            for (let client of clientList) {
                if (client.url.includes(location.origin)) {
                    return client.focus();
                }
            }
            
            // 새 창 열기
            const url = data.url || '/';
            return clients.openWindow(url);
        })
    );
});

// 백그라운드 동기화
self.addEventListener('sync', event => {
    console.log('[SW] Background sync triggered:', event.tag);
    
    if (event.tag === 'background-data-sync') {
        event.waitUntil(syncDataInBackground());
    }
});

// 백그라운드 데이터 동기화
async function syncDataInBackground() {
    try {
        console.log('[SW] Starting background data sync');
        
        // 중요한 API 엔드포인트들 미리 캐싱
        const cache = await caches.open(CACHE_NAME);
        
        for (const url of API_CACHE_URLS) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    await cache.put(url, response.clone());
                    console.log('[SW] Background sync cached:', url);
                }
            } catch (error) {
                console.warn('[SW] Background sync failed for:', url);
            }
        }
        
        console.log('[SW] Background data sync completed');
        
    } catch (error) {
        console.error('[SW] Background sync error:', error);
    }
}

// 메시지 수신 (클라이언트와 통신)
self.addEventListener('message', event => {
    const { type, payload } = event.data;
    
    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            event.ports[0].postMessage({ success: true });
            break;
            
        case 'GET_VERSION':
            event.ports[0].postMessage({ version: CACHE_NAME });
            break;
            
        case 'CLEAR_CACHE':
            caches.delete(CACHE_NAME).then(success => {
                event.ports[0].postMessage({ success });
            });
            break;
            
        case 'CACHE_URLS':
            if (payload && payload.urls) {
                cacheUrls(payload.urls).then(results => {
                    event.ports[0].postMessage({ results });
                });
            }
            break;
            
        default:
            console.warn('[SW] Unknown message type:', type);
    }
});

// URL들을 캐시에 추가
async function cacheUrls(urls) {
    const cache = await caches.open(CACHE_NAME);
    const results = [];
    
    for (const url of urls) {
        try {
            const response = await fetch(url);
            if (response.ok) {
                await cache.put(url, response.clone());
                results.push({ url, success: true });
            } else {
                results.push({ url, success: false, error: 'Network error' });
            }
        } catch (error) {
            results.push({ url, success: false, error: error.message });
        }
    }
    
    return results;
}

// 온라인/오프라인 상태 감지
self.addEventListener('online', () => {
    console.log('[SW] App is back online');
    // 백그라운드 동기화 트리거
    self.registration.sync.register('background-data-sync');
});

self.addEventListener('offline', () => {
    console.log('[SW] App went offline');
});

// 주기적 백그라운드 동기화 (실험적 기능)
self.addEventListener('periodicsync', event => {
    if (event.tag === 'periodic-data-sync') {
        event.waitUntil(syncDataInBackground());
    }
});

// 오류 처리
self.addEventListener('error', event => {
    console.error('[SW] Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('[SW] Unhandled promise rejection:', event.reason);
});

console.log('[SW] Service Worker v3.2 loaded successfully');