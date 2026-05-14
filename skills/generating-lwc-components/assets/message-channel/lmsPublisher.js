/**
 * LIGHTNING MESSAGE SERVICE - PUBLISHER TEMPLATE
 *
 * This component demonstrates publishing messages via LMS.
 * Use LMS when components need to communicate but:
 * - Don't have a parent-child relationship
 * - Are in different parts of the page
 * - Need to communicate between LWC, Aura, and Visualforce
 *
 * Replace: lmsPublisher → yourComponentName
 */

import { LightningElement, wire } from 'lwc';
import { publish, MessageContext } from 'lightning/messageService';
import RECORD_SELECTED_CHANNEL from '@salesforce/messageChannel/RecordSelected__c';

export default class LmsPublisher extends LightningElement {
    // ═══════════════════════════════════════════════════════════════════════
    // MESSAGE CONTEXT
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * MessageContext provides the scope for publishing/subscribing.
     * Wire it to get the current context automatically.
     */
    @wire(MessageContext)
    messageContext;

    // ═══════════════════════════════════════════════════════════════════════
    // PUBLISH METHODS
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Publish a simple message with record selection
     */
    handleRecordSelect(event) {
        const recordId = event.target.dataset.id;
        const recordName = event.target.dataset.name;

        // Create message payload
        const payload = {
            recordId: recordId,
            recordName: recordName,
            objectApiName: 'Account',
            sourceComponent: 'lmsPublisher',
            timestamp: new Date().toISOString()
        };

        // Publish to the message channel
        publish(this.messageContext, RECORD_SELECTED_CHANNEL, payload);

        console.log('Published message:', payload);
    }

    /**
     * Publish with complex payload (JSON string for nested data)
     */
    publishWithComplexPayload(recordData) {
        const payload = {
            recordId: recordData.Id,
            recordName: recordData.Name,
            objectApiName: 'Account',
            sourceComponent: 'lmsPublisher',
            timestamp: new Date().toISOString(),
            payload: JSON.stringify({
                additionalField1: recordData.field1,
                additionalField2: recordData.field2,
                nestedObject: {
                    key1: 'value1',
                    key2: 'value2'
                }
            })
        };

        publish(this.messageContext, RECORD_SELECTED_CHANNEL, payload);
    }

    /**
     * Publish from imperative action (e.g., after Apex call)
     */
    async handleSaveAndPublish() {
        try {
            // Perform some action
            const result = await this.saveRecord();

            // Publish result to other components
            publish(this.messageContext, RECORD_SELECTED_CHANNEL, {
                recordId: result.Id,
                recordName: result.Name,
                objectApiName: 'Account',
                sourceComponent: 'lmsPublisher',
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            console.error('Save failed:', error);
        }
    }

    // Placeholder for actual save logic
    async saveRecord() {
        return { Id: '001xx000000000', Name: 'Test Account' };
    }
}
