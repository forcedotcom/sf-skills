/**
 * Composable Modal Component Template
 *
 * Based on James Simone's composable modal pattern with:
 * - Focus trap implementation
 * - ESC key to close
 * - Backdrop click to close
 * - Slot-based composition
 * - ARIA accessibility attributes
 * - Proper cleanup on disconnect
 *
 * @see https://www.jamessimone.net/blog/joys-of-apex/lwc-composable-modal/
 */
import { LightningElement, api } from 'lwc';

const OUTER_MODAL_CLASS = 'outerModalContent';
const ESCAPE_KEY = 'Escape';
const TAB_KEY = 'Tab';

export default class ModalComponent extends LightningElement {
    // Public API properties
    @api modalHeader;
    @api modalTagline;
    @api modalSaveHandler;
    @api hideFooter = false;
    @api size = 'medium'; // small, medium, large

    // Private state
    _isOpen = false;
    _focusableElements = [];
    _boundHandleKeyUp;

    constructor() {
        super();
        // Bind the handler once to ensure we can remove it later
        this._boundHandleKeyUp = this._handleKeyUp.bind(this);
    }

    /**
     * Public method to toggle modal visibility
     * Called by parent component to open/close the modal
     */
    @api
    toggleModal() {
        this._isOpen = !this._isOpen;

        if (this._isOpen) {
            this._onOpen();
        } else {
            this._onClose();
        }
    }

    /**
     * Public method to explicitly open the modal
     */
    @api
    open() {
        if (!this._isOpen) {
            this._isOpen = true;
            this._onOpen();
        }
    }

    /**
     * Public method to explicitly close the modal
     */
    @api
    close() {
        if (this._isOpen) {
            this._isOpen = false;
            this._onClose();
        }
    }

    // Computed properties for template
    get isOpen() {
        return this._isOpen;
    }

    get modalAriaHidden() {
        return String(!this._isOpen);
    }

    get modalContainerClass() {
        const sizeClass = this.size === 'large' ? 'slds-modal_large' :
                          this.size === 'small' ? 'slds-modal_small' : '';
        return this._isOpen
            ? `slds-modal slds-fade-in-open ${sizeClass}`
            : 'slds-modal slds-hidden';
    }

    get backdropClass() {
        return this._isOpen
            ? 'slds-backdrop slds-backdrop_open'
            : 'slds-backdrop';
    }

    get showHeader() {
        return this.modalHeader || this.modalTagline;
    }

    // Lifecycle hooks
    disconnectedCallback() {
        // Clean up window event listener to prevent memory leaks
        window.removeEventListener('keyup', this._boundHandleKeyUp);
    }

    // Private methods
    _onOpen() {
        // Collect all focusable elements within the modal
        // Elements must have the 'focusable' class
        this._focusableElements = [
            ...this.querySelectorAll('.focusable'),
            ...this.template.querySelectorAll(
                'lightning-button, lightning-button-icon, lightning-input, button, [tabindex="0"]'
            )
        ].filter(el => !el.disabled);

        // Focus the first focusable element
        this._focusFirstElement();

        // Add window-level keyboard listener for ESC and Tab
        window.addEventListener('keyup', this._boundHandleKeyUp);

        // Dispatch open event
        this.dispatchEvent(new CustomEvent('modalopen'));
    }

    _onClose() {
        // Remove keyboard listener
        window.removeEventListener('keyup', this._boundHandleKeyUp);

        // Dispatch close event
        this.dispatchEvent(new CustomEvent('modalclose'));
    }

    _handleKeyUp(event) {
        if (event.code === ESCAPE_KEY || event.key === ESCAPE_KEY) {
            this.close();
        } else if (event.code === TAB_KEY || event.key === TAB_KEY) {
            this._handleTabNavigation(event);
        }
    }

    _handleTabNavigation(event) {
        // Implement focus trap - keep focus within modal
        if (this._focusableElements.length === 0) return;

        const activeElement = this.template.activeElement || document.activeElement;
        const lastIndex = this._focusableElements.length - 1;
        const currentIndex = this._focusableElements.indexOf(activeElement);

        if (event.shiftKey && currentIndex <= 0) {
            // Shift+Tab on first element - wrap to last
            event.preventDefault();
            this._focusableElements[lastIndex]?.focus();
        } else if (!event.shiftKey && currentIndex >= lastIndex) {
            // Tab on last element - wrap to first
            event.preventDefault();
            this._focusFirstElement();
        }
    }

    _focusFirstElement() {
        // Small delay to ensure modal is fully rendered
        // eslint-disable-next-line @lwc/lwc/no-async-operation
        setTimeout(() => {
            if (this._focusableElements.length > 0) {
                this._focusableElements[0].focus();
            }
        }, 0);
    }

    // Event handlers
    handleBackdropClick(event) {
        // Close modal if clicking on the backdrop (outside modal content)
        if (event.target.classList.contains(OUTER_MODAL_CLASS)) {
            this.close();
        }
    }

    handleCancel() {
        this.close();
    }

    handleSave() {
        // If a save handler was provided, call it
        if (typeof this.modalSaveHandler === 'function') {
            this.modalSaveHandler();
        }

        // Dispatch save event for parent components
        this.dispatchEvent(new CustomEvent('modalsave'));

        // Close the modal
        this.close();
    }
}
