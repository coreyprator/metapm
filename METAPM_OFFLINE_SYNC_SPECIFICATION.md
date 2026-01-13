# MetaPM Offline CRUD with Sync - Technical Specification

**Version:** 1.0  
**Author:** Claude (Architect)  
**Date:** January 13, 2026  
**Target Sprint:** Sprint 3-4  
**Estimated Effort:** 1-2 weeks

---

## 1. Executive Summary

Enable MetaPM to function fully offline with automatic sync when connectivity resumes. Users can create, read, update, and delete tasks/projects while disconnected (e.g., on airplane), with changes automatically syncing to the server upon reconnection.

**Key Design Decisions:**
- Single user system - no collision handling required
- IndexedDB for local persistence
- Background Sync API for automatic reconnection sync
- Sync failures logged to AI History table (with local fallback)
- Visual sync status indicators in UI

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MetaPM PWA                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │  Dashboard  │────▶│  Data Layer  │────▶│   IndexedDB     │  │
│  │    (UI)     │     │   (JS API)   │     │  (Local Store)  │  │
│  └─────────────┘     └──────────────┘     └─────────────────┘  │
│         │                   │                      │            │
│         │                   ▼                      │            │
│         │            ┌──────────────┐              │            │
│         │            │  Sync Queue  │◀─────────────┘            │
│         │            └──────────────┘                           │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌─────────────┐     ┌──────────────┐                          │
│  │ Sync Status │     │   Service    │                          │
│  │  Indicator  │     │   Worker     │                          │
│  └─────────────┘     └──────────────┘                          │
│                             │                                   │
└─────────────────────────────│───────────────────────────────────┘
                              │
                              ▼ (when online)
                    ┌──────────────────┐
                    │   Cloud Run API  │
                    │   (SQL Server)   │
                    └──────────────────┘
```

---

## 3. IndexedDB Schema

### 3.1 Database Structure

```javascript
const DB_NAME = 'MetaPM_Offline';
const DB_VERSION = 1;

const STORES = {
    tasks: {
        keyPath: 'localId',      // Local UUID for offline-created items
        indexes: ['taskId', 'status', 'projectCode', 'syncStatus']
    },
    projects: {
        keyPath: 'localId',
        indexes: ['projectId', 'projectCode', 'syncStatus']
    },
    conversations: {
        keyPath: 'localId',
        indexes: ['conversationId', 'syncStatus']
    },
    methodologyRules: {
        keyPath: 'ruleId',       // Read-only cache, no sync needed
        indexes: ['ruleCode', 'category']
    },
    syncQueue: {
        keyPath: 'queueId',
        autoIncrement: true,
        indexes: ['entityType', 'operation', 'createdAt', 'status']
    },
    apiCache: {
        keyPath: 'endpoint',     // Cache GET responses
        indexes: ['cachedAt']
    }
};
```

### 3.2 Task Schema (IndexedDB)

```javascript
{
    localId: 'local-uuid-123',           // Always present, generated client-side
    taskId: 45,                          // Server ID, null until synced
    title: 'My Task',
    description: 'Details...',
    priority: 3,
    status: 'NEW',
    dueDate: '2026-01-20',
    projectCode: 'META',
    projects: ['META'],
    categories: ['BUG'],
    
    // Sync metadata
    syncStatus: 'pending',               // 'synced' | 'pending' | 'error'
    localCreatedAt: '2026-01-13T10:00:00Z',
    localUpdatedAt: '2026-01-13T10:05:00Z',
    serverUpdatedAt: '2026-01-13T10:05:00Z',  // Last known server timestamp
    syncError: null                      // Error message if sync failed
}
```

### 3.3 Sync Queue Schema

```javascript
{
    queueId: 1,                          // Auto-increment
    entityType: 'task',                  // 'task' | 'project' | 'conversation'
    entityLocalId: 'local-uuid-123',     // Reference to local record
    operation: 'CREATE',                 // 'CREATE' | 'UPDATE' | 'DELETE'
    payload: { ... },                    // Full entity data at time of queue
    createdAt: '2026-01-13T10:00:00Z',
    status: 'pending',                   // 'pending' | 'processing' | 'completed' | 'failed'
    attempts: 0,
    lastAttempt: null,
    errorMessage: null
}
```

---

## 4. Data Layer API

### 4.1 Offline-First Data Service

```javascript
// static/js/offline-data.js

