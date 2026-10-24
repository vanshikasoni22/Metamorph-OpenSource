/**
 * Contrib — Beginner Mode Controller (beginner.js)
 * Connected to Contrib backend API.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Stepper Elements
  const stepBtn1 = document.getElementById('step-btn-1');
  const stepBtn2 = document.getElementById('step-btn-2');
  const stepBtn3 = document.getElementById('step-btn-3');

  // Views
  const viewStep1 = document.getElementById('view-step-1');
  const viewStep2 = document.getElementById('view-step-2');
  const viewStep3 = document.getElementById('view-step-3');

  // Controls
  const formConnect = document.getElementById('form-connect-github');
  const btnAnalyze = document.getElementById('btn-analyze-github');
  const btnBackStep1 = document.getElementById('btn-back-to-step1');
  const btnBackStep2 = document.getElementById('btn-back-to-step2');
  const ghUsernameInput = document.getElementById('gh-username-input');
  const btnToggleSaved = document.getElementById('btn-toggle-saved');
  const savedCountSpan = document.getElementById('saved-count');

  // Results containers
  const issuesContainer = document.querySelector('.issues-cards-stack');
  const planTitle = document.getElementById('plan-title');
  const checklistBox = document.querySelector('.checklist-group');
  const checklistCounter = document.getElementById('checklist-counter');
  const codebaseRefList = document.querySelector('.plan-card-right .reads-list');

  let currentBeginnerData = null;
  let selectedIssue = null;
  let savedIssuesList = [];
  let isViewingSaved = false;

  async function loadSavedIssues() {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const username = ghUsernameInput ? ghUsernameInput.value.trim() : 'octocat';
      const res = await fetch(`${apiUrl}/beginner/saved?username=${encodeURIComponent(username)}`);
      if (!res.ok) return;
      const data = await res.json();
      savedIssuesList = data.saved_issues || [];
      if (savedCountSpan) savedCountSpan.textContent = savedIssuesList.length;
    } catch (e) {
      console.warn('Could not load saved issues:', e);
    }
  }

  loadSavedIssues();

  function setStep(stepNum) {
    viewStep1.style.display = 'none';
    viewStep2.style.display = 'none';
    viewStep3.style.display = 'none';

    [stepBtn1, stepBtn2, stepBtn3].forEach(btn => {
      btn.className = 'stepper-pill next';
      btn.querySelector('.pill-meta').textContent = 'Next';
    });

    if (stepNum === 1) {
      viewStep1.style.display = 'block';
      stepBtn1.className = 'stepper-pill current';
      stepBtn1.querySelector('.pill-meta').textContent = 'Current';
    } else if (stepNum === 2) {
      viewStep2.style.display = 'block';
      stepBtn1.className = 'stepper-pill completed';
      stepBtn1.querySelector('.pill-meta').textContent = 'Done';
      stepBtn2.className = 'stepper-pill current';
      stepBtn2.querySelector('.pill-meta').textContent = 'Current';
    } else if (stepNum === 3) {
      viewStep3.style.display = 'block';
      stepBtn1.className = 'stepper-pill completed';
      stepBtn1.querySelector('.pill-meta').textContent = 'Done';
      stepBtn2.className = 'stepper-pill completed';
      stepBtn2.querySelector('.pill-meta').textContent = 'Done';
      stepBtn3.className = 'stepper-pill current';
      stepBtn3.querySelector('.pill-meta').textContent = 'Current';
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderMatchedIssues(issues, isSavedView = false) {
    if (!issuesContainer) return;

    if (!issues || issues.length === 0) {
      issuesContainer.innerHTML = `
        <div style="padding: 32px; text-align: center; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px;">
          <h3 style="color: #0f172a; margin-bottom: 8px;">${isSavedView ? 'No Saved Issues Yet' : 'No issues found right now'}</h3>
          <p style="color: #64748b; font-size: 14px;">${isSavedView ? 'Bookmark issues to see them here.' : 'Try searching again in a moment.'}</p>
        </div>
      `;
      return;
    }

    let html = '';
    issues.forEach((item, idx) => {
      let pillsHtml = '';
      if (item.evidence_points) {
        item.evidence_points.forEach(pt => {
          pillsHtml += `<span class="ev-pill">${escapeHtml(pt)}</span>`;
        });
      }

      html += `
        <div class="issue-recommend-card" data-idx="${idx}">
          <div class="issue-header-row">
            <div class="issue-repo-meta">
              <span class="repo-badge">${escapeHtml(item.repo)}</span>
              <span class="issue-num">#${item.issue_number}</span>
              <span class="fit-pill">${item.fit_score || 90}% Fit Score</span>
            </div>
            <span class="time-est">${escapeHtml(item.estimated_hours || '2-4 hours est.')}</span>
          </div>
          <h3 class="issue-name">${escapeHtml(item.title)}</h3>
          <p class="issue-desc">${escapeHtml(item.description || '')}</p>
          <div class="evidence-pills-row">
            ${pillsHtml}
          </div>
          <div class="issue-card-actions" style="display: flex; gap: 10px; align-items: center;">
            <button class="btn btn-black btn-select-issue" data-idx="${idx}">
              Select this issue & get plan →
            </button>
            ${!isSavedView ? `<button class="btn btn-outline btn-save-issue" data-idx="${idx}">★ Save</button>` : ''}
          </div>
        </div>
      `;
    });

    issuesContainer.innerHTML = html;

    // Attach select issue handlers
    document.querySelectorAll('.btn-select-issue').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        selectedIssue = issues[idx];
        populatePlan(selectedIssue);
        setStep(3);
      });
    });

    // Attach save issue handlers
    document.querySelectorAll('.btn-save-issue').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        const iss = issues[idx];
        btn.textContent = 'Saving...';
        try {
          const apiUrl = window.CONTRIB_API_URL || '';
          const username = ghUsernameInput ? ghUsernameInput.value.trim() : 'octocat';
          const res = await fetch(`${apiUrl}/beginner/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ issue: iss, username })
          });
          if (res.ok) {
            btn.textContent = '✓ Saved';
            btn.disabled = true;
            await loadSavedIssues();
          } else {
            btn.textContent = 'Failed';
          }
        } catch (err) {
          btn.textContent = 'Error';
        }
      });
    });
  }

  // Toggle Saved Issues View
  if (btnToggleSaved) {
    btnToggleSaved.addEventListener('click', async () => {
      isViewingSaved = !isViewingSaved;
      if (isViewingSaved) {
        btnToggleSaved.textContent = '← Show Recommendations';
        await loadSavedIssues();
        renderMatchedIssues(savedIssuesList, true);
      } else {
        btnToggleSaved.innerHTML = `★ Saved Issues (<span id="saved-count">${savedIssuesList.length}</span>)`;
        if (currentBeginnerData && currentBeginnerData.recommended_issues) {
          renderMatchedIssues(currentBeginnerData.recommended_issues, false);
        }
      }
    });
  }

  function populatePlan(issue) {
    if (!issue) return;

    if (planTitle) {
      planTitle.textContent = issue.title;
    }
    const repoBadge = document.querySelector('.plan-banner .repo-badge');
    if (repoBadge) {
      repoBadge.textContent = `${issue.repo} #${issue.issue_number}`;
    }

    // Populate checklist
    if (checklistBox && issue.implementation_steps) {
      let cbHtml = '';
      issue.implementation_steps.forEach(step => {
        cbHtml += `
          <label class="check-row">
            <input type="checkbox" class="plan-cb">
            <span>${escapeHtml(step)}</span>
          </label>
        `;
      });
      checklistBox.innerHTML = cbHtml;

      // Re-attach counter listeners
      const checkboxes = checklistBox.querySelectorAll('.plan-cb');
      function updateChecklist() {
        let count = 0;
        checkboxes.forEach(cb => { if (cb.checked) count++; });
        if (checklistCounter) {
          checklistCounter.textContent = `${count} of ${checkboxes.length} completed`;
        }
      }
      checkboxes.forEach(cb => cb.addEventListener('change', updateChecklist));
      updateChecklist();
    }

    // Populate codebase references
    if (codebaseRefList && issue.codebase_references) {
      let refHtml = '';
      issue.codebase_references.forEach(ref => {
        refHtml += `
          <li class="reads-item">
            <span class="code-pill">${escapeHtml(ref.type)}</span>
            <span class="reads-desc"><code>${escapeHtml(ref.reference)}</code></span>
          </li>
        `;
      });
      codebaseRefList.innerHTML = refHtml;
    }
  }

  // Submit Step 1 -> Call Backend -> Step 2
  if (formConnect) {
    formConnect.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = ghUsernameInput ? ghUsernameInput.value.trim() : 'octocat';

      btnAnalyze.innerHTML = 'Analyzing...';
      btnAnalyze.disabled = true;

      try {
        const apiUrl = window.CONTRIB_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/beginner/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username })
        });

        if (!res.ok) {
          throw new Error(`API error (${res.status})`);
        }

        currentBeginnerData = await res.json();
        renderMatchedIssues(currentBeginnerData.recommended_issues);
        setStep(2);
      } catch (err) {
        console.error('[Contrib] Beginner analysis error:', err);
        alert(`Failed to analyze profile: ${err.message}`);
      } finally {
        btnAnalyze.innerHTML = 'Analyze my GitHub <span class="arrow">→</span>';
        btnAnalyze.disabled = false;
      }
    });
  }

  // Back Buttons
  if (btnBackStep1) btnBackStep1.addEventListener('click', () => setStep(1));
  if (btnBackStep2) btnBackStep2.addEventListener('click', () => setStep(2));

  // Direct Stepper Click
  stepBtn1.addEventListener('click', () => setStep(1));
  stepBtn2.addEventListener('click', () => { if (currentBeginnerData) setStep(2); });
  stepBtn3.addEventListener('click', () => { if (selectedIssue) setStep(3); });
});
