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

  window.CONTRIB_API_URL =
    window.CONTRIB_API_URL ||
    (window.__ENV && window.__ENV.CONTRIB_API_URL) ||
    metaUrl ||
    localStorage.getItem('CONTRIB_API_URL') ||
    'http://localhost:8000';

  console.log(`[Contrib] API URL initialized: ${window.CONTRIB_API_URL}`);
})();