class OfflineDataService {
    constructor() {
        this.db = null;
        this.isOnline = navigator.onLine;
        this.syncInProgress = false;
        
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
    }
    
    async init() {
        this.db = await this.openDatabase();
        await this.loadCachedData();
        if (this.isOnline) {
            await this.syncAll();
        }
    }
    
    // ==========================================
    // TASKS CRUD
    // ==========================================
    
    async getTasks(filters = {}) {
        // Always read from IndexedDB first
        let tasks = await this.getFromStore('tasks');
        
        // Apply client-side filters
        if (filters.status) {
            tasks = tasks.filter(t => t.status === filters.status);
        }
        if (filters.projectCode) {
            tasks = tasks.filter(t => t.projectCode === filters.projectCode);
        }
        
        return tasks.filter(t => t.syncStatus !== 'deleted');
    }
    
    async createTask(taskData) {
        const task = {
            localId: crypto.randomUUID(),
            taskId: null,  // Will be assigned by server
            ...taskData,
            syncStatus: 'pending',
            localCreatedAt: new Date().toISOString(),
            localUpdatedAt: new Date().toISOString()
        };
        
        // Save locally
        await this.saveToStore('tasks', task);
        
        // Queue for sync
        await this.queueSync('task', task.localId, 'CREATE', task);
        
        // Attempt immediate sync if online
        if (this.isOnline) {
            this.syncAll();  // Fire and forget
        }
        
        return task;
    }
    
    async updateTask(localId, updates) {
        const task = await this.getByLocalId('tasks', localId);
        if (!task) throw new Error('Task not found');
        
        const updatedTask = {
            ...task,
            ...updates,
            syncStatus: 'pending',
            localUpdatedAt: new Date().toISOString()
        };
        
        await this.saveToStore('tasks', updatedTask);
        await this.queueSync('task', localId, 'UPDATE', updatedTask);
        
        if (this.isOnline) this.syncAll();
        
        return updatedTask;
    }
    
    async deleteTask(localId) {
        const task = await this.getByLocalId('tasks', localId);
        if (!task) throw new Error('Task not found');
        
        // Mark as deleted locally (soft delete)
        task.syncStatus = 'deleted';
        task.localUpdatedAt = new Date().toISOString();
        
        await this.saveToStore('tasks', task);
        await this.queueSync('task', localId, 'DELETE', { taskId: task.taskId });
        
        if (this.isOnline) this.syncAll();
    }
    
    // ==========================================
    // SYNC ENGINE
    // ==========================================
    
    async syncAll() {
        if (this.syncInProgress || !this.isOnline) return;
        
        this.syncInProgress = true;
        this.updateSyncStatus('syncing');
        
        try {
            // Process queue in order
            const queue = await this.getPendingQueue();
            
            for (const item of queue) {
                await this.processSyncItem(item);
            }
            
            // Refresh data from server
            await this.refreshFromServer();
            
            this.updateSyncStatus('synced');
        } catch (error) {
            console.error('Sync failed:', error);
            this.updateSyncStatus('error');
        } finally {
            this.syncInProgress = false;
        }
    }
    
    async processSyncItem(item) {
        item.status = 'processing';
        item.attempts++;
        item.lastAttempt = new Date().toISOString();
        await this.saveToStore('syncQueue', item);
        
        try {
            let response;
            const API = window.location.origin;
            
            switch (item.operation) {
                case 'CREATE':
                    response = await this.syncCreate(item);
                    break;
                case 'UPDATE':
                    response = await this.syncUpdate(item);
                    break;
                case 'DELETE':
                    response = await this.syncDelete(item);
                    break;
            }
            
            // Success - update local record with server IDs
            item.status = 'completed';
            await this.saveToStore('syncQueue', item);
            
            // Log to AI History
            await this.logSyncEvent(item, 'success');
            
        } catch (error) {
            item.status = 'failed';
            item.errorMessage = error.message;
            await this.saveToStore('syncQueue', item);
            
            // Log failure to AI History (or local if that fails)
            await this.logSyncEvent(item, 'error', error.message);
            
            // Don't throw - continue with other items
            console.error(`Sync failed for ${item.entityType}:`, error);
        }
    }
    
