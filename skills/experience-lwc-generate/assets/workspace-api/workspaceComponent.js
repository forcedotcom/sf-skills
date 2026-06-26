/**
 * Workspace API Component Template
 *
 * Demonstrates tab management in Salesforce Console (Service/Sales Console) using:
 * - IsConsoleNavigation wire to detect console context
 * - Tab opening, closing, and focusing
 * - Subtab management
 * - Tab label and icon customization
 * - Tab refresh
 *
 * @see https://developer.salesforce.com/docs/component-library/bundle/lightning-workspace-api
 */
import { LightningElement, wire, api } from 'lwc';
import {
    IsConsoleNavigation,
    getFocusedTabInfo,
    getTabInfo,
    openTab,
    closeTab,
    focusTab,
    refreshTab,
    setTabLabel,
    setTabIcon,
    setTabHighlighted,
    disableTabClose,
    getAllTabInfo,
    openSubtab,
    MINIMUM_SUBTAB_SIZE
} from 'lightning/platformWorkspaceApi';

export default class WorkspaceComponent extends LightningElement {
    // Wire to check if we're in a console app
    @wire(IsConsoleNavigation) isConsoleNavigation;

    // Current tab information
    currentTabId;
    currentTabLabel;
    allTabs = [];

    // Error tracking
    error;

    /**
     * Check if the component is running in a console context
     */
    get isConsole() {
        return this.isConsoleNavigation?.data === true;
    }

    get isNotConsole() {
        return this.isConsoleNavigation?.data === false;
    }

    /**
     * Connected callback - get current tab info
     */
    async connectedCallback() {
        if (this.isConsole) {
            await this._refreshCurrentTabInfo();
        }
    }

    // ==================
    // Public API Methods
    // ==================

    /**
     * Open a record in a new tab
     * @param {String} recordId - The record ID to open
     * @param {String} objectApiName - The object API name (for icon)
     * @param {Boolean} focus - Whether to focus the new tab
     */
    @api
    async openRecordTab(recordId, objectApiName = 'Account', focus = true) {
        if (!this.isConsole) {
            console.warn('openRecordTab: Not in console context');
            return null;
        }

        try {
            const tabId = await openTab({
                recordId,
                focus,
                icon: `standard:${objectApiName.toLowerCase()}`,
                label: 'Loading...'
            });
            return tabId;
        } catch (error) {
            this._handleError('Error opening tab', error);
            return null;
        }
    }

    /**
     * Open a URL in a new tab
     * @param {String} url - The URL to open
     * @param {String} label - The tab label
     * @param {String} icon - The tab icon
     */
    @api
    async openUrlTab(url, label = 'New Tab', icon = 'utility:new_window') {
        if (!this.isConsole) return null;

        try {
            const tabId = await openTab({
                url,
                focus: true,
                label,
                icon
            });
            return tabId;
        } catch (error) {
            this._handleError('Error opening URL tab', error);
            return null;
        }
    }

    /**
     * Open a subtab under the current (or specified) parent tab
     * @param {String} recordId - The record ID for the subtab
     * @param {String} parentTabId - Optional parent tab ID (defaults to current tab)
     */
    @api
    async openRecordSubtab(recordId, parentTabId = null) {
        if (!this.isConsole) return null;

        try {
            const parent = parentTabId || (await this._getCurrentTabId());
            const subtabId = await openSubtab({
                parentTabId: parent,
                recordId,
                focus: true
            });
            return subtabId;
        } catch (error) {
            this._handleError('Error opening subtab', error);
            return null;
        }
    }

    /**
     * Close a specific tab
     * @param {String} tabId - The tab ID to close
     */
    @api
    async closeTabById(tabId) {
        if (!this.isConsole) return;

        try {
            await closeTab(tabId);
        } catch (error) {
            this._handleError('Error closing tab', error);
        }
    }

    /**
     * Close the current tab
     */
    @api
    async closeCurrentTab() {
        if (!this.isConsole) return;

        try {
            const tabId = await this._getCurrentTabId();
            await closeTab(tabId);
        } catch (error) {
            this._handleError('Error closing current tab', error);
        }
    }

    /**
     * Focus a specific tab
     * @param {String} tabId - The tab ID to focus
     */
    @api
    async focusTabById(tabId) {
        if (!this.isConsole) return;

        try {
            await focusTab(tabId);
        } catch (error) {
            this._handleError('Error focusing tab', error);
        }
    }

    /**
     * Update the current tab's label
     * @param {String} label - The new label
     */
    @api
    async updateCurrentTabLabel(label) {
        if (!this.isConsole) return;

        try {
            const tabId = await this._getCurrentTabId();
            await setTabLabel(tabId, label);
            this.currentTabLabel = label;
        } catch (error) {
            this._handleError('Error updating tab label', error);
        }
    }

    /**
     * Update the current tab's icon
     * @param {String} iconName - The icon name (e.g., 'standard:account')
     */
    @api
    async updateCurrentTabIcon(iconName) {
        if (!this.isConsole) return;

        try {
            const tabId = await this._getCurrentTabId();
            await setTabIcon(tabId, iconName);
        } catch (error) {
            this._handleError('Error updating tab icon', error);
        }
    }

    /**
     * Highlight a tab (shows visual indicator)
     * @param {String} tabId - The tab ID to highlight
     * @param {Boolean} highlighted - Whether to highlight or remove highlight
     */
    @api
    async highlightTab(tabId, highlighted = true) {
        if (!this.isConsole) return;

        try {
            await setTabHighlighted(tabId, highlighted);
        } catch (error) {
            this._handleError('Error highlighting tab', error);
        }
    }

    /**
     * Prevent a tab from being closed
     * @param {String} tabId - The tab ID
     * @param {Boolean} disabled - Whether to disable close
     */
    @api
    async preventTabClose(tabId, disabled = true) {
        if (!this.isConsole) return;

        try {
            await disableTabClose(tabId, disabled);
        } catch (error) {
            this._handleError('Error disabling tab close', error);
        }
    }

    /**
     * Refresh the current tab
     */
    @api
    async refreshCurrentTab() {
        if (!this.isConsole) return;

        try {
            const tabId = await this._getCurrentTabId();
            await refreshTab(tabId);
        } catch (error) {
            this._handleError('Error refreshing tab', error);
        }
    }

    /**
     * Get information about all open tabs
     */
    @api
    async getAllTabs() {
        if (!this.isConsole) return [];

        try {
            const tabInfo = await getAllTabInfo();
            this.allTabs = tabInfo;
            return tabInfo;
        } catch (error) {
            this._handleError('Error getting all tabs', error);
            return [];
        }
    }

    // =================
    // Private Methods
    // =================

    async _getCurrentTabId() {
        const tabInfo = await getFocusedTabInfo();
        this.currentTabId = tabInfo.tabId;
        return tabInfo.tabId;
    }

    async _refreshCurrentTabInfo() {
        try {
            const tabInfo = await getFocusedTabInfo();
            this.currentTabId = tabInfo.tabId;
            this.currentTabLabel = tabInfo.title;
        } catch (error) {
            this._handleError('Error getting tab info', error);
        }
    }

    _handleError(message, error) {
        console.error(message, error);
        this.error = `${message}: ${error?.body?.message || error?.message || 'Unknown error'}`;
    }

    // Event handlers for UI (if template is used)
    handleRefresh() {
        this.refreshCurrentTab();
    }

    handleGetAllTabs() {
        this.getAllTabs();
    }
}
