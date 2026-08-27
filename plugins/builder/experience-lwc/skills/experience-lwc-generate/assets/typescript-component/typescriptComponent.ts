/**
 * TypeScript LWC Component Template
 *
 * Demonstrates TypeScript usage in Lightning Web Components with:
 * - Type definitions using @salesforce/lightning-types
 * - Typed wire service patterns
 * - Generic type parameters
 * - Interface definitions
 * - Strict null checking
 *
 * Requires: API 66.0+ (Spring '26)
 * Setup: npm install @salesforce/lightning-types @salesforce/i18n lwc
 *
 * @see https://developer.salesforce.com/docs/platform/lwc/guide/ts.html
 */
import { LightningElement, api, wire, track } from 'lwc';
import { getRecord, getFieldValue, updateRecord } from 'lightning/uiRecordApi';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { refreshApex } from '@salesforce/apex';

// Import Apex controller with type definitions
import getAccounts from '@salesforce/apex/AccountController.getAccounts';

// Import schema for type safety
import ACCOUNT_NAME_FIELD from '@salesforce/schema/Account.Name';
import ACCOUNT_INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';
import ACCOUNT_REVENUE_FIELD from '@salesforce/schema/Account.AnnualRevenue';
import ACCOUNT_ID_FIELD from '@salesforce/schema/Account.Id';

// ═══════════════════════════════════════════════════════════════════════════
// TYPE DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Account record interface matching Salesforce object
 */
interface AccountRecord {
    Id: string;
    Name: string;
    Industry?: string;
    AnnualRevenue?: number;
}

/**
 * Wire result type for Apex calls
 */
interface WireResult<T> {
    data?: T;
    error?: Error;
}

/**
 * Apex wire result with refresh support
 */
interface ApexWireResult<T> extends WireResult<T> {
    // Full result object for refreshApex
}

/**
 * LDS Record result type
 */
interface RecordResult {
    data?: {
        id: string;
        fields: Record<string, { value: unknown }>;
    };
    error?: Error;
}

/**
 * Component configuration props
 */
interface ComponentConfig {
    maxRecords: number;
    sortField: keyof AccountRecord;
    sortDirection: 'ASC' | 'DESC';
}

// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const DEFAULT_CONFIG: ComponentConfig = {
    maxRecords: 10,
    sortField: 'Name',
    sortDirection: 'ASC'
};

const ACCOUNT_FIELDS = [
    ACCOUNT_NAME_FIELD,
    ACCOUNT_INDUSTRY_FIELD,
    ACCOUNT_REVENUE_FIELD
];

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT CLASS
// ═══════════════════════════════════════════════════════════════════════════

export default class TypescriptComponent extends LightningElement {
    // ─────────────────────────────────────────────────────────────────────
    // Public API Properties (typed)
    // ─────────────────────────────────────────────────────────────────────

    @api recordId: string | undefined;

    @api
    get maxRecords(): number {
        return this._config.maxRecords;
    }
    set maxRecords(value: number) {
        this._config = { ...this._config, maxRecords: value };
    }

    // ─────────────────────────────────────────────────────────────────────
    // Private Properties (tracked for reactivity)
    // ─────────────────────────────────────────────────────────────────────

    @track private _accounts: AccountRecord[] = [];
    @track private _selectedAccount: AccountRecord | null = null;
    @track private _error: string | null = null;
    @track private _isLoading: boolean = true;

    private _config: ComponentConfig = { ...DEFAULT_CONFIG };
    private _wiredAccountsResult: ApexWireResult<AccountRecord[]> | undefined;

    // ─────────────────────────────────────────────────────────────────────
    // Wire Services (typed)
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Wire Apex method with typed result handling
     */
    @wire(getAccounts, { maxRecords: '$maxRecords' })
    wiredAccounts(result: ApexWireResult<AccountRecord[]>): void {
        this._wiredAccountsResult = result;
        const { data, error } = result;

        this._isLoading = false;

        if (data) {
            this._accounts = this.sortAccounts(data);
            this._error = null;
        } else if (error) {
            this._error = this.reduceErrors(error);
            this._accounts = [];
        }
    }

