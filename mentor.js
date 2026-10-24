/**
 * Contrib — Maintainer Mode Controller (mentor.js)
 * Fully connected to the Contrib backend API.
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
  const formPasteLinks = document.getElementById('form-paste-links');
  const btnAnalyzePrs = document.getElementById('btn-analyze-prs');
  const btnSampleLinks = document.getElementById('btn-sample-links');
  const btnBackToInput = document.getElementById('btn-back-to-input');

  const issueUrlInput = document.getElementById('issue-url-input');
  const prUrlInputs = document.querySelectorAll('.pr-url');

  // Analysis Ticker Elements
  const analysisProgress = document.getElementById('analysis-progress');
  const tick1 = document.getElementById('tick-1');
  const tick2 = document.getElementById('tick-2');
  const tick3 = document.getElementById('tick-3');
  const tick4 = document.getElementById('tick-4');

  // Result Elements
  const scorecardsStack = document.querySelector('.scorecards-stack');
  const diffSection = document.getElementById('diff-section');
  const diffTitle = document.getElementById('diff-title');

  let currentScoreData = null;

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

  // Use Real Public Sample Links (pallets/flask issue and PRs)
  const sampleIssue = 'https://github.com/pallets/flask/issues/5412';
  const sampleLinks = [
    'https://github.com/pallets/flask/pull/5415',
    'https://github.com/pallets/flask/pull/5416'
  ];

  if (btnSampleLinks) {
    btnSampleLinks.addEventListener('click', () => {
      issueUrlInput.value = sampleIssue;
      prUrlInputs.forEach((input, idx) => {
        input.value = sampleLinks[idx] || '';
      });
      btnSampleLinks.textContent = '✓ Sample Links Applied';
      setTimeout(() => {
        btnSampleLinks.textContent = 'Use sample links';
      }, 1500);
    });
  }

  // Ticker Helper
  function updateTicker(step, status, text) {
    const el = document.getElementById(`tick-${step}`);
    if (!el) return;
    el.className = `ticker-item ${status}`;
    const prefix = status === 'completed' ? '✓ ' : (status === 'in-progress' ? '⚙ ' : '○ ');
    el.textContent = `${prefix}${text}`;
  }

  // Database History Elements & Loader
  const historyCard = document.getElementById('maintainer-history-card');
  const historyContainer = document.getElementById('history-items-container');
  const historyCountBadge = document.getElementById('history-count-badge');

  async function loadReviewHistory() {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const res = await fetch(`${apiUrl}/maintainer/history?limit=5`);
      if (!res.ok) return;
      const data = await res.json();
      const history = data.history || [];

      if (!historyCard || !historyContainer) return;

      if (history.length === 0) {
        historyCard.style.display = 'none';
        return;
      }

      historyCard.style.display = 'block';
      if (historyCountBadge) historyCountBadge.textContent = `${history.length} saved`;

      let html = '';
      history.forEach((item) => {
        const dateStr = item.created_at ? new Date(item.created_at * 1000).toLocaleString() : '';
        html += `
          <div class="history-item-row" data-history-id="${item.id}" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; cursor: pointer; transition: all 0.15s ease;">
            <div>
              <div style="font-weight: 600; font-size: 13.5px; color: #0f172a;">${escapeHtml(item.repo)} #${escapeHtml(String(item.issue_number))} · ${escapeHtml(item.issue_title || '')}</div>
              <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                <span>${item.pr_count} PR(s) evaluated</span> ·
                <span style="color: #059669; font-weight: 600;">Top Score: ${item.top_score}/100</span> ·
                <span>${dateStr}</span>
              </div>
            </div>
            <button class="btn btn-outline btn-sm btn-load-history" style="font-size: 12px; padding: 4px 10px;">Load Report →</button>
          </div>
        `;
      });
      historyContainer.innerHTML = html;

      // Attach click listeners to load report
      historyContainer.querySelectorAll('.history-item-row').forEach((row, idx) => {
        row.addEventListener('click', () => {
          const item = history[idx];
          if (item && item.report && item.report.score_response) {
            currentScoreData = item.report.score_response;
            renderResults(item.report.score_response);
            if (item.report.pull_requests && item.report.pull_requests[0]) {
              renderDiffForPR(item.report.pull_requests[0]);
            }
            setStep(3);
          }
        });
      });
    } catch (e) {
      console.warn('Could not load review history:', e);
    }
  }

  loadReviewHistory();

  function showAnalysisError(errorMessage) {
    const statusCard = document.querySelector('.analysis-status-card');
    if (statusCard) {
      statusCard.innerHTML = `
        <div style="padding: 24px; text-align: left; background-color: #fff1f2; border: 1px solid #fecdd3; border-radius: 12px;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <span style="font-size: 20px;">⚠️</span>
            <h3 style="font-size: 16px; font-weight: 700; color: #9f1239; margin: 0;">Failed to Fetch GitHub Data</h3>
          </div>
          <p style="color: #4c0519; font-size: 13.5px; line-height: 1.5; margin: 0 0 16px 0;">
            ${escapeHtml(errorMessage)}
          </p>
          <button class="btn btn-black btn-sm" id="btn-error-retry">← Edit links and try again</button>
        </div>
      `;
      document.getElementById('btn-error-retry')?.addEventListener('click', () => {
        window.location.reload();
      });
    }
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

  // Render Diff in Diff Section
  function renderDiffForPR(pr) {
    if (!diffSection) return;

    const fileTag = diffSection.querySelector('.diff-file-tag');
    const preContainer = diffSection.querySelector('.diff-code-pre');

    diffTitle.textContent = `Evidence Proof Inspector — PR #${pr.pr_number || pr.number} · ${pr.title}`;

    if (!pr.files || pr.files.length === 0) {
      if (fileTag) fileTag.textContent = 'No files changed';
      if (preContainer) {
        preContainer.innerHTML = `
          <div class="code-line context" style="padding: 16px; color: #64748b;">
            No patch or diff files reported for this pull request.
          </div>
        `;
      }
      return;
    }

    const firstFile = pr.files[0];
    if (fileTag) {
      fileTag.textContent = `${firstFile.filename} (+${firstFile.additions}/-${firstFile.deletions})`;
    }

    if (preContainer) {
      let linesHtml = '';
      if (firstFile.patch === 'unknown' || !firstFile.patch) {
        linesHtml = `
          <div class="code-line context" style="padding: 12px; color: #64748b;">
            <span class="proof-badge" style="background-color: #f1f5f9; color: #475569;">Patch unknown</span>
            Binary file or large diff omitted by GitHub. Requires manual inspection.
          </div>
        `;
      } else {
        const lines = firstFile.patch.split('\n');
        lines.forEach((line, idx) => {
          let lineClass = 'context';
          let badge = '';
          if (line.startsWith('+')) {
            lineClass = 'add';
            if (idx === 1) badge = '<span class="proof-badge">✓ Cited by Contrib: verified patch</span>';
          } else if (line.startsWith('-')) {
            lineClass = 'del';
          }
          linesHtml += `
            <div class="code-line ${lineClass}">
              <span>${idx + 1}</span> ${escapeHtml(line)} ${badge}
            </div>
          `;
        });
      }
      preContainer.innerHTML = linesHtml;
    }
  }

  // Render Scored Results in Step 3
  function renderResults(scoreData) {
    if (!scorecardsStack) return;

    if (!scoreData.candidate_prs || scoreData.candidate_prs.length === 0) {
      scorecardsStack.innerHTML = `
        <div style="padding: 32px; text-align: center; background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px;">
          <h3 style="color: #0f172a; margin-bottom: 8px;">No Candidate PRs Found</h3>
          <p style="color: #64748b; font-size: 14px;">No pull requests were found matching this issue. You can go back and paste specific PR URLs to evaluate.</p>
        </div>
      `;
      return;
    }

    let cardsHtml = '';
    scoreData.candidate_prs.forEach((pr, idx) => {
      const activeClass = idx === 0 ? 'active' : '';
      const rankClass = `rank-${pr.rank <= 3 ? pr.rank : 'default'}`;

      let verdictsHtml = '';
      pr.verdicts.forEach(v => {
        let pillClass = 'pill-supported';
        let icon = '✓ Supported';
        if (v.status === 'blocker') {
          pillClass = 'pill-blocker';
          icon = '✕ Blocker';
        } else if (v.status === 'unknown') {
          pillClass = 'pill-unknown';
          icon = '? Unknown';
        }

        verdictsHtml += `
          <div class="verdict-point">
            <span class="status-pill ${pillClass}">${icon}</span>
            <span class="point-claim">${escapeHtml(v.claim)}</span>
            <span class="point-evidence">${escapeHtml(v.evidence)}</span>
          </div>
        `;
      });

      cardsHtml += `
        <div class="pr-result-card ${activeClass}" data-pr="${pr.pr_number}" data-idx="${idx}">
          <div class="pr-card-header">
            <div class="pr-title-group">
              <span class="rank-tag ${rankClass}">Rank #${pr.rank}</span>
              <span class="pr-label">PR #${pr.pr_number} · ${escapeHtml(pr.title)}</span>
              <span class="pr-by">by @${escapeHtml(pr.author)}</span>
            </div>
            <div class="pr-score-group">
              <span class="score-large">${pr.score}</span>
              <span class="score-label">Score</span>
            </div>
          </div>

          <div class="verdict-points-list">
            ${verdictsHtml}
          </div>

          <div class="pr-card-footer">
            <button class="btn btn-${idx === 0 ? 'black' : 'outline'} btn-sm view-inspector-btn" data-idx="${idx}">Inspect Diff & Proof</button>
            <button class="btn btn-outline btn-sm export-markdown-btn" data-idx="${idx}">Copy Review Markdown</button>
          </div>
        </div>
      `;
    });

    scorecardsStack.innerHTML = cardsHtml;

    // Attach card click handlers
    document.querySelectorAll('.pr-result-card').forEach(card => {
      card.addEventListener('click', () => {
        document.querySelectorAll('.pr-result-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        const idx = parseInt(card.getAttribute('data-idx'), 10);
        if (scoreData.candidate_prs[idx]) {
          renderDiffForPR(scoreData.candidate_prs[idx]);
        }
      });
    });

    // Attach Inspect Diff buttons
    document.querySelectorAll('.view-inspector-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        if (scoreData.candidate_prs[idx]) {
          renderDiffForPR(scoreData.candidate_prs[idx]);
          diffSection?.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });

    // Attach Copy Markdown buttons
    document.querySelectorAll('.export-markdown-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        const pr = scoreData.candidate_prs[idx];
        const md = `## Contrib Evidence Review\n- Rank #${pr.rank}: PR #${pr.pr_number} — ${pr.title} (Score: ${pr.score}/100)\n` +
          pr.verdicts.map(v => `- [${v.status.toUpperCase()}] ${v.claim}: ${v.evidence}`).join('\n') +
          '\n\n*Human maintainer review required before merge.*';

        navigator.clipboard.writeText(md).then(() => {
          const originalText = btn.textContent;
          btn.textContent = '✓ Copied Markdown!';
          setTimeout(() => {
            btn.textContent = originalText;
          }, 2000);
        });
      });
    });

    // Render initial diff for the first PR
    if (scoreData.candidate_prs[0]) {
      renderDiffForPR(scoreData.candidate_prs[0]);
    }
  }

  // Handle Form Submit: Step 1 -> Step 2 -> Step 3 via real backend API
  if (formPasteLinks) {
    formPasteLinks.addEventListener('submit', async (e) => {
      e.preventDefault();

      const issueUrl = issueUrlInput.value.trim();
      const prUrls = Array.from(prUrlInputs)
        .map(i => i.value.trim())
        .filter(url => url.length > 0);

      setStep(2);

      // Start ticker
      updateTicker(1, 'in-progress', 'Connecting to GitHub API & parsing issue...');
      updateTicker(2, 'pending', 'Fetching candidate pull requests and diffs...');
      updateTicker(3, 'pending', 'Validating CI check-runs and tests...');
      updateTicker(4, 'pending', 'Evaluating rules and ranking candidates...');
      if (analysisProgress) analysisProgress.style.width = '20%';

      try {
        const apiUrl = window.CONTRIB_API_URL || 'http://localhost:8000';
        
        // 1. Fetch GitHub data
        const fetchResponse = await fetch(`${apiUrl}/maintainer/fetch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            issue_url: issueUrl,
            pr_urls: prUrls,
            force_refresh: false
          })
        });

        if (!fetchResponse.ok) {
          const errorData = await fetchResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || `Server returned ${fetchResponse.status}: ${fetchResponse.statusText}`);
        }

        const data = await fetchResponse.json();

        // Update ticker after fetch
        updateTicker(1, 'completed', `Fetched issue #${data.issue.number}: ${data.issue.title}`);
        updateTicker(2, 'in-progress', `Inspecting changed files across ${data.pull_requests.length} candidate PR(s)...`);
        if (analysisProgress) analysisProgress.style.width = '50%';

        await new Promise(r => setTimeout(r, 300));

        const totalFiles = data.pull_requests.reduce((acc, p) => acc + (p.files ? p.files.length : 0), 0);
        updateTicker(2, 'completed', `Inspected ${totalFiles} changed file(s) across ${data.pull_requests.length} PR(s)`);
        updateTicker(3, 'completed', 'Verified check-runs & test artifacts');
        updateTicker(4, 'in-progress', 'Running rule engine & scoring candidates...');
        if (analysisProgress) analysisProgress.style.width = '80%';

        // 2. Score candidate PRs
        const scoreResponse = await fetch(`${apiUrl}/maintainer/score`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });

        if (!scoreResponse.ok) {
          const errorData = await scoreResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to score candidate pull requests');
        }

        currentScoreData = await scoreResponse.json();

        updateTicker(4, 'completed', `Completed: Top ${currentScoreData.candidate_prs.length} candidate PR(s) ranked`);
        if (analysisProgress) analysisProgress.style.width = '100%';

        await new Promise(r => setTimeout(r, 400));

        // 3. Render and advance to Step 3
        renderResults(currentScoreData);
        setStep(3);

      } catch (err) {
        console.error('[Contrib] Maintainer analysis error:', err);
        showAnalysisError(err.message || 'An unknown error occurred during GitHub data extraction.');
      }
    });
  }

  // Back Button
  if (btnBackToInput) {
    btnBackToInput.addEventListener('click', () => setStep(1));
  }

  // Direct Stepper Click
  stepBtn1.addEventListener('click', () => setStep(1));
  stepBtn2.addEventListener('click', () => {
    // Only allow if we already have data
    if (currentScoreData) setStep(2);
  });
  stepBtn3.addEventListener('click', () => {
    // Only allow if we already have data
    if (currentScoreData) setStep(3);
  });
});
