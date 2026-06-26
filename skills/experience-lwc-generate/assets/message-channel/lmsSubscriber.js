/**
 * LIGHTNING MESSAGE SERVICE - SUBSCRIBER TEMPLATE
 *
 * This component demonstrates subscribing to messages via LMS.
 * The subscriber listens for messages published on a channel
 * and reacts to them.
 *
 * Replace: lmsSubscriber → yourComponentName
 */

import { LightningElement, wire } from 'lwc';
import {
    subscribe,
    unsubscribe,
    APPLICATION_SCOPE,
    MessageContext
} from 'lightning/messageService';
import RECORD_SELECTED_CHANNEL from '@salesforce/messageChannel/RecordSelected__c';

export default class LmsSubscriber extends LightningElement {
    // ═══════════════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════════════

    subscription = null;
    receivedMessage = null;

    // Store received data for display
    selectedRecordId;
    selectedRecordName;
    sourceComponent;
    timestamp;

    // ═══════════════════════════════════════════════════════════════════════
    // MESSAGE CONTEXT
    // ═══════════════════════════════════════════════════════════════════════

    @wire(MessageContext)
    messageContext;

    // ═══════════════════════════════════════════════════════════════════════
    // LIFECYCLE HOOKS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Subscribe to the message channel when component connects
     */
    connectedCallback() {
        this.subscribeToMessageChannel();
    }

    /**
     * Unsubscribe when component disconnects to prevent memory leaks
     */
    disconnectedCallback() {
        this.unsubscribeToMessageChannel();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SUBSCRIPTION MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Subscribe to the message channel
     *
     * Options:
     * - No scope: Only receive messages from same page
     * - APPLICATION_SCOPE: Receive messages across the entire application
     */
    subscribeToMessageChannel() {
        // Avoid duplicate subscriptions
        if (this.subscription) {
            return;
        }

        // Subscribe with APPLICATION_SCOPE to receive messages from anywhere
        this.subscription = subscribe(
            this.messageContext,
            RECORD_SELECTED_CHANNEL,
            (message) => this.handleMessage(message),
            { scope: APPLICATION_SCOPE }
        );

        console.log('Subscribed to RecordSelected channel');
    }

    /**
     * Unsubscribe from the message channel
     */
    unsubscribeToMessageChannel() {
        if (this.subscription) {
            unsubscribe(this.subscription);
            this.subscription = null;
            console.log('Unsubscribed from RecordSelected channel');
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // MESSAGE HANDLING
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Handle incoming messages
     * This is called whenever a message is published to the channel
     */
    handleMessage(message) {
        console.log('Received message:', message);

        // Store the raw message for debugging
        this.receivedMessage = message;

        // Extract fields from the message
        this.selectedRecordId = message.recordId;
        this.selectedRecordName = message.recordName;
        this.sourceComponent = message.sourceComponent;
        this.timestamp = message.timestamp;

        // Handle complex payload if present
        if (message.payload) {
            try {
                const additionalData = JSON.parse(message.payload);
                this.handleAdditionalData(additionalData);
            } catch (e) {
                console.error('Failed to parse payload:', e);
            }
        }

        // Ignore messages from self (optional)
        if (message.sourceComponent === 'lmsSubscriber') {
            console.log('Ignoring self-published message');
            return;
        }

        // React to the message
        this.onRecordSelected(message.recordId, message.recordName);
    }

    /**
     * Handle additional data from complex payload
     */
    handleAdditionalData(data) {
        console.log('Additional data:', data);
        // Process additional data as needed
    }

    /**
     * Custom logic when a record is selected
     */
    onRecordSelected(recordId, recordName) {
        // Example: Refresh child component data
        // Example: Update URL parameters
        // Example: Fetch related records

        console.log(`Record selected: ${recordName} (${recordId})`);

        // Dispatch event for any parent components
        this.dispatchEvent(new CustomEvent('recordchange', {
            detail: {
                recordId,
                recordName
            }
        }));
    }

    // ═══════════════════════════════════════════════════════════════════════
    // GETTERS FOR TEMPLATE
    // ═══════════════════════════════════════════════════════════════════════

    get hasSelection() {
        return !!this.selectedRecordId;
    }

    get formattedTimestamp() {
        if (!this.timestamp) return '';
        return new Date(this.timestamp).toLocaleString();
    }

    get debugInfo() {
        return JSON.stringify(this.receivedMessage, null, 2);
    }
}