    async syncCreate(item) {
        const API = window.location.origin;
        const endpoints = {
            task: '/api/tasks',
            project: '/api/projects'
        };
        
        const response = await fetch(`${API}${endpoints[item.entityType]}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item.payload)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        
        // Update local record with server ID
        const localRecord = await this.getByLocalId(
            item.entityType + 's', 
            item.entityLocalId
        );
        
        if (localRecord) {
            localRecord[item.entityType + 'Id'] = result.taskId || result.projectId;
            localRecord.syncStatus = 'synced';
            await this.saveToStore(item.entityType + 's', localRecord);
        }
        
        return result;
    }
    
    async syncUpdate(item) {
        const API = window.location.origin;
        const localRecord = await this.getByLocalId(
            item.entityType + 's',
            item.entityLocalId
        );
        
        if (!localRecord || !localRecord[item.entityType + 'Id']) {
            throw new Error('Cannot update: no server ID');
        }
        
        const serverId = localRecord[item.entityType + 'Id'];
        const endpoints = {
            task: `/api/tasks/${serverId}`,
            project: `/api/projects/${localRecord.projectCode}`
        };
        
        const response = await fetch(`${API}${endpoints[item.entityType]}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(item.payload)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        // Mark as synced
        localRecord.syncStatus = 'synced';
        await this.saveToStore(item.entityType + 's', localRecord);
        
        return await response.json();
    }
    
    async syncDelete(item) {
        const API = window.location.origin;
        const serverId = item.payload.taskId || item.payload.projectId;
        
        if (!serverId) {
            // Never synced to server, just remove locally
            await this.deleteFromStore(item.entityType + 's', item.entityLocalId);
            return;
        }
        
        const endpoints = {
            task: `/api/tasks/${serverId}`,
            project: `/api/projects/${item.payload.projectCode}`
        };
        
        const response = await fetch(`${API}${endpoints[item.entityType]}`, {
            method: 'DELETE'
        });
        
        if (!response.ok && response.status !== 404) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        // Remove from local store
        await this.deleteFromStore(item.entityType + 's', item.entityLocalId);
    }
    
    // ==========================================
    // SYNC LOGGING
    // ==========================================
    
    async logSyncEvent(item, status, errorMessage = null) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            entityType: item.entityType,
            operation: item.operation,
            localId: item.entityLocalId,
            status: status,
            attempts: item.attempts,
            errorMessage: errorMessage
        };
        
