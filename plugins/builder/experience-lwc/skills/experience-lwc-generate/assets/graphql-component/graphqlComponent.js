/**
 * GraphQL Component Template
 *
 * Demonstrates GraphQL patterns for LWC with:
 * - GraphQL query definition using gql tagged template
 * - GraphQL mutations (Create, Update, Delete) - Spring '26 GA
 * - Cursor-based pagination
 * - Reactive variables
 * - Error handling
 * - Data transformation
 *
 * Module: lightning/graphql supersedes lightning/uiGraphQLApi
 * Requires: API 66.0+ for mutations (GA in Spring '26)
 *
 * @see https://developer.salesforce.com/docs/platform/lwc/guide/data-graphql.html
 */
import { LightningElement, wire, track } from 'lwc';
import { gql, graphql, refreshGraphQL, executeMutation } from 'lightning/graphql';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

// ═══════════════════════════════════════════════════════════════════════════
// GRAPHQL QUERY
// ═══════════════════════════════════════════════════════════════════════════
const CONTACTS_QUERY = gql`
    query ContactsWithAccount($first: Int!, $after: String, $orderBy: ContactOrderByInput) {
        uiapi {
            query {
                Contact(first: $first, after: $after, orderBy: $orderBy) {
                    edges {
                        node {
                            Id
                            Name { value }
                            Email { value }
                            Phone { value }
                            Title { value }
                            Account {
                                Id
                                Name { value }
                            }
                        }
                        cursor
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        endCursor
                        startCursor
                    }
                    totalCount
                }
            }
        }
    }
`;

// ═══════════════════════════════════════════════════════════════════════════
// GRAPHQL MUTATIONS (Spring '26 - API 66.0+)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Create a new Contact record
 * Returns the newly created record fields
 */
const CREATE_CONTACT = gql`
    mutation CreateContact($firstName: String, $lastName: String!, $email: String, $accountId: ID) {
        uiapi {
            ContactCreate(input: {
                Contact: {
                    FirstName: $firstName
                    LastName: $lastName
                    Email: $email
                    AccountId: $accountId
                }
            }) {
                Record {
                    Id
                    Name { value }
                    Email { value }
                }
            }
        }
    }
`;

/**
 * Update an existing Contact record
 * Note: Cannot query fields in update response
 */
const UPDATE_CONTACT = gql`
    mutation UpdateContact($id: ID!, $firstName: String, $lastName: String, $email: String) {
        uiapi {
            ContactUpdate(input: {
                Contact: {
                    Id: $id
                    FirstName: $firstName
                    LastName: $lastName
                    Email: $email
                }
            }) {
                Record {
                    Id
                }
            }
        }
    }
`;

/**
 * Delete a Contact record
 */
const DELETE_CONTACT = gql`
    mutation DeleteContact($id: ID!) {
        uiapi {
            ContactDelete(input: { Contact: { Id: $id } }) {
                Id
            }
        }
    }
`;

export default class GraphqlComponent extends LightningElement {
    // Data state
    @track contacts = [];
    pageInfo;
    totalCount = 0;
    error;
    isLoading = true;

    // Pagination state
    _pageSize = 10;
    _cursor = null;

    // Store the wire result for refresh
    _wiredResult;

    /**
     * Wire the GraphQL query with reactive variables
     * Variables are recalculated whenever queryVariables getter returns new values
     */
    @wire(graphql, {
        query: CONTACTS_QUERY,
        variables: '$queryVariables'
    })
    wiredContacts(result) {
        this._wiredResult = result;
        const { data, error } = result;

        this.isLoading = false;

        if (data) {
            const queryResult = data.uiapi.query.Contact;

            // Transform GraphQL response to flat structure
            this.contacts = queryResult.edges.map(edge => ({
                id: edge.node.Id,
                name: edge.node.Name?.value,
                email: edge.node.Email?.value,
                phone: edge.node.Phone?.value,
                title: edge.node.Title?.value,
                accountId: edge.node.Account?.Id,
                accountName: edge.node.Account?.Name?.value,
                cursor: edge.cursor
            }));

            this.pageInfo = queryResult.pageInfo;
            this.totalCount = queryResult.totalCount;
            this.error = undefined;
        } else if (error) {
            this.error = this._reduceErrors(error);
            this.contacts = [];
        }
    }

