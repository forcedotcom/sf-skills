/**
 * BASIC LWC COMPONENT TEMPLATE
 *
 * This template demonstrates a standard LWC component with:
 * - Wire service for data fetching
 * - Loading and error states
 * - Event dispatching
 * - Proper lifecycle management
 *
 * Replace: basicComponent → yourComponentName
 * Replace: BasicComponent → YourComponentName
 * Replace: Account → YourObject
 */

import { LightningElement, api, wire } from 'lwc';
import getRecords from '@salesforce/apex/BasicComponentController.getRecords';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

export default class BasicComponent extends LightningElement {
    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API (@api) - Properties set by parent or App Builder
    // ═══════════════════════════════════════════════════════════════════════

    @api recordId;           // Automatically populated on record pages
    @api objectApiName;      // Automatically populated on record pages
    @api title = 'Records';  // Configurable in App Builder

    // ═══════════════════════════════════════════════════════════════════════
    // PRIVATE REACTIVE PROPERTIES
    // ═══════════════════════════════════════════════════════════════════════

    records = [];
    error;
    isLoading = true;

    // ═══════════════════════════════════════════════════════════════════════
    // WIRE SERVICE - Reactive data fetching
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Wire service automatically calls Apex when recordId changes.
     * The '$recordId' syntax makes it reactive to changes.
     */
    @wire(getRecords, { parentId: '$recordId' })
    wiredRecords({ error, data }) {
        this.isLoading = false;
        if (data) {
            this.records = data;
            this.error = undefined;
        } else if (error) {
            this.error = this.reduceErrors(error);
            this.records = [];
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // GETTERS - Computed properties for template
    // ═══════════════════════════════════════════════════════════════════════

    get hasRecords() {
        return this.records && this.records.length > 0;
    }

    get isEmpty() {
        return !this.isLoading && !this.error && !this.hasRecords;
    }

    get recordCount() {
        return this.records ? this.records.length : 0;
    }

    get cardTitle() {
        return `${this.title} (${this.recordCount})`;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LIFECYCLE HOOKS
    // ═══════════════════════════════════════════════════════════════════════

    connectedCallback() {
        // Component inserted into DOM
        // Good for: event listeners, subscriptions
        console.log('BasicComponent connected');
    }

    renderedCallback() {
        // DOM has been rendered
        // Warning: Runs after every render - avoid heavy operations
        // Use a flag to run once if needed
    }

    disconnectedCallback() {
        // Component removed from DOM
        // Good for: cleanup, unsubscribe, remove event listeners
        console.log('BasicComponent disconnected');
    }

    // ═══════════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════════

    handleRecordClick(event) {
        const recordId = event.currentTarget.dataset.id;
        const recordName = event.currentTarget.dataset.name;

        // Dispatch custom event for parent components
        this.dispatchEvent(new CustomEvent('recordselected', {
            detail: {
                recordId,
                recordName
            },
            bubbles: true,      // Event bubbles up through DOM
            composed: true      // Event crosses shadow DOM boundary
        }));
    }

    handleRefresh() {
        // Force refresh by triggering wire service
        // Note: Wire with cacheable=true caches results
        // Use refreshApex() for explicit refresh
        this.isLoading = true;
        // Wire will re-execute when recordId changes
    }

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITY METHODS
    // ═══════════════════════════════════════════════════════════════════════

    showToast(title, message, variant = 'info') {
        this.dispatchEvent(new ShowToastEvent({
            title,
            message,
            variant  // 'success', 'warning', 'error', 'info'
        }));
    }

    reduceErrors(errors) {
        if (!Array.isArray(errors)) {
            errors = [errors];
        }

        return errors
            .filter(error => !!error)
            .map(error => {
                if (typeof error === 'string') {
                    return error;
                }
                if (error.body) {
                    if (typeof error.body.message === 'string') {
                        return error.body.message;
                    }
                    if (Array.isArray(error.body)) {
                        return error.body.map(e => e.message).join(', ');
                    }
                }
                if (error.message) {
                    return error.message;
                }
                return JSON.stringify(error);
            })
            .join(', ');
    }
}