        try {
            // Try to log to server (AI History / Transactions)
            const API = window.location.origin;
            await fetch(`${API}/api/capture/text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: `[SYNC ${status.toUpperCase()}] ${item.operation} ${item.entityType}: ${item.entityLocalId}${errorMessage ? ' - ' + errorMessage : ''}`,
                    projectCode: 'META'
                })
            });
        } catch (e) {
            // Server logging failed - store locally
            console.warn('Could not log sync to server, storing locally');
            const localLogs = JSON.parse(localStorage.getItem('syncLogs') || '[]');
            localLogs.push(logEntry);
            localStorage.setItem('syncLogs', JSON.stringify(localLogs.slice(-100))); // Keep last 100
        }
    }
    
    // ==========================================
    // ONLINE/OFFLINE HANDLERS
    // ==========================================
    
    handleOnline() {
        this.isOnline = true;
        console.log('Back online - starting sync');
        this.updateSyncStatus('syncing');
        this.syncAll();
    }
    
    handleOffline() {
        this.isOnline = false;
        console.log('Gone offline');
        this.updateSyncStatus('offline');
    }
    
    updateSyncStatus(status) {
        // Dispatch event for UI to handle
        window.dispatchEvent(new CustomEvent('syncStatusChange', { 
            detail: { status } 
        }));
    }
    
    // ==========================================
    // INDEXEDDB HELPERS
    // ==========================================
    
    async openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create stores
                for (const [name, config] of Object.entries(STORES)) {
                    if (!db.objectStoreNames.contains(name)) {
                        const store = db.createObjectStore(name, { 
                            keyPath: config.keyPath,
                            autoIncrement: config.autoIncrement
                        });
                        
                        for (const index of config.indexes || []) {
                            store.createIndex(index, index, { unique: false });
                        }
                    }
                }
            };
        });
    }
    
    async getFromStore(storeName) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const store = tx.objectStore(storeName);
            const request = store.getAll();
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }
    
    async getByLocalId(storeName, localId) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readonly');
            const store = tx.objectStore(storeName);
            const request = store.get(localId);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }
    
    async saveToStore(storeName, data) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            const store = tx.objectStore(storeName);
            const request = store.put(data);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }
    
    async deleteFromStore(storeName, key) {
        return new Promise((resolve, reject) => {
            const tx = this.db.transaction(storeName, 'readwrite');
            const store = tx.objectStore(storeName);
            const request = store.delete(key);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }
    
    async getPendingQueue() {
        const all = await this.getFromStore('syncQueue');
        return all
            .filter(item => item.status === 'pending' || item.status === 'failed')
            .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
    }
    
    async queueSync(entityType, localId, operation, payload) {
        const item = {
            entityType,
            entityLocalId: localId,
            operation,
            payload,
            createdAt: new Date().toISOString(),
            status: 'pending',
            attempts: 0,
            lastAttempt: null,
            errorMessage: null
        };
        
        await this.saveToStore('syncQueue', item);
    }
    
    async refreshFromServer() {
        if (!this.isOnline) return;
        
        const API = window.location.origin;
        
        // Fetch fresh data from server
        const [tasksRes, projectsRes, rulesRes] = await Promise.all([
            fetch(`${API}/api/tasks?pageSize=500`),
            fetch(`${API}/api/projects`),
            fetch(`${API}/api/methodology/rules`)
        ]);
        
        const tasksData = await tasksRes.json();
        const projectsData = await projectsRes.json();
        const rulesData = await rulesRes.json();
        
        // Merge server data with local (preserving pending changes)
        await this.mergeServerData('tasks', tasksData.tasks || [], 'taskId');
        await this.mergeServerData('projects', projectsData.projects || [], 'projectId');
        
        // Rules are read-only, just replace
        for (const rule of rulesData.rules || []) {
            await this.saveToStore('methodologyRules', rule);
        }
    }
    
    async mergeServerData(storeName, serverRecords, serverIdField) {
        const localRecords = await this.getFromStore(storeName);
        const localByServerId = new Map();
        const localByLocalId = new Map();
        
        for (const local of localRecords) {
            if (local[serverIdField]) {
                localByServerId.set(local[serverIdField], local);
            }
            localByLocalId.set(local.localId, local);
        }
        
        for (const server of serverRecords) {
            const serverId = server[serverIdField];
            const existing = localByServerId.get(serverId);
            
            if (existing) {
                // Record exists locally
                if (existing.syncStatus === 'synced') {
                    // Safe to overwrite with server data
                    await this.saveToStore(storeName, {
                        ...server,
                        localId: existing.localId,
                        syncStatus: 'synced'
                    });
                }
                // If pending, keep local version (will sync)
            } else {
                // New from server - create local record
                await this.saveToStore(storeName, {
                    ...server,
                    localId: crypto.randomUUID(),
                    syncStatus: 'synced'
                });
            }
        }
    }
    
    async loadCachedData() {
        // Load from IndexedDB into memory if needed
        // This ensures app works immediately on load
    }
}

// Global instance
const offlineData = new OfflineDataService();
```

---

## 5. Service Worker Updates

### 5.1 Enhanced Service Worker

```javascript
// static/sw.js - UPDATED

const CACHE_VERSION = 'metapm-v2.1.0';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

const STATIC_ASSETS = [
    '/static/dashboard.html',
    '/static/manifest.json',
    '/static/js/offline-data.js'
];

const API_ENDPOINTS_TO_CACHE = [
    '/api/projects',
    '/api/tasks',
    '/api/methodology/rules',
    '/api/categories'
];

// Install - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
});

// Fetch - network first for API, cache first for static
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    if (url.pathname.startsWith('/api/')) {
        // API requests - network first, fallback to cache
        event.respondWith(networkFirstAPI(event.request));
    } else if (STATIC_ASSETS.includes(url.pathname)) {
        // Static assets - cache first
        event.respondWith(cacheFirst(event.request));
    } else {
        // Everything else - network
        event.respondWith(fetch(event.request));
    }
});

async function networkFirstAPI(request) {
    try {
        const response = await fetch(request);
        
        // Cache successful GET responses
        if (request.method === 'GET' && response.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        // Offline - try cache
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        
        // No cache, return offline response
        return new Response(
            JSON.stringify({ error: 'offline', message: 'No cached data available' }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
    }
}

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    
    const response = await fetch(request);
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, response.clone());
    return response;
}

// Background sync
self.addEventListener('sync', event => {
    if (event.tag === 'metapm-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Notify the page to run sync
    const clients = await self.clients.matchAll();
    for (const client of clients) {
        client.postMessage({ type: 'SYNC_TRIGGERED' });
    }
}
```

---

## 6. UI Sync Status Indicator

### 6.1 Status Badge Component

```html
<!-- Add to dashboard.html header -->
<div id="syncStatus" class="sync-indicator" title="Sync status">
    <span class="sync-icon">●</span>
    <span class="sync-text">Synced</span>
</div>
```

### 6.2 Styles

```css
.sync-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    background: rgba(255,255,255,0.1);
}

.sync-indicator.synced {
    color: #22c55e;
}

.sync-indicator.synced .sync-icon {
    color: #22c55e;
}

.sync-indicator.pending {
    color: #f59e0b;
}

.sync-indicator.pending .sync-icon {
    animation: pulse 1s infinite;
}

.sync-indicator.syncing {
    color: #3b82f6;
}

.sync-indicator.syncing .sync-icon {
    animation: spin 1s linear infinite;
}

.sync-indicator.offline {
    color: #ef4444;
}

.sync-indicator.error {
    color: #ef4444;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
```

### 6.3 JavaScript Handler

```javascript
// Add to dashboard.html script

window.addEventListener('syncStatusChange', (event) => {
    const indicator = document.getElementById('syncStatus');
    const icon = indicator.querySelector('.sync-icon');
    const text = indicator.querySelector('.sync-text');
    
    // Remove all status classes
    indicator.className = 'sync-indicator';
    
    switch(event.detail.status) {
        case 'synced':
            indicator.classList.add('synced');
            icon.textContent = '●';
            text.textContent = 'Synced';
            break;
        case 'pending':
            indicator.classList.add('pending');
            icon.textContent = '●';
            text.textContent = 'Pending';
            break;
        case 'syncing':
            indicator.classList.add('syncing');
            icon.textContent = '↻';
            text.textContent = 'Syncing...';
            break;
        case 'offline':
            indicator.classList.add('offline');
            icon.textContent = '○';
            text.textContent = 'Offline';
            break;
        case 'error':
            indicator.classList.add('error');
            icon.textContent = '!';
            text.textContent = 'Sync Error';
            break;
    }
});

// Show pending count badge
async function updatePendingBadge() {
    const pending = await offlineData.getPendingQueue();
    const badge = document.getElementById('syncPendingCount');
    
    if (pending.length > 0) {
        badge.textContent = pending.length;
        badge.style.display = 'inline';
    } else {
        badge.style.display = 'none';
    }
}
```

---

## 7. Dashboard Integration

### 7.1 Replace Direct API Calls

**Before (direct API):**
```javascript
async function loadTasks() {
    const res = await fetch(`${API}/api/tasks`);
    const data = await res.json();
    allTasks = data.tasks || [];
    renderTasks();
}
```

**After (offline-first):**
```javascript
async function loadTasks() {
    allTasks = await offlineData.getTasks();
    renderTasks();
}

async function createTask(taskData) {
    const task = await offlineData.createTask(taskData);
    allTasks.push(task);
    renderTasks();
    showToast('Task created' + (offlineData.isOnline ? '' : ' (will sync when online)'));
}

async function updateTask(localId, updates) {
    const task = await offlineData.updateTask(localId, updates);
    const index = allTasks.findIndex(t => t.localId === localId);
    if (index >= 0) allTasks[index] = task;
    renderTasks();
}

async function deleteTask(localId) {
    await offlineData.deleteTask(localId);
    allTasks = allTasks.filter(t => t.localId !== localId);
    renderTasks();
}
```

### 7.2 Initialization

```javascript
// Replace existing init
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize offline data service
    await offlineData.init();
    
    // Load data (from IndexedDB)
    await loadTasks();
    await loadProjects();
    await loadRules();
    
    // Set up sync status listener
    window.addEventListener('syncStatusChange', updateSyncBadge);
    
    // Initial status
    updateSyncStatus(navigator.onLine ? 'synced' : 'offline');
});
```

---

## 8. Implementation Phases

### Phase 1: IndexedDB Foundation (2-3 days)
1. Create `offline-data.js` with IndexedDB setup
2. Implement basic CRUD for tasks
3. Add sync queue
4. Test offline storage works

**Definition of Done:**
- [ ] Can create task offline, see it in list
- [ ] Task persists after page refresh
- [ ] Sync queue records operations

### Phase 2: Sync Engine (2-3 days)
1. Implement `syncAll()` function
2. Process CREATE, UPDATE, DELETE operations
3. Handle server ID assignment after create
4. Error handling and retry

**Definition of Done:**
- [ ] Tasks created offline sync when online
- [ ] Updates sync correctly
- [ ] Deletes sync correctly
- [ ] Errors don't crash sync

### Phase 3: Service Worker + Caching (1-2 days)
1. Update service worker for API caching
2. Add background sync registration
3. Cache static assets
4. Test offline page loads

**Definition of Done:**
- [ ] Dashboard loads offline
- [ ] Cached API data shows when offline
- [ ] Background sync triggers on reconnect

### Phase 4: UI Indicators (1 day)
1. Add sync status badge
2. Add pending count indicator
3. Show offline-created items differently
4. Toast messages for sync status

**Definition of Done:**
- [ ] Status shows Synced/Pending/Offline/Error
- [ ] User knows when changes are pending
- [ ] User knows when sync completes

### Phase 5: Projects + Testing (2-3 days)
1. Extend to projects CRUD
2. Comprehensive Playwright tests
3. Edge case testing (offline create → online delete)
4. Final deployment

**Definition of Done:**
- [ ] All CRUD works offline for tasks AND projects
- [ ] Playwright tests verify offline behavior
- [ ] 24-hour soak test with airplane mode simulation

---

## 9. Testing Requirements

### 9.1 Playwright Offline Tests

```python
def test_create_task_offline(page):
    """Create task while offline, verify it syncs"""
    page.goto(BASE_URL)
    
    # Go offline
    page.context.set_offline(True)
    
    # Create task
    page.click('#addTaskBtn')
    page.fill('#taskTitle', 'Offline Task Test')
    page.click('#taskForm button[type="submit"]')
    
    # Verify task appears with pending status
    expect(page.locator('#taskList')).to_contain_text('Offline Task Test')
    expect(page.locator('#syncStatus')).to_contain_text('Offline')
    
    # Go online
    page.context.set_offline(False)
    page.wait_for_timeout(2000)  # Wait for sync
    
    # Verify synced
    expect(page.locator('#syncStatus')).to_contain_text('Synced')

def test_offline_data_persists(page):
    """Data created offline persists after refresh"""
    page.goto(BASE_URL)
    page.context.set_offline(True)
    
    # Create task
    page.click('#addTaskBtn')
    page.fill('#taskTitle', 'Persistence Test')
    page.click('#taskForm button[type="submit"]')
    
    # Refresh page
    page.reload()
    
    # Verify task still exists
    expect(page.locator('#taskList')).to_contain_text('Persistence Test')
```

---

## 10. Sync Failure Handling

### 10.1 Retry Logic

- **Max attempts:** 3
- **Backoff:** 1s, 5s, 30s
- **After max retries:** Mark as `failed`, show in UI
- **User action:** Manual "Retry Sync" button

### 10.2 Failure Logging

All sync attempts logged to:
1. **Primary:** AI History table via `/api/capture/text`
2. **Fallback:** `localStorage.syncLogs` (last 100 entries)

Log format:
```
[SYNC SUCCESS] CREATE task: local-uuid-123
[SYNC ERROR] UPDATE task: local-uuid-456 - Server error: 500
```

---

## 11. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `static/js/offline-data.js` | CREATE | IndexedDB + sync engine |
| `static/sw.js` | MODIFY | Add API caching, background sync |
| `static/dashboard.html` | MODIFY | Add sync indicator, use offlineData |
| `static/css/sync.css` | CREATE | Sync indicator styles |
| `tests/test_offline.py` | CREATE | Playwright offline tests |

---

## 12. Rollback Plan

If offline sync causes issues:

1. **Disable IndexedDB:** Comment out `offlineData.init()` in dashboard.html
2. **Revert to direct API:** Change back to `fetch()` calls
3. **Clear user data:** `indexedDB.deleteDatabase('MetaPM_Offline')`

---

## Summary

This design provides:
- ✅ Full offline CRUD for tasks and projects
- ✅ Automatic sync when connectivity resumes
- ✅ Visual sync status indicators
- ✅ Audit logging of sync events
- ✅ Graceful error handling
- ✅ Data persistence across sessions

**Estimated total effort:** 8-12 days

**Prerequisites before starting:**
1. Fix current UI bugs (filters, task duplication)
2. All 8 Playwright tests passing
3. Stable deployed version to branch from
