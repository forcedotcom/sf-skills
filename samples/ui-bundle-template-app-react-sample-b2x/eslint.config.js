/**
 * ESLint 9 flat config for LWC and Aura.
 * @see https://github.com/salesforce/eslint-config-lwc
 */
const lwcConfig = require("@salesforce/eslint-config-lwc");

module.exports = [...lwcConfig.configs.recommended];
