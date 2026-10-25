/**
 * build-frontend.js
 * Bundles pure static HTML, CSS, and JS into dist/ for Vercel CDN hosting.
 * Completely isolates frontend from backend to guarantee 0 serverless functions.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist');

const API_URL = process.env.CONTRIB_API_URL || 'https://metamorph-opensource-2.onrender.com';
const META_TAG = `<meta name="contrib-api-url" content="${API_URL}">`;

// Clean & recreate dist
if (fs.existsSync(DIST)) {
  fs.rmSync(DIST, { recursive: true, force: true });
}
fs.mkdirSync(DIST, { recursive: true });

// Copy & patch HTML files
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

  fs.writeFileSync(path.join(DIST, file), content, 'utf8');
  console.log(`  ✓ HTML: ${file}`);
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
    console.log(`  ✓ Asset: ${entry.name}`);
  }
}

console.log(`\nFrontend build complete. Dist ready at ${DIST}`);