    get queryVariables() {
        return {
            first: this._pageSize,
            after: this._cursor,
            orderBy: { Name: { order: 'ASC' } }
        };
    }

    get hasData() {
        return this.contacts.length > 0;
    }

    get hasNoData() {
        return !this.isLoading && !this.error && this.contacts.length === 0;
    }

    get hasNextPage() {
        return this.pageInfo?.hasNextPage;
    }

    get currentPageInfo() {
        return `Showing ${this.contacts.length} of ${this.totalCount} contacts`;
    }

    handleLoadMore() {
        if (this.hasNextPage) {
            this.isLoading = true;
            this._cursor = this.pageInfo.endCursor;
        }
    }

    handleRefresh() {
        this.isLoading = true;
        this._cursor = null;
        refreshGraphQL(this._wiredResult);
    }

    handleRowClick(event) {
        const contactId = event.currentTarget.dataset.id;
        this.dispatchEvent(new CustomEvent('contactselected', {
            detail: { contactId },
            bubbles: true,
            composed: true
        }));
    }

    _reduceErrors(errors) {
        if (!Array.isArray(errors)) {
            errors = [errors];
        }
        return errors
            .filter(error => !!error)
            .map(error => {
                if (typeof error === 'string') return error;
                if (error.body?.message) return error.body.message;
                if (error.message) return error.message;
                return 'Unknown error';
            })
            .join('; ');
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MUTATION METHODS (Spring '26 - API 66.0+)
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Create a new Contact via GraphQL mutation
     * @param {Object} contactData - { firstName, lastName, email, accountId }
     * @returns {Promise<Object>} - Created record
     */
    async createContact(contactData) {
        try {
            const result = await executeMutation(CREATE_CONTACT, {
                variables: {
                    firstName: contactData.firstName || null,
                    lastName: contactData.lastName,
                    email: contactData.email || null,
                    accountId: contactData.accountId || null
                }
            });

            const newRecord = result.data.uiapi.ContactCreate.Record;
            this._showToast('Success', `Contact "${newRecord.Name.value}" created`, 'success');

            // Refresh the query to show new record
            await refreshGraphQL(this._wiredResult);

            return newRecord;
        } catch (error) {
            this._handleMutationError(error);
            throw error;
        }
    }

    /**
     * Update an existing Contact via GraphQL mutation
     * @param {String} contactId - ID of contact to update
     * @param {Object} updates - { firstName, lastName, email }
     * @returns {Promise<Object>} - Updated record ID
     */
    async updateContact(contactId, updates) {
        try {
            const result = await executeMutation(UPDATE_CONTACT, {
                variables: {
                    id: contactId,
                    firstName: updates.firstName,
                    lastName: updates.lastName,
                    email: updates.email
                }
            });

            this._showToast('Success', 'Contact updated successfully', 'success');

            // Refresh the query to show updated data
            await refreshGraphQL(this._wiredResult);

            return result.data.uiapi.ContactUpdate.Record;
        } catch (error) {
            this._handleMutationError(error);
            throw error;
        }
    }

    /**
     * Delete a Contact via GraphQL mutation
     * @param {String} contactId - ID of contact to delete
     */
    async deleteContact(contactId) {
        try {
            await executeMutation(DELETE_CONTACT, {
                variables: { id: contactId }
            });

            this._showToast('Success', 'Contact deleted successfully', 'success');

            // Refresh the query to remove deleted record
            await refreshGraphQL(this._wiredResult);
        } catch (error) {
            this._handleMutationError(error);
            throw error;
        }
    }

    /**
     * Handle mutation errors with proper GraphQL error parsing
     */
    _handleMutationError(error) {
        let message;
        if (error.graphQLErrors && error.graphQLErrors.length > 0) {
            message = error.graphQLErrors.map(e => e.message).join(', ');
        } else {
            message = error.message || 'An unknown error occurred';
        }
        this._showToast('Error', message, 'error');
    }

    /**
     * Display toast notification
     */
    _showToast(title, message, variant) {
        this.dispatchEvent(new ShowToastEvent({ title, message, variant }));
    }
}
