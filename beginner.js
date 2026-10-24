/**
 * Contrib — Beginner Mode Controller (beginner.js)
 * Matching the exact 3-step pill stepper workflow.
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
  const planTitle = document.getElementById('plan-title');

  // Checklist
  const checkboxes = document.querySelectorAll('.plan-cb');
  const checklistCounter = document.getElementById('checklist-counter');

  function setStep(stepNum) {
    // Hide all
    viewStep1.style.display = 'none';
    viewStep2.style.display = 'none';
    viewStep3.style.display = 'none';

    // Update Pills
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

  // Submit Step 1 -> Step 2
  if (formConnect) {
    formConnect.addEventListener('submit', (e) => {
      e.preventDefault();
      btnAnalyze.innerHTML = 'Analyzing...';
      btnAnalyze.disabled = true;

      setTimeout(() => {
        btnAnalyze.innerHTML = 'Analyze my GitHub <span class="arrow">→</span>';
        btnAnalyze.disabled = false;
        setStep(2);
      }, 500);
    });
  }

  // Back Buttons
  if (btnBackStep1) btnBackStep1.addEventListener('click', () => setStep(1));
  if (btnBackStep2) btnBackStep2.addEventListener('click', () => setStep(2));

  // Direct Stepper Click
  stepBtn1.addEventListener('click', () => setStep(1));
  stepBtn2.addEventListener('click', () => setStep(2));
  stepBtn3.addEventListener('click', () => setStep(3));

  // Select Issue -> Step 3
  document.querySelectorAll('.btn-select-issue').forEach(btn => {
    btn.addEventListener('click', () => {
      const card = btn.closest('.issue-recommend-card');
      const issueName = card.querySelector('.issue-name')?.textContent || '';
      if (planTitle) planTitle.textContent = issueName;
      setStep(3);
    });
  });

  // Checklist counter
  function updateChecklist() {
    let count = 0;
    checkboxes.forEach(cb => {
      if (cb.checked) count++;
    });
    if (checklistCounter) {
      checklistCounter.textContent = `${count} of ${checkboxes.length} completed`;
    }
  }

  checkboxes.forEach(cb => {
    cb.addEventListener('change', updateChecklist);
  });
});
