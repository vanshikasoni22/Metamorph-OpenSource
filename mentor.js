/**
 * Contrib — Maintainer Mode Controller (mentor.js)
 * Matching the exact Paste links layout and 3-step pill stepper workflow.
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

  const analysisProgress = document.getElementById('analysis-progress');
  const tick1 = document.getElementById('tick-1');
  const tick2 = document.getElementById('tick-2');
  const tick3 = document.getElementById('tick-3');
  const tick4 = document.getElementById('tick-4');

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

  // Use Sample Links
  const sampleLinks = [
    'https://github.com/example-org/httpkit/pull/231',
    'https://github.com/example-org/httpkit/pull/229',
    'https://github.com/example-org/httpkit/pull/236',
    'https://github.com/example-org/httpkit/pull/225'
  ];

  if (btnSampleLinks) {
    btnSampleLinks.addEventListener('click', () => {
      issueUrlInput.value = 'https://github.com/example-org/httpkit/issues/1042';
      prUrlInputs.forEach((input, idx) => {
        if (sampleLinks[idx]) {
          input.value = sampleLinks[idx];
        }
      });
      btnSampleLinks.textContent = '✓ Sample Links Applied';
      setTimeout(() => {
        btnSampleLinks.textContent = 'Use sample links';
      }, 1500);
    });
  }

  // Submit Step 1 -> Step 2 -> Step 3
  if (formPasteLinks) {
    formPasteLinks.addEventListener('submit', (e) => {
      e.preventDefault();
      setStep(2);

      // Ticker animation
      if (analysisProgress) analysisProgress.style.width = '25%';

      setTimeout(() => {
        if (tick3) {
          tick3.className = 'ticker-item completed';
          tick3.textContent = '✓ Validated author claims against actual lines of code';
        }
        if (tick4) {
          tick4.className = 'ticker-item in-progress';
          tick4.textContent = '⚙ Ranking candidate PRs and surfacing blockers...';
        }
        if (analysisProgress) analysisProgress.style.width = '75%';
      }, 700);

      setTimeout(() => {
        if (tick4) {
          tick4.className = 'ticker-item completed';
          tick4.textContent = '✓ Scoring completed: Top 4 candidate PRs ranked';
        }
        if (analysisProgress) analysisProgress.style.width = '100%';
        setStep(3);
      }, 1400);
    });
  }

  // Back Button
  if (btnBackToInput) {
    btnBackToInput.addEventListener('click', () => setStep(1));
  }

  // Direct Stepper Click
  stepBtn1.addEventListener('click', () => setStep(1));
  stepBtn2.addEventListener('click', () => setStep(2));
  stepBtn3.addEventListener('click', () => setStep(3));

  // PR Card selection
  document.querySelectorAll('.pr-result-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.pr-result-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
    });
  });

  // Copy Markdown Review
  document.querySelectorAll('.export-markdown-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const markdown = `## Contrib Evidence Review\n- Rank #1: PR #231 (Score: 92/100)\n- Verified: Adds tests for retry path (tests/test_sender.py:42-71)\n- Blocker: check_run/lint is failing.\n*Human maintainer review required before merge.*`;
      navigator.clipboard.writeText(markdown).then(() => {
        const originalText = btn.textContent;
        btn.textContent = '✓ Copied Markdown!';
        setTimeout(() => {
          btn.textContent = originalText;
        }, 2000);
      });
    });
  });

  // Diff Inspector scroll
  document.querySelectorAll('.view-inspector-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const diffSection = document.getElementById('diff-section');
      if (diffSection) {
        diffSection.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
});
