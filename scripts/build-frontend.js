/**
 * build-frontend.js
 * Builds static frontend into dist/ for clean, function-free Vercel deployment.
 * Also injects <meta name="contrib-api-url"> into HTML files pointing to the Render backend.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist');

const API_URL = process.env.CONTRIB_API_URL || 'https://contribo.onrender.com';
const META_TAG = `<meta name="contrib-api-url" content="${API_URL}">`;

// Ensure clean dist/
if (fs.existsSync(DIST)) {
  fs.rmSync(DIST, { recursive: true, force: true });
}
fs.mkdirSync(DIST, { recursive: true });

// Copy and patch HTML files
const htmlFiles = ['index.html', 'beginner.html', 'mentor.html'];
for (const file of htmlFiles) {
  const src = path.join(ROOT, file);
  if (!fs.existsSync(src)) continue;
  let content = fs.readFileSync(src, 'utf8');

  // Strip duplicate meta tags
  content = content.replace(/<meta name="contrib-api-url"[^>]*>/g, '');

  if (content.includes('</head>')) {
    content = content.replace('</head>', `  ${META_TAG}\n</head>`);
  }

  // Write to both ROOT (for local dev) and DIST (for Vercel)
  fs.writeFileSync(src, content, 'utf8');
  fs.writeFileSync(path.join(DIST, file), content, 'utf8');
  console.log(`  ✓ HTML: ${file} (API: ${API_URL})`);
}

// Copy static assets (.css, .js, .svg, .png, etc.)
const staticExtensions = ['.css', '.js', '.svg', '.png', '.jpg', '.ico'];
const rootEntries = fs.readdirSync(ROOT, { withFileTypes: true });

for (const entry of rootEntries) {
  if (!entry.isFile()) continue;
  const ext = path.extname(entry.name);
  if (staticExtensions.includes(ext) && !htmlFiles.includes(entry.name)) {
    const src = path.join(ROOT, entry.name);
    const dest = path.join(DIST, entry.name);
    fs.copyFileSync(src, dest);
    console.log(`  ✓ Static: ${entry.name}`);
  }
}

console.log(`\nFrontend build complete. Dist ready at ${DIST}`);
