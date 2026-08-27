/**
 * DATATABLE LWC COMPONENT TEMPLATE
 *
 * This template demonstrates lightning-datatable with:
 * - Column configuration
 * - Row selection (single/multi)
 * - Inline editing
 * - Sorting
 * - Infinite scrolling
 * - Row actions
 *
 * Replace: datatableComponent → yourComponentName
 */

import { LightningElement, api, wire, track } from 'lwc';
import { refreshApex } from '@salesforce/apex';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { NavigationMixin } from 'lightning/navigation';
import getRecords from '@salesforce/apex/DatatableController.getRecords';
import updateRecords from '@salesforce/apex/DatatableController.updateRecords';
import deleteRecords from '@salesforce/apex/DatatableController.deleteRecords';

// Row actions
const actions = [
    { label: 'View', name: 'view' },
    { label: 'Edit', name: 'edit' },
    { label: 'Delete', name: 'delete' }
];

// Column definitions
const COLUMNS = [
    {
        label: 'Account Name',
        fieldName: 'nameUrl',
        type: 'url',
        typeAttributes: {
            label: { fieldName: 'Name' },
            target: '_blank'
        },
        sortable: true
    },
    {
        label: 'Industry',
        fieldName: 'Industry',
        type: 'text',
        sortable: true,
        editable: true
    },
    {
        label: 'Annual Revenue',
        fieldName: 'AnnualRevenue',
        type: 'currency',
        typeAttributes: {
            currencyCode: 'USD',
            minimumFractionDigits: 0
        },
        sortable: true,
        editable: true,
        cellAttributes: { alignment: 'right' }
    },
    {
        label: 'Phone',
        fieldName: 'Phone',
        type: 'phone',
        editable: true
    },
    {
        label: 'Created Date',
        fieldName: 'CreatedDate',
        type: 'date',
        typeAttributes: {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        },
        sortable: true
    },
    {
        label: 'Active',
        fieldName: 'IsActive__c',
        type: 'boolean',
        editable: true
    },
    {
        type: 'action',
        typeAttributes: { rowActions: actions }
    }
];

export default class DatatableComponent extends NavigationMixin(LightningElement) {
    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API
    // ═══════════════════════════════════════════════════════════════════════

    @api recordId;
    @api maxRows = 50;
    @api enableInfiniteScroll = false;
    @api showRowNumbers = false;

    // ═══════════════════════════════════════════════════════════════════════
    // PRIVATE PROPERTIES
    // ═══════════════════════════════════════════════════════════════════════

    columns = COLUMNS;
    @track data = [];
    error;
    isLoading = true;

    // Sorting
    sortBy;
    sortDirection = 'asc';

    // Selection
    selectedRows = [];
    draftValues = [];

    // Infinite scroll
    offset = 0;
    loadMoreStatus;
    totalRecords = 0;

    // Wire result for refresh
    wiredRecordsResult;

    // ═══════════════════════════════════════════════════════════════════════
    // WIRE SERVICE
    // ═══════════════════════════════════════════════════════════════════════

