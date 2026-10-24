/**
 * Contrib — Global Runtime Configuration
 * 
 * Configures the backend API URL dynamically. Can be overridden via:
 * 1. window.__ENV.CONTRIB_API_URL
 * 2. <meta name="contrib-api-url" content="..."> in the HTML head
 * 3. localStorage.getItem("CONTRIB_API_URL")
 * 4. Default: "http://localhost:8000"
 */

(function () {
  const metaTag = document.querySelector('meta[name="contrib-api-url"]');
  const metaUrl = metaTag ? metaTag.getAttribute('content') : null;

  // Smart default:
  // 1. When hosted on the web (Render, custom domain) or unified localhost:8000, use window.location.origin
  // 2. When running on an independent frontend dev server (e.g. Live Server on port 5500), use http://localhost:8000
  // 3. When opened via file://, use http://localhost:8000
  let defaultApiUrl = 'http://localhost:8000';
  if (typeof window !== 'undefined' && window.location && window.location.protocol.startsWith('http')) {
    const isSeparateDevPort = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') &&
                              window.location.port &&
                              window.location.port !== '8000';
    if (!isSeparateDevPort) {
      defaultApiUrl = window.location.origin;
    }
  }

  window.CONTRIB_API_URL =
    window.CONTRIB_API_URL ||
    (window.__ENV && window.__ENV.CONTRIB_API_URL) ||
    metaUrl ||
    localStorage.getItem('CONTRIB_API_URL') ||
    defaultApiUrl;

  console.log(`[Contrib] API URL initialized: ${window.CONTRIB_API_URL}`);
})();
