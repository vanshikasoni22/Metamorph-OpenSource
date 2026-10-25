/**
 * inject-api-url.js
 * Vercel build step: injects <meta name="contrib-api-url"> into every HTML
 * file so config.js picks up the Render backend URL at runtime.
 *
 * Set the CONTRIB_API_URL env var in Vercel dashboard (e.g. https://contribo.onrender.com)
 */

const fs = require('fs');
const path = require('path');
const glob = require('fs');

const API_URL = process.env.CONTRIB_API_URL || 'https://contribo.onrender.com';
const META_TAG = `<meta name="contrib-api-url" content="${API_URL}">`;

const ROOT = path.resolve(__dirname, '..');
const htmlFiles = fs.readdirSync(ROOT).filter(f => f.endsWith('.html'));

let patched = 0;
for (const file of htmlFiles) {
  const filePath = path.join(ROOT, file);
  let content = fs.readFileSync(filePath, 'utf8');

  // Remove any existing contrib-api-url meta tag to avoid duplicates
  content = content.replace(/<meta name="contrib-api-url"[^>]*>/g, '');

  // Inject before closing </head>
  if (content.includes('</head>')) {
    content = content.replace('</head>', `  ${META_TAG}\n</head>`);
    fs.writeFileSync(filePath, content, 'utf8');
    patched++;
    console.log(`  ✓ Patched ${file} → ${API_URL}`);
  } else {
    console.warn(`  ⚠ No </head> found in ${file}, skipping`);
  }
}

console.log(`\nDone. Injected CONTRIB_API_URL="${API_URL}" into ${patched} HTML file(s).`);
