#!/usr/bin/env node
/**
 * Intelligent vendor file detection for Code Analyzer results
 * Uses multiple heuristics to classify files as vendor vs project code
 *
 * Usage: node filter-violations.js <input.json> <output.json> [--report]
 */

const fs = require('fs');
const path = require('path');

class VendorDetector {
  constructor(projectRoot) {
    this.projectRoot = projectRoot;
    this.packageNames = this.loadPackageNames();
    this.fileContentCache = new Map();
  }

  /**
   * Load known third-party package names from package.json
   */
  loadPackageNames() {
    const names = new Set();
    const packageJsonPath = path.join(this.projectRoot, 'package.json');

    if (fs.existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
        Object.keys(pkg.dependencies || {}).forEach(d => names.add(d.toLowerCase()));
        Object.keys(pkg.devDependencies || {}).forEach(d => names.add(d.toLowerCase()));
      } catch (err) {
        // Ignore parsing errors
      }
    }

    return names;
  }

  /**
   * Main classification method - returns classification with confidence score
   */
  classifyFile(filePath) {
    const scores = {
      pathBased: this.scoreByPath(filePath),
      nameBased: this.scoreByName(filePath),
      contentBased: this.scoreByContent(filePath),
    };

    // Weighted average (content analysis is more reliable when available)
    const weights = {
      pathBased: 0.3,
      nameBased: 0.3,
      contentBased: 0.4,
    };

    const weightedScore = Object.entries(scores).reduce(
      (sum, [key, score]) => sum + score * weights[key],
      0
    );

    const reasons = this.explainScores(scores, filePath);

    return {
      isVendor: weightedScore > 50,
      confidence: weightedScore,
      scores,
      reasons,
      classification: this.getClassificationLabel(weightedScore),
    };
  }

  /**
   * Score based on directory/path patterns (0-100)
   */
  scoreByPath(filePath) {
    let score = 0;
    const normalizedPath = filePath.toLowerCase();

    // Absolute vendor indicators
    if (/node_modules/.test(normalizedPath)) return 100;
    if (/bower_components/.test(normalizedPath)) return 100;
    if (/vendor\//.test(normalizedPath)) return 95;
    if (/third[_-]party/.test(normalizedPath)) return 95;

    // Common vendor directory names
    if (/\/lib\//i.test(normalizedPath)) score += 60;
    if (/StaticResourceSources/i.test(normalizedPath)) score += 70;
    if (/CumulusStaticResources/i.test(normalizedPath)) score += 70;

    // Salesforce-specific: project source is typically in aura/ or lwc/
    if (/force-app\/main\/default\/(aura|lwc)\/[^/]+\//.test(filePath)) {
      // In an Aura or LWC component directory - likely project code
      return Math.min(score, 20); // Cap score at 20 for project paths
    }

    // Outside of component directories but in staticresources
    if (/staticresources/.test(normalizedPath)) score += 50;

    return Math.min(score, 100);
  }

  /**
   * Score based on filename patterns (0-100)
   */
  scoreByName(filePath) {
    let score = 0;
    const basename = path.basename(filePath).toLowerCase();

    // Minified files are almost always vendor code
    if (/\.min\.js$/.test(basename)) return 95;
    if (/\.bundle\.js$/.test(basename)) score += 80;
    if (/-min\.js$/.test(basename)) return 95;

    // Version numbers in filename (e.g., jquery-1.12.1.js)
    if (/-\d+\.\d+(\.\d+)?\.js$/.test(basename)) score += 85;
    if (/\d+\.\d+\.\d+/.test(basename)) score += 70;

    // Known library name patterns
    const knownLibs = [
      'jquery', 'lodash', 'underscore', 'moment', 'angular', 'react', 'vue',
      'bootstrap', 'foundation', 'handlebars', 'backbone', 'ember', 'knockout',
      'typeahead', 'select2', 'datatables', 'chart', 'arbor', 'd3', 'raphael',
      'leaflet', 'mapbox', 'three', 'pixi', 'phaser', 'babylonjs',
    ];

    for (const lib of knownLibs) {
      if (new RegExp(`\\b${lib}\\b`, 'i').test(basename)) {
        score += 85;
        break;
      }
    }

    // Check against package.json dependencies
    for (const pkgName of this.packageNames) {
      if (basename.includes(pkgName)) {
        score += 80;
        break;
      }
    }

    return Math.min(score, 100);
  }

  /**
   * Score based on file content analysis (0-100)
   */
  scoreByContent(filePath) {
    try {
      const absolutePath = path.isAbsolute(filePath)
        ? filePath
        : path.join(this.projectRoot, filePath);

      if (!fs.existsSync(absolutePath)) {
        return 0; // Can't score if file doesn't exist
      }

      const content = fs.readFileSync(absolutePath, 'utf8');
      let score = 0;

      // Check first 2000 characters for header information
      const header = content.slice(0, 2000);

      // License headers strongly indicate vendor code
      if (/\b(MIT License|Apache License|BSD License|GPL|ISC License|Mozilla Public License)\b/i.test(header)) {
        score += 80;
      }
      if (/@license\b/i.test(header)) score += 75;

      // Copyright notices (but not from the current org)
      if (/@copyright\b(?!.*salesforce\.com)/i.test(header)) score += 60;

      // Version stamps
      if (/@version\s+\d+\.\d+\.\d+/.test(header)) score += 65;
      if (/\bv\d+\.\d+\.\d+\b/.test(header)) score += 55;

      // Author field that's not project-specific
      if (/@author\b/i.test(header) && !/salesforce/i.test(header)) score += 50;

      // Check for minification indicators
      const lines = content.split('\n');
      const avgLineLength = content.length / lines.length;

      if (avgLineLength > 500) score += 90; // Extremely long lines = minified
      if (avgLineLength > 200) score += 70;
      if (lines.length < 10 && content.length > 5000) score += 85; // Very dense

      // UMD/AMD/CommonJS wrapper patterns (common in libraries)
      if (/\(function\s*\([^)]*\)\s*\{[\s\S]{0,200}(typeof\s+define|typeof\s+module|typeof\s+exports)/.test(header)) {
        score += 70;
      }

      // IIFE wrapping entire file (very common in libraries)
      const trimmed = content.trim();
      if (/^\(function\s*\(/.test(trimmed) && /\}\s*\)\s*\([^)]*\)\s*;?\s*$/.test(trimmed)) {
        score += 60;
      }

      // Banner comments with project URLs
      if (/\bhttps?:\/\/(github\.com|npmjs\.com|unpkg\.com|cdnjs\.com)/i.test(header)) {
        score += 75;
      }

      return Math.min(score, 100);
    } catch (err) {
      // If we can't read the file, don't penalize it
      return 0;
    }
  }

  /**
   * Generate human-readable reasons for the classification
   */
  explainScores(scores, filePath) {
    const reasons = [];
    const basename = path.basename(filePath);

    if (scores.pathBased > 70) {
      reasons.push('located in vendor directory');
    }
    if (scores.nameBased > 70) {
      if (/\.min\.js$/.test(basename)) {
        reasons.push('minified file (.min.js)');
      } else if (/\d+\.\d+\.\d+/.test(basename)) {
        reasons.push('version number in filename');
      } else {
        reasons.push('matches known library name');
      }
    }
    if (scores.contentBased > 70) {
      reasons.push('contains vendor markers (license, version, minification)');
    }

    if (reasons.length === 0) {
      if (scores.pathBased < 30 && scores.nameBased < 30) {
        reasons.push('appears to be project source code');
      } else {
        reasons.push('unclear classification');
      }
    }

    return reasons;
  }

  /**
   * Get classification label based on confidence score
   */
  getClassificationLabel(score) {
    if (score > 70) return 'vendor';
    if (score < 30) return 'project';
    return 'uncertain';
  }
}

/**
 * Filter violations from Code Analyzer results
 */
function filterViolations(inputFile, outputFile, options = {}) {
  const results = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
  const projectRoot = results.runDir || process.cwd();

  const detector = new VendorDetector(projectRoot);

  // Group violations by file
  const fileViolations = {};
  for (const v of results.violations) {
    const file = v.locations[v.primaryLocationIndex].file;
    if (!fileViolations[file]) {
      fileViolations[file] = {
        violations: [],
        classification: null,
      };
    }
    fileViolations[file].violations.push(v);
  }

  // Classify each file
  const analysis = {
    vendor: [],
    project: [],
    uncertain: [],
  };

  for (const [file, data] of Object.entries(fileViolations)) {
    const classification = detector.classifyFile(file);
    data.classification = classification;

    const entry = {
      file,
      violationCount: data.violations.length,
      ...classification,
    };

    if (classification.classification === 'vendor') {
      analysis.vendor.push(entry);
    } else if (classification.classification === 'project') {
      analysis.project.push(entry);
    } else {
      analysis.uncertain.push(entry);
    }
  }

  // Filter violations to project files only
  const projectFiles = new Set(analysis.project.map(e => e.file));
  const filteredViolations = results.violations.filter(v => {
    const file = v.locations[v.primaryLocationIndex].file;
    return projectFiles.has(file);
  });

  // Recalculate severity counts
  const severityCounts = { sev1: 0, sev2: 0, sev3: 0, sev4: 0, sev5: 0 };
  for (const v of filteredViolations) {
    const sev = `sev${v.severity}`;
    if (severityCounts[sev] !== undefined) {
      severityCounts[sev]++;
    }
  }

  // Create filtered results
  const filteredResults = {
    ...results,
    violations: filteredViolations,
    violationCounts: {
      total: filteredViolations.length,
      ...severityCounts,
    },
    filterMetadata: {
      filteredAt: new Date().toISOString(),
      originalViolations: results.violations.length,
      filteredViolations: filteredViolations.length,
      vendorFilesExcluded: analysis.vendor.length,
      projectFilesIncluded: analysis.project.length,
      uncertainFiles: analysis.uncertain.length,
    },
  };

  fs.writeFileSync(outputFile, JSON.stringify(filteredResults, null, 2));

  // Print summary
  printSummary(results, filteredResults, analysis, options);

  return filteredResults;
}

/**
 * Print detailed summary report
 */
function printSummary(original, filtered, analysis, options) {
  console.log('\n=== INTELLIGENT VENDOR FILE DETECTION ===\n');
  console.log(`Original violations: ${original.violations.length}`);
  console.log(`Filtered violations: ${filtered.violations.length}`);
  console.log(`Reduction: ${original.violations.length - filtered.violations.length} (${((1 - filtered.violations.length / original.violations.length) * 100).toFixed(1)}%)\n`);

  console.log(`📦 Vendor files excluded: ${analysis.vendor.length}`);
  if (analysis.vendor.length > 0 && options.report) {
    const top = analysis.vendor.sort((a, b) => b.violationCount - a.violationCount).slice(0, 10);
    top.forEach(e => {
      console.log(`   ${e.violationCount.toString().padStart(4)} violations | ${e.confidence.toFixed(0)}% confidence | ${e.file}`);
      console.log(`        ${e.reasons.join(', ')}`);
    });
    if (analysis.vendor.length > 10) {
      console.log(`   ... and ${analysis.vendor.length - 10} more vendor files`);
    }
  }

  console.log(`\n✅ Project files included: ${analysis.project.length}`);
  if (analysis.project.length > 0 && options.report) {
    const top = analysis.project.sort((a, b) => b.violationCount - a.violationCount).slice(0, 10);
    top.forEach(e => {
      console.log(`   ${e.violationCount.toString().padStart(4)} violations | ${e.file}`);
    });
  }

  if (analysis.uncertain.length > 0) {
    console.log(`\n⚠️  Uncertain files: ${analysis.uncertain.length}`);
    console.log('    These files have 30-70% vendor confidence - review manually:');
    analysis.uncertain.forEach(e => {
      console.log(`   ${e.violationCount.toString().padStart(4)} violations | ${e.confidence.toFixed(0)}% vendor | ${e.file}`);
      console.log(`        ${e.reasons.join(', ')}`);
    });
  }

  console.log(`\n✓ Filtered results written to: ${outputFile}`);
}

// CLI
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('Usage: node filter-violations.js <input.json> <output.json> [--report]');
  console.error('');
  console.error('Options:');
  console.error('  --report    Show detailed file-by-file analysis');
  process.exit(1);
}

const [inputFile, outputFile] = args;
const options = {
  report: args.includes('--report'),
};

try {
  filterViolations(inputFile, outputFile, options);
} catch (err) {
  console.error('Error:', err.message);
  process.exit(1);
}
