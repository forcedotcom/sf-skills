/**
 * Flow Screen Component Template
 *
 * Demonstrates complete Flow integration patterns:
 * - @api properties with inputOnly/outputOnly roles
 * - FlowAttributeChangeEvent for output binding
 * - FlowNavigationFinishEvent for programmatic navigation
 * - availableActions for navigation state awareness
 * - @AuraEnabled Apex integration for data operations
 *
 * @see https://developer.salesforce.com/docs/component-library/bundle/lightning-flow-support
 */
import { LightningElement, api, wire } from 'lwc';
import { FlowAttributeChangeEvent, FlowNavigationFinishEvent } from 'lightning/flowSupport';

// Apex imports (uncomment and modify as needed)
// import getRecords from '@salesforce/apex/FlowScreenController.getRecords';
// import processRecord from '@salesforce/apex/FlowScreenController.processRecord';

export default class FlowScreenComponent extends LightningElement {
    // ═══════════════════════════════════════════════════════════════════════
    // FLOW INPUT PROPERTIES (inputOnly - Flow → Component)
    // These receive values FROM the Flow. Changes in Flow update the component.
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Record ID from Flow context (e.g., from Record-Triggered Flow)
     * Maps to: Flow variable or $Record.Id
     */
    @api recordId;

    /**
     * Object API Name for context-aware behavior
     * Maps to: Flow variable or $Record.Object
     */
    @api objectApiName;

    /**
     * Custom label configurable in Flow Builder
     * Maps to: Flow constant, variable, or direct text
     */
    @api inputLabel = 'Select a Record';

    /**
     * Available navigation actions - automatically populated by Flow runtime
     * Possible values: ['NEXT', 'BACK', 'FINISH', 'PAUSE']
     * Use this to conditionally show/hide navigation buttons
     */
    @api availableActions = [];

    // ═══════════════════════════════════════════════════════════════════════
    // FLOW OUTPUT PROPERTIES (outputOnly - Component → Flow)
    // These send values BACK to the Flow. Use FlowAttributeChangeEvent to update.
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Selected record ID - output to Flow
     * IMPORTANT: Use FlowAttributeChangeEvent to notify Flow of changes
     */
    @api selectedRecordId;

    /**
     * Selected record name - output to Flow
     */
    @api selectedRecordName;

    /**
     * Boolean flag indicating completion - useful for Flow decisions
     */
    @api isComplete = false;

    /**
     * Error message if validation fails - Flow can use in fault path
     */
    @api errorMessage;

    // ═══════════════════════════════════════════════════════════════════════
    // PRIVATE REACTIVE PROPERTIES
    // ═══════════════════════════════════════════════════════════════════════

    records = [];
    error;
    isLoading = true;
    _selectedId;

    // ═══════════════════════════════════════════════════════════════════════
    // LIFECYCLE HOOKS
    // ═══════════════════════════════════════════════════════════════════════

