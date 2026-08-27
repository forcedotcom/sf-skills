// ESLint flat config for the Komaci offline static analyzer.
// Applies the recommended ruleset from
// @salesforce/eslint-plugin-lwc-graph-analyzer with the bundleAnalyzer
// processor wired in via the recommended config.
import lwcGraphAnalyzerPlugin from '@salesforce/eslint-plugin-lwc-graph-analyzer';

const PLUGIN_NAME = '@salesforce/lwc-graph-analyzer';
const RECOMMENDED = lwcGraphAnalyzerPlugin.configs.recommended;

export default [
  {
    name: `config: ${PLUGIN_NAME}`,
    plugins: {
      [PLUGIN_NAME]: lwcGraphAnalyzerPlugin,
    },
    ...RECOMMENDED,
  },
];
