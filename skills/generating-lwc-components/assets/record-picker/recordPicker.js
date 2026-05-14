/**
 * Enhanced Record Picker Component Template
 *
 * Wraps lightning-record-picker with additional features:
 * - Single and multi-select modes
 * - Display of selected records as pills
 * - Custom display fields
 * - Filter support
 * - Validation support
 *
 * @see https://developer.salesforce.com/docs/component-library/bundle/lightning-record-picker
 */
import { LightningElement, api, track } from 'lwc';

export default class RecordPicker extends LightningElement {
    // Public API - Configuration
    @api label = 'Select Record';
    @api objectApiName = 'Account';
    @api placeholder = 'Search...';
    @api required = false;
    @api disabled = false;
    @api multiSelect = false;
    @api maxSelections = 10;

    // Public API - Display configuration
    @api displayInfo = {
        primaryField: 'Name',
        additionalFields: []
    };

    // Public API - Matching configuration
    @api matchingInfo = {
        primaryField: { fieldPath: 'Name' },
        additionalFields: []
    };

    // Public API - Filter (optional)
    @api filter;

    // Private state
    @track _selectedRecords = [];
    _messageWhenBadInput = 'Please select a valid record';

    /**
     * Get the selected value(s)
     * Returns single ID for single-select, array for multi-select
     */
    @api
    get value() {
        if (this.multiSelect) {
            return this._selectedRecords.map(r => r.id);
        }
        return this._selectedRecords.length > 0 ? this._selectedRecords[0].id : null;
    }

    /**
     * Set the selected value(s)
     * Accepts single ID or array of IDs
     */
    set value(val) {
        if (val === null || val === undefined) {
            this._selectedRecords = [];
            return;
        }

        if (Array.isArray(val)) {
            // For arrays, create placeholder records (names will be fetched)
            this._selectedRecords = val.map(id => ({ id, name: id }));
        } else {
            this._selectedRecords = [{ id: val, name: val }];
        }
    }

    /**
     * Get array of selected record IDs
     */
    @api
    get selectedIds() {
        return this._selectedRecords.map(r => r.id);
    }

    /**
     * Check validity
     */
    @api
    checkValidity() {
        if (this.required && this._selectedRecords.length === 0) {
            return false;
        }
        return true;
    }

    /**
     * Report validity with error message
     */
    @api
    reportValidity() {
        const isValid = this.checkValidity();
        const picker = this.template.querySelector('lightning-record-picker');
        if (picker && !isValid) {
            picker.setCustomValidity(this._messageWhenBadInput);
            picker.reportValidity();
        }
        return isValid;
    }

    /**
     * Clear all selections
     */
    @api
    clear() {
        this._selectedRecords = [];
        const picker = this.template.querySelector('lightning-record-picker');
        if (picker) {
            picker.clearSelection();
        }
        this._dispatchChangeEvent();
    }

    // Computed properties
    get hasSelections() {
        return this._selectedRecords.length > 0;
    }

    get showPills() {
        return this.multiSelect && this.hasSelections;
    }

    get isMaxSelectionsReached() {
        return this.multiSelect && this._selectedRecords.length >= this.maxSelections;
    }

    get pickerDisabled() {
        return this.disabled || this.isMaxSelectionsReached;
    }

    get selectionCountMessage() {
        if (!this.multiSelect) return '';
        return `${this._selectedRecords.length} of ${this.maxSelections} selected`;
    }

    // Event handlers
    handleChange(event) {
        const recordId = event.detail.recordId;

        if (!recordId) {
            // Selection cleared
            if (!this.multiSelect) {
                this._selectedRecords = [];
            }
        } else {
            // New selection made
            const recordName = event.detail.recordName || recordId;

            if (this.multiSelect) {
                // Add to selections if not already present
                if (!this._selectedRecords.some(r => r.id === recordId)) {
                    this._selectedRecords = [
                        ...this._selectedRecords,
                        { id: recordId, name: recordName }
                    ];

                    // Clear the picker for next selection
                    const picker = this.template.querySelector('lightning-record-picker');
                    if (picker) {
                        // Small delay to allow event to complete
                        // eslint-disable-next-line @lwc/lwc/no-async-operation
                        setTimeout(() => picker.clearSelection(), 0);
                    }
                }
            } else {
                // Single select - replace selection
                this._selectedRecords = [{ id: recordId, name: recordName }];
            }
        }

        this._dispatchChangeEvent();
    }

    handleRemove(event) {
        const idToRemove = event.target.dataset.id;
        this._selectedRecords = this._selectedRecords.filter(r => r.id !== idToRemove);
        this._dispatchChangeEvent();
    }

    handleClearAll() {
        this.clear();
    }

    _dispatchChangeEvent() {
        this.dispatchEvent(new CustomEvent('change', {
            detail: {
                value: this.value,
                selectedIds: this.selectedIds,
                selectedRecords: [...this._selectedRecords]
            }
        }));
    }
}
