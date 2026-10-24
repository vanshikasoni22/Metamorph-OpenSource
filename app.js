/**
 * Contrib — Interactive UI Controller
 * Handles user interactions, preview modals, verdict inspections, and setup for
 * upcoming Beginner and Maintainer workflows.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const beginnerCard = document.getElementById('beginner-card');
  const maintainerCard = document.getElementById('maintainer-card');
  const startBeginnerBtn = document.getElementById('start-beginner-btn');
  const startMaintainerBtn = document.getElementById('start-maintainer-btn');
  
  const modal = document.getElementById('flow-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalDismissBtn = document.getElementById('modal-dismiss-btn');
  const modalActionBtn = document.getElementById('modal-action-btn');
  const modalModeBadge = document.getElementById('modal-mode-badge');
  const modalBodyContent = document.getElementById('modal-body-content');

  const toast = document.getElementById('toast-notify');
  const toastTitle = document.getElementById('toast-title');
  const toastMessage = document.getElementById('toast-message');

  let toastTimeout = null;

  // Show Toast Helper
  function showToast(title, message) {
    if (toastTimeout) {
      clearTimeout(toastTimeout);
    }
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    toast.classList.add('is-visible');

    toastTimeout = setTimeout(() => {
      toast.classList.remove('is-visible');
    }, 3800);
  }

  // Open Modal Helper
  function openModal(mode) {
    if (mode === 'beginner') {
      modalModeBadge.textContent = 'Beginner Flow · Ready for Configuration';
      modalModeBadge.style.backgroundColor = '#ecfdf5';
      modalModeBadge.style.color = '#065f46';
      modalBodyContent.innerHTML = `
        <h3 style="font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
          Find your first open-source issue
        </h3>
        <p style="color: #64748b; font-size: 13.5px; margin-bottom: 20px;">
          Contrib matches you with issues backed by evidence: clear reproduction steps, small diff scope, and active maintainers.
        </p>
        <div class="modal-form-group">
          <label class="modal-label" for="gh-username">GitHub Username</label>
          <input type="text" id="gh-username" class="modal-input" placeholder="e.g. torvalds or octocat" value="" />
          <p class="modal-hint">We'll inspect public repos, languages and commit frequency.</p>
        </div>
        <div class="modal-form-group">
          <label class="modal-label" for="target-topics">Preferred Languages / Tags</label>
          <input type="text" id="target-topics" class="modal-input" placeholder="e.g. Python, TypeScript, Rust" />
        </div>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 14px; font-size: 12.5px; color: #475569;">
          <strong>Next step ready:</strong> We'll build the complete interactive question flow and recommendations dashboard next!
        </div>
      `;
      modalActionBtn.textContent = 'Launch Beginner Setup';
    } else if (mode === 'maintainer') {
      modalModeBadge.textContent = 'Maintainer Flow · Ready for Configuration';
      modalModeBadge.style.backgroundColor = '#f1f5f9';
      modalModeBadge.style.color = '#0f172a';
      modalBodyContent.innerHTML = `
        <h3 style="font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px;">
          Verify Pull Requests with Evidence
        </h3>
        <p style="color: #64748b; font-size: 13.5px; margin-bottom: 20px;">
          Compare multiple pull requests solving the same issue. Check claims directly against diffs, test coverage, and CI checks.
        </p>
        <div class="modal-form-group">
          <label class="modal-label" for="issue-url">GitHub Issue URL</label>
          <input type="url" id="issue-url" class="modal-input" placeholder="https://github.com/org/repo/issues/123" />
        </div>
        <div class="modal-form-group">
          <label class="modal-label" for="pr-urls">Pull Request URLs (one or more)</label>
          <input type="text" id="pr-urls" class="modal-input" placeholder="https://github.com/org/repo/pull/214, #215" />
          <p class="modal-hint">Contrib extracts claims, checks diffs & surfaces blockers.</p>
        </div>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 14px; font-size: 12.5px; color: #475569;">
          <strong>Next step ready:</strong> We'll build the PR verification workbench and evidence scoring rules next!
        </div>
      `;
      modalActionBtn.textContent = 'Launch Maintainer Setup';
    }

    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
  }

  // Event Listeners for Cards and Action Links
  if (beginnerCard) {
    beginnerCard.addEventListener('click', (e) => {
      window.location.href = 'beginner.html';
    });
  }

  if (startBeginnerBtn) {
    startBeginnerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      window.location.href = 'beginner.html';
    });
  }

  if (maintainerCard) {
    maintainerCard.addEventListener('click', (e) => {
      window.location.href = 'mentor.html';
    });
  }

  if (startMaintainerBtn) {
    startMaintainerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      window.location.href = 'mentor.html';
    });
  }

  // Modal close handlers
  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
  if (modalDismissBtn) modalDismissBtn.addEventListener('click', closeModal);
  
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('is-open')) {
      closeModal();
    }
  });

  if (modalActionBtn) {
    modalActionBtn.addEventListener('click', () => {
      showToast('Step Saved', 'Configured settings saved. Ready for detailed questions!');
      closeModal();
    });
  }

  // Sample Verdict interactive item clicks
  const verdictItems = document.querySelectorAll('.verdict-item');
  verdictItems.forEach((item) => {
    item.addEventListener('click', () => {
      const status = item.getAttribute('data-status');
      const claim = item.querySelector('.claim-text')?.textContent || '';
      const ref = item.querySelector('.evidence-ref')?.textContent || '';

      if (status === 'supported') {
        showToast('Evidence Verified ✓', `${ref}`);
      } else if (status === 'unknown') {
        showToast('Evidence Unknown ?', 'Flagged for human maintainer review');
      } else if (status === 'blocker') {
        showToast('Hard Blocker ✕', `${ref}`);
      }
    });
  });

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId && targetId !== '#' && !targetId.includes('flow')) {
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
          e.preventDefault();
          targetElement.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });
});
