/**
 * MetaPM Offline Data Module
 * Manages IndexedDB storage and sync queue for offline-first operation
 */

const OfflineDB = {
    dbName: 'MetaPM',
    version: 2,
    db: null,
    
    // Initialize IndexedDB
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);
            
            request.onerror = () => {
                console.error('IndexedDB init failed:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB initialized');
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Tasks store
                if (!db.objectStoreNames.contains('tasks')) {
                    const tasksStore = db.createObjectStore('tasks', { keyPath: 'taskId' });
                    tasksStore.createIndex('status', 'status', { unique: false });
                    tasksStore.createIndex('projectCode', 'projectCode', { unique: false });
                }
                
                // Projects store
                if (!db.objectStoreNames.contains('projects')) {
                    const projectsStore = db.createObjectStore('projects', { keyPath: 'projectCode' });
                    projectsStore.createIndex('status', 'status', { unique: false });
                }
                
                // Sync queue for offline operations
                if (!db.objectStoreNames.contains('syncQueue')) {
                    db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
                }
                
                // Bugs store
                if (!db.objectStoreNames.contains('bugs')) {
                    const bugsStore = db.createObjectStore('bugs', { keyPath: 'bugId' });
                    bugsStore.createIndex('projectId', 'projectId', { unique: false });
                    bugsStore.createIndex('status', 'status', { unique: false });
                }

                // Requirements store
                if (!db.objectStoreNames.contains('requirements')) {
                    const reqsStore = db.createObjectStore('requirements', { keyPath: 'requirementId' });
                    reqsStore.createIndex('projectId', 'projectId', { unique: false });
                    reqsStore.createIndex('status', 'status', { unique: false });
                }

                // Metadata (last sync, etc)
                if (!db.objectStoreNames.contains('metadata')) {
                    db.createObjectStore('metadata', { keyPath: 'key' });
                }

                console.log('IndexedDB stores created');
            };
        });
    },
    
    // ==================== TASKS ====================
    async getTasks() {
        const store = this.db.transaction('tasks', 'readonly').objectStore('tasks');
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async getTask(taskId) {
        const store = this.db.transaction('tasks', 'readonly').objectStore('tasks');
        return new Promise((resolve, reject) => {
            const request = store.get(taskId);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async saveTask(task) {
        const store = this.db.transaction('tasks', 'readwrite').objectStore('tasks');
        return new Promise((resolve, reject) => {
            const request = store.put({
                ...task,
                localUpdatedAt: new Date().toISOString()
            });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async deleteTask(taskId) {
        const store = this.db.transaction('tasks', 'readwrite').objectStore('tasks');
        return new Promise((resolve, reject) => {
            const request = store.delete(taskId);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },
    
    // ==================== PROJECTS ====================
    async getProjects() {
        const store = this.db.transaction('projects', 'readonly').objectStore('projects');
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async getProject(projectCode) {
        const store = this.db.transaction('projects', 'readonly').objectStore('projects');
        return new Promise((resolve, reject) => {
            const request = store.get(projectCode);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async saveProject(project) {
        const store = this.db.transaction('projects', 'readwrite').objectStore('projects');
        return new Promise((resolve, reject) => {
            const request = store.put({
                ...project,
                localUpdatedAt: new Date().toISOString()
            });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async deleteProject(projectCode) {
        const store = this.db.transaction('projects', 'readwrite').objectStore('projects');
        return new Promise((resolve, reject) => {
            const request = store.delete(projectCode);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },
    
    // ==================== SYNC QUEUE ====================
    async queueOperation(operation, data) {
        const store = this.db.transaction('syncQueue', 'readwrite').objectStore('syncQueue');
        return new Promise((resolve, reject) => {
            const request = store.add({
                operation,  // 'CREATE_TASK', 'UPDATE_TASK', 'DELETE_TASK', etc
                data,
                timestamp: new Date().toISOString(),
                synced: false
            });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    
    async getPendingOperations() {
        const store = this.db.transaction('syncQueue', 'readonly').objectStore('syncQueue');
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => {
                resolve(request.result.filter(op => !op.synced));
            };
            request.onerror = () => reject(request.error);
        });
    },
    
    async markSynced(operationId) {
        const store = this.db.transaction('syncQueue', 'readwrite').objectStore('syncQueue');
        return new Promise((resolve, reject) => {
            const getRequest = store.get(operationId);
            
            getRequest.onsuccess = () => {
                const operation = getRequest.result;
                operation.synced = true;
                operation.syncedAt = new Date().toISOString();
                
                const putRequest = store.put(operation);
                putRequest.onsuccess = () => resolve();
                putRequest.onerror = () => reject(putRequest.error);
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    },
    
    async clearSyncQueue() {
        const store = this.db.transaction('syncQueue', 'readwrite').objectStore('syncQueue');
        return new Promise((resolve, reject) => {
            const request = store.clear();
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },
    
    // ==================== METADATA ====================
    async setMetadata(key, value) {
        const store = this.db.transaction('metadata', 'readwrite').objectStore('metadata');
        return new Promise((resolve, reject) => {
            const request = store.put({ key, value, timestamp: new Date().toISOString() });
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },
    
    async getMetadata(key) {
        const store = this.db.transaction('metadata', 'readonly').objectStore('metadata');
        return new Promise((resolve, reject) => {
            const request = store.get(key);
            request.onsuccess = () => resolve(request.result?.value);
            request.onerror = () => reject(request.error);
        });
    },
    
    // ==================== BULK OPERATIONS ====================
    async bulkSaveTasks(tasks) {
        const store = this.db.transaction('tasks', 'readwrite').objectStore('tasks');
        tasks.forEach(task => {
            store.put({
                ...task,
                localUpdatedAt: new Date().toISOString()
            });
        });
        return new Promise((resolve, reject) => {
            const checkRequest = store.count();
            checkRequest.onsuccess = () => resolve(checkRequest.result);
            checkRequest.onerror = () => reject(checkRequest.error);
        });
    },
    
    async bulkSaveProjects(projects) {
        const store = this.db.transaction('projects', 'readwrite').objectStore('projects');
        projects.forEach(project => {
            store.put({
                ...project,
                localUpdatedAt: new Date().toISOString()
            });
        });
        return new Promise((resolve, reject) => {
            const checkRequest = store.count();
            checkRequest.onsuccess = () => resolve(checkRequest.result);
            checkRequest.onerror = () => reject(checkRequest.error);
        });
    },
    
    // ==================== BUGS ====================
    async getBugs() {
        const store = this.db.transaction('bugs', 'readonly').objectStore('bugs');
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async saveBug(bug) {
        const store = this.db.transaction('bugs', 'readwrite').objectStore('bugs');
        return new Promise((resolve, reject) => {
            const request = store.put({ ...bug, localUpdatedAt: new Date().toISOString() });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async deleteBug(bugId) {
        const store = this.db.transaction('bugs', 'readwrite').objectStore('bugs');
        return new Promise((resolve, reject) => {
            const request = store.delete(bugId);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },

    async bulkSaveBugs(bugs) {
        const store = this.db.transaction('bugs', 'readwrite').objectStore('bugs');
        bugs.forEach(bug => store.put({ ...bug, localUpdatedAt: new Date().toISOString() }));
        return new Promise((resolve, reject) => {
            const req = store.count();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    },

    // ==================== REQUIREMENTS ====================
    async getRequirements() {
        const store = this.db.transaction('requirements', 'readonly').objectStore('requirements');
        return new Promise((resolve, reject) => {
            const request = store.getAll();
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async saveRequirement(req) {
        const store = this.db.transaction('requirements', 'readwrite').objectStore('requirements');
        return new Promise((resolve, reject) => {
            const request = store.put({ ...req, localUpdatedAt: new Date().toISOString() });
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },

    async deleteRequirement(reqId) {
        const store = this.db.transaction('requirements', 'readwrite').objectStore('requirements');
        return new Promise((resolve, reject) => {
            const request = store.delete(reqId);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    },

    async bulkSaveRequirements(reqs) {
        const store = this.db.transaction('requirements', 'readwrite').objectStore('requirements');
        reqs.forEach(r => store.put({ ...r, localUpdatedAt: new Date().toISOString() }));
        return new Promise((resolve, reject) => {
            const req = store.count();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    },

    async clearAllData() {
        const tx = this.db.transaction(['tasks', 'projects', 'bugs', 'requirements', 'syncQueue'], 'readwrite');
        tx.objectStore('tasks').clear();
        tx.objectStore('projects').clear();
        tx.objectStore('bugs').clear();
        tx.objectStore('requirements').clear();
        tx.objectStore('syncQueue').clear();

        return new Promise((resolve, reject) => {
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }
};

// Online/offline detection
const OnlineStatus = {
    isOnline: navigator.onLine,
    listeners: [],
    
    init() {
        window.addEventListener('online', () => this.setOnline(true));
        window.addEventListener('offline', () => this.setOnline(false));
        
        // Periodic connectivity check
        setInterval(() => {
            fetch('/health', { method: 'HEAD', cache: 'no-store' })
                .then(() => this.setOnline(true))
                .catch(() => this.setOnline(false));
        }, 30000);
    },
    
    setOnline(online) {
        if (this.isOnline !== online) {
            this.isOnline = online;
            console.log(`Status: ${online ? 'ONLINE' : 'OFFLINE'}`);
            this.notifyListeners();
        }
    },
    
    onChange(callback) {
        this.listeners.push(callback);
    },
    
    notifyListeners() {
        this.listeners.forEach(cb => cb(this.isOnline));
    }
};

// Sync Engine
const SyncEngine = {
    syncing: false,
    syncInterval: null,
    
    init() {
        OnlineStatus.onChange((online) => {
            if (online && !this.syncing) {
                console.log('Connection restored, starting sync...');
                this.syncAll();
            }
        });
    },
    
    async syncAll() {
        if (this.syncing || !OnlineStatus.isOnline) return;
        
        this.syncing = true;
        try {
            const pendingOps = await OfflineDB.getPendingOperations();
            console.log(`Syncing ${pendingOps.length} pending operations...`);
            
            for (const op of pendingOps) {
                try {
                    await this.syncOperation(op);
                    await OfflineDB.markSynced(op.id);
                } catch (error) {
                    console.error(`Failed to sync operation ${op.id}:`, error);
                    // Continue with other operations
                }
            }
            
            console.log('Sync completed');
            window.dispatchEvent(new CustomEvent('syncComplete'));
        } catch (error) {
            console.error('Sync error:', error);
        } finally {
            this.syncing = false;
        }
    },
    
    async syncOperation(operation) {
        const { operation: op, data } = operation;
        
        switch (op) {
            case 'CREATE_TASK':
                return fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());
            
            case 'UPDATE_TASK':
                return fetch(`/api/tasks/${data.taskId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());
            
            case 'DELETE_TASK':
                return fetch(`/api/tasks/${data.taskId}`, {
                    method: 'DELETE'
                }).then(r => r.json());
            
            case 'CREATE_PROJECT':
                return fetch('/api/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());
            
            case 'UPDATE_PROJECT':
                return fetch(`/api/projects/${data.projectCode}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());
            
            case 'DELETE_PROJECT':
                return fetch(`/api/projects/${data.projectCode}`, {
                    method: 'DELETE'
                }).then(r => r.json());

            case 'CREATE_BUG':
                return fetch('/api/backlog/bugs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());

            case 'UPDATE_BUG':
                return fetch(`/api/backlog/bugs/${data.bugId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());

            case 'DELETE_BUG':
                return fetch(`/api/backlog/bugs/${data.bugId}`, {
                    method: 'DELETE'
                }).then(r => r.json());

            case 'CREATE_REQUIREMENT':
                return fetch('/api/backlog/requirements', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());

            case 'UPDATE_REQUIREMENT':
                return fetch(`/api/backlog/requirements/${data.requirementId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                }).then(r => r.json());

            case 'DELETE_REQUIREMENT':
                return fetch(`/api/backlog/requirements/${data.requirementId}`, {
                    method: 'DELETE'
                }).then(r => r.json());

            default:
                throw new Error(`Unknown operation: ${op}`);
        }
    }
};

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', async () => {
        await OfflineDB.init();
        OnlineStatus.init();
        SyncEngine.init();
    });
} else {
    OfflineDB.init().then(() => {
        OnlineStatus.init();
        SyncEngine.init();
    });
}
