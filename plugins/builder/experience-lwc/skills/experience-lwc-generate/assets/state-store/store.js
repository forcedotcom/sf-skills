/**
 * STATE STORE TEMPLATE
 *
 * Singleton store for cross-component state management in LWC.
 * Provides reactive state with subscription-based updates.
 *
 * Features:
 * - Cross-component state sharing
 * - Subscription-based reactivity
 * - Automatic cleanup utilities
 * - Debug mode for development
 *
 * Usage:
 * import store from 'c/store';
 *
 * // In connectedCallback:
 * this.cart = store.initState('cart', { items: [], total: 0 });
 * this._unsubscribe = store.subscribe('cart', (cart) => { this.cart = cart; });
 *
 * // In disconnectedCallback:
 * if (this._unsubscribe) this._unsubscribe();
 *
 * // Update state anywhere:
 * store.setState('cart', { ...store.getState('cart'), items: [...items, newItem] });
 */

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Enable debug mode for state change logging.
 * Set to false in production.
 */
const DEBUG_MODE = false;

// ═══════════════════════════════════════════════════════════════════════════
// PRIVATE STATE
// ═══════════════════════════════════════════════════════════════════════════

/** @type {Map<string, any>} State container */
const state = new Map();

/** @type {Map<string, Array<Function>>} Subscribers by key */
const subscribers = new Map();

/** @type {Map<string, any>} Initial values for reset */
const initialValues = new Map();

// ═══════════════════════════════════════════════════════════════════════════
// CORE API
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Get current state for a key.
 *
 * @param {string} key - State key
 * @returns {any} Current state value, or undefined if not set
 *
 * @example
 * const cart = store.getState('cart');
 */
function getState(key) {
    return state.get(key);
}

/**
 * Set state and notify all subscribers.
 *
 * @param {string} key - State key
 * @param {any} value - New state value
 *
 * @example
 * store.setState('cart', { items: [...cart.items, newItem], total: newTotal });
 */
function setState(key, value) {
    const oldValue = state.get(key);
    state.set(key, value);

    if (DEBUG_MODE) {
        console.log(`[Store] ${key} updated:`, { old: oldValue, new: value });
    }

    // Notify all subscribers for this key
    const keySubscribers = subscribers.get(key) || [];
    keySubscribers.forEach(callback => {
        try {
            callback(value, oldValue);
        } catch (e) {
            console.error(`[Store] Subscriber error for "${key}":`, e);
        }
    });
}

/**
 * Subscribe to state changes for a key.
 *
 * @param {string} key - State key to watch
 * @param {Function} callback - Called with (newValue, oldValue) on change
 * @returns {Function} Unsubscribe function - MUST be called in disconnectedCallback
 *
 * @example
 * // In connectedCallback:
 * this._unsubscribe = store.subscribe('cart', (cart) => {
 *     this.cart = cart;
 * });
 *
 * // In disconnectedCallback:
 * if (this._unsubscribe) this._unsubscribe();
 */
function subscribe(key, callback) {
    if (!subscribers.has(key)) {
        subscribers.set(key, []);
    }
    subscribers.get(key).push(callback);

    if (DEBUG_MODE) {
        console.log(`[Store] Subscribed to "${key}", total: ${subscribers.get(key).length}`);
    }

    // Return unsubscribe function
    return () => {
        const keySubscribers = subscribers.get(key) || [];
        const index = keySubscribers.indexOf(callback);
        if (index > -1) {
            keySubscribers.splice(index, 1);
            if (DEBUG_MODE) {
                console.log(`[Store] Unsubscribed from "${key}", remaining: ${keySubscribers.length}`);
            }
        }
    };
}

/**
 * Initialize state with a default value if not already set.
 *
 * @param {string} key - State key
 * @param {any} defaultValue - Default value if key doesn't exist
 * @returns {any} Current state value (existing or newly set default)
 *
 * @example
 * // Safe initialization - won't overwrite existing state
 * const cart = store.initState('cart', { items: [], total: 0 });
 */
function initState(key, defaultValue) {
    if (!state.has(key)) {
        state.set(key, defaultValue);
        initialValues.set(key, JSON.parse(JSON.stringify(defaultValue)));
    }
    return state.get(key);
}

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY METHODS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Reset a state key to its initial value.
 *
 * @param {string} key - State key to reset
 *
 * @example
 * store.resetState('cart'); // Resets to initial { items: [], total: 0 }
 */
function resetState(key) {
    if (initialValues.has(key)) {
        const initial = JSON.parse(JSON.stringify(initialValues.get(key)));
        setState(key, initial);
    }
}

/**
 * Clear all state (useful for testing or logout).
 */
function clearAll() {
    state.clear();
    subscribers.clear();
    initialValues.clear();

    if (DEBUG_MODE) {
        console.log('[Store] All state cleared');
    }
}

/**
 * Get all current state keys.
 *
 * @returns {Array<string>} Array of state keys
 */
function getKeys() {
    return Array.from(state.keys());
}

/**
 * Check if a state key exists.
 *
 * @param {string} key - State key
 * @returns {boolean} True if key exists
 */
function hasState(key) {
    return state.has(key);
}

/**
 * Get subscriber count for a key (useful for debugging).
 *
 * @param {string} key - State key
 * @returns {number} Number of active subscribers
 */
function getSubscriberCount(key) {
    return (subscribers.get(key) || []).length;
}

// ═══════════════════════════════════════════════════════════════════════════
// BATCH UPDATES
// ═══════════════════════════════════════════════════════════════════════════

let batchUpdates = [];
let isBatching = false;

/**
 * Batch multiple state updates to reduce re-renders.
 *
 * @param {Function} updateFn - Function containing multiple setState calls
 *
 * @example
 * store.batch(() => {
 *     store.setState('user', newUser);
 *     store.setState('preferences', newPrefs);
 *     store.setState('cart', newCart);
 * }); // Subscribers notified once after all updates
 */
function batch(updateFn) {
    isBatching = true;
    batchUpdates = [];

    try {
        updateFn();
    } finally {
        isBatching = false;

        // Notify subscribers for all changed keys
        const changedKeys = new Set(batchUpdates.map(u => u.key));
        changedKeys.forEach(key => {
            const lastUpdate = batchUpdates.filter(u => u.key === key).pop();
            if (lastUpdate) {
                const keySubscribers = subscribers.get(key) || [];
                keySubscribers.forEach(callback => {
                    try {
                        callback(lastUpdate.value, lastUpdate.oldValue);
                    } catch (e) {
                        console.error(`[Store] Batch subscriber error for "${key}":`, e);
                    }
                });
            }
        });

        batchUpdates = [];
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═══════════════════════════════════════════════════════════════════════════

export default {
    // Core API
    getState,
    setState,
    subscribe,
    initState,

    // Utilities
    resetState,
    clearAll,
    getKeys,
    hasState,
    getSubscriberCount,

    // Batch operations
    batch
};