    @wire(getRecords, {
        parentId: '$recordId',
        limitSize: '$maxRows',
        offset: '$offset',
        sortBy: '$sortBy',
        sortDirection: '$sortDirection'
    })
    wiredRecords(result) {
        this.wiredRecordsResult = result;
        this.isLoading = false;

        const { data, error } = result;

        if (data) {
            // Add URL field for navigation
            this.data = data.records.map(record => ({
                ...record,
                nameUrl: `/${record.Id}`
            }));
            this.totalRecords = data.totalCount;
            this.error = undefined;
        } else if (error) {
            this.error = this.reduceErrors(error);
            this.data = [];
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // GETTERS
    // ═══════════════════════════════════════════════════════════════════════

    get hasData() {
        return this.data && this.data.length > 0;
    }

    get hasSelection() {
        return this.selectedRows && this.selectedRows.length > 0;
    }

    get selectedCount() {
        return this.selectedRows.length;
    }

    get tableTitle() {
        return `Accounts (${this.totalRecords})`;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SORTING
    // ═══════════════════════════════════════════════════════════════════════

    handleSort(event) {
        this.sortBy = event.detail.fieldName;
        this.sortDirection = event.detail.sortDirection;
        this.isLoading = true;
        // Wire will automatically refetch with new sort params
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SELECTION
    // ═══════════════════════════════════════════════════════════════════════

    handleRowSelection(event) {
        this.selectedRows = event.detail.selectedRows;

        // Dispatch event for parent
        this.dispatchEvent(new CustomEvent('selection', {
            detail: {
                selectedRows: this.selectedRows,
                selectedIds: this.selectedRows.map(row => row.Id)
            }
        }));
    }

    // ═══════════════════════════════════════════════════════════════════════
    // ROW ACTIONS
    // ═══════════════════════════════════════════════════════════════════════

    handleRowAction(event) {
        const actionName = event.detail.action.name;
        const row = event.detail.row;

        switch (actionName) {
            case 'view':
                this.navigateToView(row.Id);
                break;
            case 'edit':
                this.navigateToEdit(row.Id);
                break;
            case 'delete':
                this.handleDeleteRow(row);
                break;
            default:
                break;
        }
    }

    navigateToView(recordId) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: recordId,
                objectApiName: 'Account',
                actionName: 'view'
            }
        });
    }

    navigateToEdit(recordId) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: recordId,
                objectApiName: 'Account',
                actionName: 'edit'
            }
        });
    }

    async handleDeleteRow(row) {
        if (!confirm(`Delete ${row.Name}?`)) {
            return;
        }

        this.isLoading = true;
        try {
            await deleteRecords({ recordIds: [row.Id] });
            this.showToast('Success', 'Record deleted', 'success');
            await this.refresh();
        } catch (error) {
            this.showToast('Error', this.reduceErrors(error), 'error');
        } finally {
            this.isLoading = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // INLINE EDITING
    // ═══════════════════════════════════════════════════════════════════════

    handleCellChange(event) {
        this.draftValues = event.detail.draftValues;
    }

    async handleSave(event) {
        const updatedFields = event.detail.draftValues;
        this.isLoading = true;

        try {
            await updateRecords({ records: updatedFields });
            this.showToast('Success', 'Records updated', 'success');
            this.draftValues = [];
            await this.refresh();
        } catch (error) {
            this.showToast('Error', this.reduceErrors(error), 'error');
        } finally {
            this.isLoading = false;
        }
    }

    handleCancel() {
        this.draftValues = [];
    }

    // ═══════════════════════════════════════════════════════════════════════
    // INFINITE SCROLLING
    // ═══════════════════════════════════════════════════════════════════════

    loadMoreData(event) {
        if (!this.enableInfiniteScroll) return;

        const { target } = event;
        target.isLoading = true;

        if (this.data.length >= this.totalRecords) {
            target.enableInfiniteLoading = false;
            this.loadMoreStatus = 'All records loaded';
            target.isLoading = false;
            return;
        }

        this.offset = this.data.length;
        // Wire will load more data
    }

    // ═══════════════════════════════════════════════════════════════════════
    // BULK ACTIONS
    // ═══════════════════════════════════════════════════════════════════════

    async handleBulkDelete() {
        if (!this.hasSelection) return;

        const selectedIds = this.selectedRows.map(row => row.Id);

        if (!confirm(`Delete ${selectedIds.length} records?`)) {
            return;
        }

        this.isLoading = true;
        try {
            await deleteRecords({ recordIds: selectedIds });
            this.showToast('Success', `${selectedIds.length} records deleted`, 'success');
            this.selectedRows = [];
            await this.refresh();
        } catch (error) {
            this.showToast('Error', this.reduceErrors(error), 'error');
        } finally {
            this.isLoading = false;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════

    async refresh() {
        this.isLoading = true;
        await refreshApex(this.wiredRecordsResult);
        this.isLoading = false;
    }

    handleRefresh() {
        this.refresh();
    }

    showToast(title, message, variant) {
        this.dispatchEvent(new ShowToastEvent({ title, message, variant }));
    }

    reduceErrors(errors) {
        if (!Array.isArray(errors)) errors = [errors];
        return errors
            .filter(e => !!e)
            .map(e => e.body?.message || e.message || JSON.stringify(e))
            .join(', ');
    }
}
