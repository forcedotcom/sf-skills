/**
 * NATIVE MODAL TEMPLATE (lightning/modal)
 *
 * Uses the platform's built-in modal service instead of a hand-rolled
 * backdrop/focus-trap implementation. LightningModal already provides:
 * - focus trap and initial focus
 * - ESC-to-close
 * - ARIA roles/labels
 * - size variants (small / medium / large / full)
 * - a promise-based result returned from open()
 *
 * Supported in Lightning Experience, the Salesforce app, and Experience
 * Builder sites (confirm current support for your specific site template
 * before relying on it as the only implementation).
 *
 * Replace: nativeModalComponent → yourModalName
 * Replace: NativeModalComponent → YourModalName
 *
 * ── How a parent opens this modal ──────────────────────────────────────
 * import YourModalName from 'c/yourModalName';
 *
 * async handleOpenModal() {
 *     const result = await YourModalName.open({
 *         size: 'small',                    // small | medium | large | full
 *         description: 'Accessible description of the modal purpose',
 *         label: 'Confirm Action',          // passed through as @api label
 *         content: 'Are you sure?'          // any custom @api input props
 *     });
 *
 *     if (result === 'save') {
 *         // user confirmed
 *     }
 * }
 * ────────────────────────────────────────────────────────────────────────
 */
import { api } from 'lwc';
import LightningModal from 'lightning/modal';

export default class NativeModalComponent extends LightningModal {
    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API (@api) - Passed in via YourModalName.open({ ... })
    // ═══════════════════════════════════════════════════════════════════════

    @api label;
    @api content;

    // ═══════════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════════

    handleCancel() {
        // Resolve the promise returned by open() with a falsy/known value
        this.close('cancel');
    }

    handleSave() {
        // Resolve the promise returned by open() with the result the
        // caller needs. Close is explicit, so validation can prevent it:
        // guard this call behind your own validity check before closing.
        this.close('save');
    }
}