    /**
     * Wire LDS getRecord with typed result
     */
    @wire(getRecord, { recordId: '$recordId', fields: ACCOUNT_FIELDS })
    wiredRecord(result: RecordResult): void {
        if (result.data) {
            this._selectedAccount = {
                Id: result.data.id,
                Name: getFieldValue(result.data, ACCOUNT_NAME_FIELD) as string,
                Industry: getFieldValue(result.data, ACCOUNT_INDUSTRY_FIELD) as string | undefined,
                AnnualRevenue: getFieldValue(result.data, ACCOUNT_REVENUE_FIELD) as number | undefined
            };
        } else if (result.error) {
            this._error = this.reduceErrors(result.error);
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // Getters (computed properties)
    // ─────────────────────────────────────────────────────────────────────

    get accounts(): AccountRecord[] {
        return this._accounts;
    }

    get hasAccounts(): boolean {
        return this._accounts.length > 0;
    }

    get isLoading(): boolean {
        return this._isLoading;
    }

    get errorMessage(): string | null {
        return this._error;
    }

    get hasError(): boolean {
        return this._error !== null;
    }

    get selectedAccountName(): string {
        return this._selectedAccount?.Name ?? 'No account selected';
    }

    get formattedRevenue(): string {
        const revenue = this._selectedAccount?.AnnualRevenue;
        if (revenue === undefined || revenue === null) {
            return 'N/A';
        }
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(revenue);
    }

    // ─────────────────────────────────────────────────────────────────────
    // Event Handlers (typed parameters)
    // ─────────────────────────────────────────────────────────────────────

    handleAccountSelect(event: CustomEvent<{ accountId: string }>): void {
        const { accountId } = event.detail;
        const account = this._accounts.find(a => a.Id === accountId);

        if (account) {
            this._selectedAccount = account;
            this.dispatchAccountSelected(account);
        }
    }

    handleRefresh(): void {
        this._isLoading = true;
        if (this._wiredAccountsResult) {
            refreshApex(this._wiredAccountsResult);
        }
    }

    async handleUpdate(event: CustomEvent<{ field: keyof AccountRecord; value: string | number }>): Promise<void> {
        const { field, value } = event.detail;

        if (!this._selectedAccount?.Id) {
            this.showToast('Error', 'No account selected', 'error');
            return;
        }

        try {
            const fields: Record<string, unknown> = {
                [ACCOUNT_ID_FIELD.fieldApiName]: this._selectedAccount.Id,
                [field]: value
            };

            await updateRecord({ fields });

            this.showToast('Success', 'Account updated successfully', 'success');
            this.handleRefresh();
        } catch (error) {
            this.showToast('Error', this.reduceErrors(error as Error), 'error');
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // Private Methods (typed)
    // ─────────────────────────────────────────────────────────────────────

    private sortAccounts(accounts: AccountRecord[]): AccountRecord[] {
        const { sortField, sortDirection } = this._config;

        return [...accounts].sort((a, b) => {
            const aVal = a[sortField];
            const bVal = b[sortField];

            if (aVal === undefined || aVal === null) return 1;
            if (bVal === undefined || bVal === null) return -1;

            const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            return sortDirection === 'ASC' ? comparison : -comparison;
        });
    }

    private reduceErrors(error: Error | Error[]): string {
        const errors = Array.isArray(error) ? error : [error];

        return errors
            .filter((e): e is Error => e !== null && e !== undefined)
            .map(e => {
                if (typeof e === 'string') return e;
                if ('body' in e && typeof (e as { body?: { message?: string } }).body?.message === 'string') {
                    return (e as { body: { message: string } }).body.message;
                }
                return e.message || 'Unknown error';
            })
            .join('; ');
    }

    private dispatchAccountSelected(account: AccountRecord): void {
        const event = new CustomEvent<{ account: AccountRecord }>('accountselected', {
            detail: { account },
            bubbles: true,
            composed: true
        });
        this.dispatchEvent(event);
    }

    private showToast(title: string, message: string, variant: 'success' | 'error' | 'warning' | 'info'): void {
        this.dispatchEvent(new ShowToastEvent({ title, message, variant }));
    }
}