    connectedCallback() {
        // Initialize component when added to DOM
        this.loadData();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // DATA LOADING
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Load data - replace with @wire or imperative Apex call
     */
    async loadData() {
        this.isLoading = true;
        try {
            // Example: Load records from Apex
            // this.records = await getRecords({ parentId: this.recordId });

            // Placeholder data for template
            this.records = [
                { id: '001xx000000001', name: 'Sample Record 1', description: 'Description 1' },
                { id: '001xx000000002', name: 'Sample Record 2', description: 'Description 2' },
                { id: '001xx000000003', name: 'Sample Record 3', description: 'Description 3' }
            ];
            this.error = undefined;
        } catch (err) {
            this.error = this.reduceErrors(err);
            this.records = [];
        } finally {
            this.isLoading = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FLOW OUTPUT - FlowAttributeChangeEvent
    // CRITICAL: This is how you send values back to Flow variables
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Handle record selection and notify Flow
     * @param {Event} event - Click event from record tile
     */
    handleRecordSelect(event) {
        const recordId = event.currentTarget.dataset.id;
        const recordName = event.currentTarget.dataset.name;

        // Update local state
        this._selectedId = recordId;
        this.selectedRecordId = recordId;
        this.selectedRecordName = recordName;

        // ─────────────────────────────────────────────────────────────────
        // CRITICAL: Dispatch FlowAttributeChangeEvent for EACH output
        // This notifies the Flow runtime that output values have changed
        // The first parameter is the @api property name (case-sensitive)
        // The second parameter is the new value
        // ─────────────────────────────────────────────────────────────────
        this.dispatchEvent(new FlowAttributeChangeEvent(
            'selectedRecordId',
            this.selectedRecordId
        ));

        this.dispatchEvent(new FlowAttributeChangeEvent(
            'selectedRecordName',
            this.selectedRecordName
        ));
    }

    /**
     * Update completion status and notify Flow
     * @param {Boolean} complete - Whether the screen is complete
     */
    setComplete(complete) {
        this.isComplete = complete;
        this.dispatchEvent(new FlowAttributeChangeEvent('isComplete', complete));
    }

    /**
     * Set error message and notify Flow
     * @param {String} message - Error message
     */
    setError(message) {
        this.errorMessage = message;
        this.dispatchEvent(new FlowAttributeChangeEvent('errorMessage', message));
    }

    // ═══════════════════════════════════════════════════════════════════════
    // FLOW NAVIGATION - FlowNavigationFinishEvent
    // Programmatically trigger Flow navigation (Next, Back, Finish, Pause)
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Navigate to next screen
     * Only works if 'NEXT' is in availableActions
     */
    handleNext() {
        // Validate before navigation
        if (!this.selectedRecordId) {
            this.setError('Please select a record before proceeding.');
            return;
        }

        // Clear any previous errors
        this.setError(null);

        // Mark as complete
        this.setComplete(true);

        // Check if NEXT action is available
        if (this.canGoNext) {
            // Dispatch navigation event - Flow will handle the rest
            this.dispatchEvent(new FlowNavigationFinishEvent('NEXT'));
        }
    }

    /**
     * Navigate to previous screen
     * Only works if 'BACK' is in availableActions
     */
    handleBack() {
        if (this.canGoBack) {
            this.dispatchEvent(new FlowNavigationFinishEvent('BACK'));
        }
    }

    /**
     * Finish the flow (for final screens)
     * Only works if 'FINISH' is in availableActions
     */
    handleFinish() {
        // Validate before finishing
        if (!this.selectedRecordId) {
            this.setError('Please select a record before finishing.');
            return;
        }

        this.setComplete(true);

        if (this.canFinish) {
            this.dispatchEvent(new FlowNavigationFinishEvent('FINISH'));
        }
    }

    /**
     * Pause the flow (for pausable flows)
     * Only works if 'PAUSE' is in availableActions
     */
    handlePause() {
        if (this.canPause) {
            this.dispatchEvent(new FlowNavigationFinishEvent('PAUSE'));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // APEX INTEGRATION (Optional)
    // Use @AuraEnabled methods for complex operations
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Example: Process selection with Apex before navigation
     */
    async handleProcessAndContinue() {
        this.isLoading = true;
        try {
            // Call Apex to process the selection
            // const result = await processRecord({
            //     recordId: this.selectedRecordId,
            //     operation: 'validate'
            // });

            // Simulate successful processing
            const result = { success: true, message: 'Validated successfully' };

            if (result.success) {
                this.setComplete(true);
                this.handleNext();
            } else {
                this.setError(result.message);
            }
        } catch (err) {
            this.setError(this.reduceErrors(err));
        } finally {
            this.isLoading = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // COMPUTED PROPERTIES
    // ═══════════════════════════════════════════════════════════════════════

    get hasRecords() {
        return this.records && this.records.length > 0;
    }

    get hasSelection() {
        return !!this._selectedId;
    }

    get canGoBack() {
        return this.availableActions.includes('BACK');
    }

    get canGoNext() {
        return this.availableActions.includes('NEXT');
    }

    get canFinish() {
        return this.availableActions.includes('FINISH');
    }

    get canPause() {
        return this.availableActions.includes('PAUSE');
    }

    get showBackButton() {
        return this.canGoBack;
    }

    get showNextButton() {
        return this.canGoNext;
    }

    get showFinishButton() {
        return this.canFinish && !this.canGoNext;
    }

    /**
     * Compute selected class for record tiles
     */
    getRecordClass(recordId) {
        return this._selectedId === recordId
            ? 'slds-box slds-box_link slds-theme_shade slds-is-selected'
            : 'slds-box slds-box_link';
    }

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Reduce various error formats to a string
     * @param {*} errors - Error object(s)
     * @returns {String} - Formatted error message
     */
    reduceErrors(errors) {
        if (!Array.isArray(errors)) {
            errors = [errors];
        }

        return errors
            .filter(error => !!error)
            .map(error => {
                if (error.body?.message) return error.body.message;
                if (error.message) return error.message;
                return JSON.stringify(error);
            })
            .join('; ');
    }
}
