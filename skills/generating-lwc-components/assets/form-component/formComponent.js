/**
 * FORM LWC COMPONENT TEMPLATE
 *
 * This template demonstrates a form component with:
 * - lightning-record-edit-form for standard forms
 * - Custom validation
 * - Imperative Apex submission
 * - Toast notifications
 *
 * Replace: formComponent → yourComponentName
 * Replace: FormComponent → YourComponentName
 */

import { LightningElement, api, wire } from 'lwc';
import { getObjectInfo } from 'lightning/uiObjectInfoApi';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { NavigationMixin } from 'lightning/navigation';
import saveRecord from '@salesforce/apex/FormComponentController.saveRecord';

// Import schema for field references
import ACCOUNT_OBJECT from '@salesforce/schema/Account';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';
import PHONE_FIELD from '@salesforce/schema/Account.Phone';

export default class FormComponent extends NavigationMixin(LightningElement) {
    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════════

    @api recordId;           // For edit mode
    @api objectApiName = 'Account';

    // ═══════════════════════════════════════════════════════════════════════
    // PRIVATE PROPERTIES
    // ═══════════════════════════════════════════════════════════════════════

    isLoading = false;
    recordTypeId;

    // Field values for custom form
    formData = {
        Name: '',
        Industry: '',
        Phone: ''
    };

    // ═══════════════════════════════════════════════════════════════════════
    // SCHEMA REFERENCES
    // ═══════════════════════════════════════════════════════════════════════

    accountObject = ACCOUNT_OBJECT;
    nameField = NAME_FIELD;
    industryField = INDUSTRY_FIELD;
    phoneField = PHONE_FIELD;

    // ═══════════════════════════════════════════════════════════════════════
    // WIRE SERVICE
    // ═══════════════════════════════════════════════════════════════════════

    @wire(getObjectInfo, { objectApiName: ACCOUNT_OBJECT })
    objectInfo({ data, error }) {
        if (data) {
            // Get default record type
            this.recordTypeId = data.defaultRecordTypeId;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // GETTERS
    // ═══════════════════════════════════════════════════════════════════════

    get isEditMode() {
        return !!this.recordId;
    }

    get cardTitle() {
        return this.isEditMode ? 'Edit Account' : 'New Account';
    }

    get submitButtonLabel() {
        return this.isEditMode ? 'Save' : 'Create';
    }

    // ═══════════════════════════════════════════════════════════════════════
    // LIGHTNING-RECORD-EDIT-FORM HANDLERS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Called when the form loads successfully
     */
    handleLoad(event) {
        this.isLoading = false;
        console.log('Form loaded', event.detail);
    }

    /**
     * Called when the record is saved successfully
     */
    handleSuccess(event) {
        this.isLoading = false;
        const recordId = event.detail.id;
        const recordName = event.detail.fields.Name.value;

        this.showToast(
            'Success',
            `Account "${recordName}" ${this.isEditMode ? 'updated' : 'created'} successfully`,
            'success'
        );

        // Dispatch event for parent components
        this.dispatchEvent(new CustomEvent('save', {
            detail: { recordId, recordName }
        }));

        // Navigate to record page
        if (!this.isEditMode) {
            this.navigateToRecord(recordId);
        }
    }

    /**
     * Called when there's an error saving
     */
    handleError(event) {
        this.isLoading = false;
        const errorMessage = event.detail.message || 'An error occurred';

        this.showToast('Error', errorMessage, 'error');

        console.error('Form error:', event.detail);
    }

    /**
     * Called before the form submits - opportunity to validate
     */
    handleSubmit(event) {
        event.preventDefault();  // Stop default submission

        // Custom validation
        const fields = event.detail.fields;

        if (!this.validateForm(fields)) {
            return;
        }

        this.isLoading = true;

        // Modify fields if needed before submission
        // fields.Custom_Field__c = 'Computed Value';

        // Submit the form
        this.template.querySelector('lightning-record-edit-form').submit(fields);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // CUSTOM FORM HANDLERS (Alternative to lightning-record-edit-form)
    // ═══════════════════════════════════════════════════════════════════════

    handleInputChange(event) {
        const field = event.target.name || event.target.dataset.field;
        const value = event.target.value;
        this.formData = { ...this.formData, [field]: value };
    }

    async handleCustomSubmit() {
        if (!this.validateCustomForm()) {
            return;
        }

        this.isLoading = true;

        try {
            const result = await saveRecord({
                recordData: JSON.stringify(this.formData),
                recordId: this.recordId
            });

            this.showToast('Success', 'Record saved successfully', 'success');

            this.dispatchEvent(new CustomEvent('save', {
                detail: { recordId: result.Id }
            }));

        } catch (error) {
            const errorMessage = error.body?.message || error.message || 'Unknown error';
            this.showToast('Error', errorMessage, 'error');
        } finally {
            this.isLoading = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // VALIDATION
    // ═══════════════════════════════════════════════════════════════════════

    validateForm(fields) {
        // Custom validation logic
        if (fields.Name && fields.Name.length < 2) {
            this.showToast('Validation Error', 'Name must be at least 2 characters', 'error');
            return false;
        }

        // Validate all input fields
        const allValid = [...this.template.querySelectorAll('lightning-input-field')]
            .reduce((validSoFar, inputField) => {
                inputField.reportValidity();
                return validSoFar && inputField.checkValidity();
            }, true);

        return allValid;
    }

    validateCustomForm() {
        const inputFields = this.template.querySelectorAll('lightning-input, lightning-combobox');
        let isValid = true;

        inputFields.forEach(field => {
            if (!field.checkValidity()) {
                field.reportValidity();
                isValid = false;
            }
        });

        return isValid;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // BUTTON HANDLERS
    // ═══════════════════════════════════════════════════════════════════════

    handleCancel() {
        // Reset form
        const inputFields = this.template.querySelectorAll('lightning-input-field');
        inputFields.forEach(field => {
            field.reset();
        });

        this.dispatchEvent(new CustomEvent('cancel'));
    }

    handleReset() {
        const inputFields = this.template.querySelectorAll('lightning-input-field');
        inputFields.forEach(field => {
            field.reset();
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    // NAVIGATION
    // ═══════════════════════════════════════════════════════════════════════

    navigateToRecord(recordId) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: recordId,
                objectApiName: this.objectApiName,
                actionName: 'view'
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════

    showToast(title, message, variant) {
        this.dispatchEvent(new ShowToastEvent({
            title,
            message,
            variant
        }));
    }
}
