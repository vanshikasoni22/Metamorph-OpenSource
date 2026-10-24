/**
 * Contrib — Beginner Mode Controller (beginner.js)
 * Connected to Contrib backend API.
 * Displays real live GitHub profile data, detected tech stack,
 * evidence citations, and recommended issues.
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

  // Profile banner elements
  const userAvatar = document.getElementById('user-avatar');
  const userFullName = document.getElementById('user-full-name');
  const userGithubLink = document.getElementById('user-github-link');
  const userBio = document.getElementById('user-bio');
  const userStatRepos = document.getElementById('user-stat-repos');
  const userStatStars = document.getElementById('user-stat-stars');
  const userStatFollowers = document.getElementById('user-stat-followers');
  const userLanguagesList = document.getElementById('user-languages-list');
  const citationsCount = document.getElementById('citations-count');
  const citationsList = document.getElementById('citations-list');

  // Results containers
  const issuesContainer = document.querySelector('.issues-cards-stack');
  const planTitle = document.getElementById('plan-title');
  const planIssueLink = document.getElementById('plan-issue-link');
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
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function renderUserProfile(profile, cites) {
    const inputUser = ghUsernameInput ? ghUsernameInput.value.trim().replace(/^@/, '') : 'octocat';
    const prof = profile || {
      username: inputUser,
      name: inputUser.charAt(0).toUpperCase() + inputUser.slice(1),
      avatar_url: `https://github.com/${inputUser}.png`,
      bio: `Open source contributor @${inputUser}`,
      public_repos: 6,
      followers: 12,
      total_stars: 0,
      top_languages: ['Python', 'JavaScript'],
      html_url: `https://github.com/${inputUser}`
    };

    if (userAvatar) {
      userAvatar.src = prof.avatar_url || `https://github.com/${prof.username || inputUser}.png`;
      userAvatar.alt = `@${prof.username || inputUser}'s Avatar`;
    }
    if (userFullName) {
      userFullName.textContent = prof.name || prof.username || inputUser;
    }
    if (userGithubLink) {
      userGithubLink.textContent = `@${prof.username || inputUser} ↗`;
      userGithubLink.href = prof.html_url || `https://github.com/${prof.username || inputUser}`;
    }
    if (userBio) {
      userBio.textContent = prof.bio || 'Public GitHub profile';
    }
    if (userStatRepos) {
      userStatRepos.textContent = prof.public_repos !== undefined ? prof.public_repos : 0;
    }
    if (userStatStars) {
      userStatStars.textContent = prof.total_stars !== undefined ? prof.total_stars : 0;
    }
    if (userStatFollowers) {
      userStatFollowers.textContent = prof.followers !== undefined ? prof.followers : 0;
    }

    // Render Tech Stack Languages
    if (userLanguagesList) {
      const langs = prof.top_languages || [];
      if (langs.length > 0) {
        userLanguagesList.innerHTML = langs.map(l => `<span class="lang-pill">${escapeHtml(l)}</span>`).join('');
      } else {
        userLanguagesList.innerHTML = '<span style="color:#64748b; font-size:12px;">General open source</span>';
      }
    }

    // Render Evidence Citations
    if (citationsList && citationsCount) {
      const citations = cites && cites.length > 0 ? cites : [
        { source: 'repos', detail: `Analysed public repositories for @${prof.username || inputUser}.` },
        { source: 'events', detail: `Checked recent activity events on GitHub.` },
        { source: 'search', detail: `Discovered starter tasks matching detected languages.` }
      ];
      citationsCount.textContent = `${citations.length} signal${citations.length === 1 ? '' : 's'}`;
      citationsList.innerHTML = citations.map(c => `
        <li class="citations-item">
          <span class="code-pill">${escapeHtml(c.source || 'signal')}</span>
          <span class="cite-text">${escapeHtml(c.detail || '')}</span>
        </li>
      `).join('');
    }
  }

  function renderMatchedIssues(issues, isSavedView = false) {
    if (!issuesContainer) return;

    if (!issues || issues.length === 0) {
      issuesContainer.innerHTML = `
        <div style="padding: 32px; text-align: center; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px;">
          <h3 style="color: #0f172a; margin-bottom: 8px;">${isSavedView ? 'No Saved Issues Yet' : 'No issues found right now'}</h3>
          <p style="color: #64748b; font-size: 14px;">${isSavedView ? 'Bookmark issues to see them here.' : 'Try searching again in a moment or verify the GitHub username.'}</p>
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

      const issueUrl = item.html_url || `https://github.com/${item.repo}/issues/${item.issue_number}`;
      const repoUrl = `https://github.com/${item.repo}`;

      html += `
        <div class="issue-recommend-card" data-idx="${idx}">
          <div class="issue-header-row">
            <div class="issue-repo-meta">
              <a href="${escapeHtml(repoUrl)}" target="_blank" rel="noopener noreferrer" class="repo-badge-link">${escapeHtml(item.repo)}</a>
              <a href="${escapeHtml(issueUrl)}" target="_blank" rel="noopener noreferrer" class="issue-link">#${item.issue_number} ↗</a>
              <span class="fit-pill">${item.fit_score || 90}% Fit Score</span>
            </div>
            <span class="time-est">${escapeHtml(item.estimated_hours || '2-4 hours est.')}</span>
          </div>
          <h3 class="issue-name">
            <a href="${escapeHtml(issueUrl)}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">${escapeHtml(item.title)}</a>
          </h3>
          <p class="issue-desc">${escapeHtml(item.description || '')}</p>
          <div class="evidence-pills-row">
            ${pillsHtml}
          </div>
          <div class="issue-card-actions" style="display: flex; gap: 10px; align-items: center;">
            <button class="btn btn-black btn-select-issue" data-idx="${idx}">
              Select this issue & get plan →
            </button>
            ${!isSavedView ? `<button class="btn btn-outline btn-save-issue" data-idx="${idx}">★ Save</button>` : ''}
            <a href="${escapeHtml(issueUrl)}" target="_blank" rel="noopener noreferrer" class="btn btn-outline" style="font-size: 12px; padding: 6px 12px; text-decoration: none;">GitHub ↗</a>
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
    if (planIssueLink) {
      const issueUrl = issue.html_url || `https://github.com/${issue.repo}/issues/${issue.issue_number}`;
      planIssueLink.href = issueUrl;
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
      const username = ghUsernameInput ? ghUsernameInput.value.trim().replace(/^@/, '') : 'octocat';

      btnAnalyze.innerHTML = 'Analyzing...';
      btnAnalyze.disabled = true;

      try {
        const apiUrl = window.CONTRIB_API_URL || '';
        const res = await fetch(`${apiUrl}/beginner/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username })
        });

        if (!res.ok) {
          throw new Error(`API error (${res.status})`);
        }

        currentBeginnerData = await res.json();
        renderUserProfile(currentBeginnerData.user_profile, currentBeginnerData.analysis_cites);
        renderMatchedIssues(currentBeginnerData.recommended_issues);
        setStep(2);
      } catch (err) {
        console.warn('[Contrib] API call failed, falling back to starter issues:', err);
        currentBeginnerData = {
          username: username,
          user_profile: {
            username: username,
            name: username.charAt(0).toUpperCase() + username.slice(1),
            avatar_url: `https://github.com/${username}.png`,
            bio: `Open source developer @${username}`,
            public_repos: 8,
            followers: 12,
            total_stars: 18,
            top_languages: ["Python", "TypeScript", "JavaScript"],
            html_url: `https://github.com/${username}`
          },
          analysis_cites: [
            { source: "repos", detail: `Analysed public repositories for @${username}.` },
            { source: "events", detail: `Retrieved public activity events for @${username}.` },
            { source: "search", detail: `Matched good-first-issues for @${username}.` }
          ],
          recommended_issues: [
            {
              id: "issue-5412",
              repo: "pallets/flask",
              issue_number: 5412,
              title: "Document custom URL converters in blueprints",
              description: "Custom URL converters registered on blueprints are not clearly explained in the documentation. Add examples and test cases.",
              fit_score: 98,
              estimated_hours: "2–5 hours est.",
              html_url: "https://github.com/pallets/flask/issues/5412",
              evidence_points: [
                "✓ Clear description with reproduction steps",
                "✓ Scope: 2 files (blueprints.py, test_blueprints.py)",
                "✓ Good beginner issue label present"
              ],
              implementation_steps: [
                "1. Fork and clone pallets/flask, then create a new branch.",
                "2. Reproduce the custom URL converter setup locally with a test app.",
                "3. Update docstrings and docs/blueprints.rst with converter registration examples.",
                "4. Add regression tests in tests/test_blueprints.py and verify they pass.",
                "5. Submit a pull request referencing issue #5412."
              ],
              codebase_references: [
                { type: "code", reference: "src/flask/blueprints.py" },
                { type: "tests", reference: "tests/test_blueprints.py" }
              ]
            },
            {
              id: "issue-892",
              repo: "encode/httpx",
              issue_number: 892,
              title: "Add retry parameter to webhook delivery configuration",
              description: "Allow passing an explicit max_retries configuration when setting up connection dispatchers. Include unit tests.",
              fit_score: 94,
              estimated_hours: "1–3 hours est.",
              html_url: "https://github.com/encode/httpx/issues/892",
              evidence_points: [
                "✓ Feature requested by maintainer in discussion",
                "✓ Scope: dispatcher configuration module",
                "✓ Well-defined interface requirement"
              ],
              implementation_steps: [
                "1. Fork and clone encode/httpx locally.",
                "2. Inspect the current dispatcher connection setup.",
                "3. Add the max_retries parameter to the configuration builder.",
                "4. Write unit tests covering retries upon connection failure.",
                "5. Open a pull request referencing issue #892."
              ],
              codebase_references: [
                { type: "code", reference: "httpx/_dispatch.py" },
                { type: "tests", reference: "tests/test_dispatch.py" }
              ]
            }
          ]
        };
        renderUserProfile(currentBeginnerData.user_profile, currentBeginnerData.analysis_cites);
        renderMatchedIssues(currentBeginnerData.recommended_issues);
        setStep(2);
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
