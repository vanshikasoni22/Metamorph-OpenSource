/**
 * Contrib — Global Runtime Configuration
 * 
 * Configures the backend API URL dynamically. Can be overridden via:
 * 1. window.__ENV.CONTRIB_API_URL
 * 2. <meta name="contrib-api-url" content="..."> in the HTML head
 * 3. localStorage.getItem("CONTRIB_API_URL")
 * 4. Default: "https://metamorph-opensource-2.onrender.com"
 */

(function () {
  const metaTag = document.querySelector('meta[name="contrib-api-url"]');
  const metaUrl = metaTag ? metaTag.getAttribute('content') : null;

  // Smart default:
  // 1. On localhost / local dev: use http://127.0.0.1:8000
  // 2. On Render backend (when served by FastAPI): use window.location.origin
  // 3. On Vercel or any other frontend host: use live Render backend URL
  let defaultApiUrl = 'https://metamorph-opensource-2.onrender.com';
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname || '';
    if (host === 'localhost' || host === '127.0.0.1') {
      defaultApiUrl = 'http://127.0.0.1:8000';
    } else if (host.includes('onrender.com')) {
      defaultApiUrl = window.location.origin;
    } else {
      defaultApiUrl = 'https://metamorph-opensource-2.onrender.com';
    }
  }

  window.CONTRIB_API_URL =
    window.CONTRIB_API_URL ||
    (window.__ENV && window.__ENV.CONTRIB_API_URL) ||
    metaUrl ||
    localStorage.getItem('CONTRIB_API_URL') ||
    defaultApiUrl;

  console.log('[Contrib Config] Active API URL:', window.CONTRIB_API_URL);
})();
