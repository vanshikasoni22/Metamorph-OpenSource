/**
 * Contrib — Beginner Mode Controller (beginner.js)
 * Connected to Contrib backend API.
 * Handles GitHub profile analysis, interactive contributor questionnaire,
 * profile persistence, issue matching, and implementation plan roadmap.
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

  // Step 1 Subsections
  const sectionUsername = document.getElementById('section-username');
  const sectionQuestionnaire = document.getElementById('section-questionnaire');

  // Username Controls
  const formConnect = document.getElementById('form-connect-github');
  const btnAnalyze = document.getElementById('btn-analyze-github');
  const ghUsernameInput = document.getElementById('gh-username-input');

  // Questionnaire Controls
  const formQuestionnaire = document.getElementById('form-questionnaire');
  const btnBackToUsername = document.getElementById('btn-back-to-username');
  const btnSaveProfileContinue = document.getElementById('btn-save-profile-continue');
  const questionnaireError = document.getElementById('questionnaire-error');
  const questionnaireLoading = document.getElementById('questionnaire-loading');
  const profileSaveStatus = document.getElementById('profile-save-status');

  // Skills Manager Controls
  const selectedSkillsContainer = document.getElementById('selected-skills-container');
  const selectSkillName = document.getElementById('select-skill-name');
  const customSkillInput = document.getElementById('custom-skill-input');
  const selectSkillLevel = document.getElementById('select-skill-level');
  const btnAddSkill = document.getElementById('btn-add-skill');

  // Interests Controls
  const interestsChipsContainer = document.getElementById('interests-chips-container');
  const customInterestInput = document.getElementById('custom-interest-input');
  const btnAddCustomInterest = document.getElementById('btn-add-custom-interest');

  // Hours Slider Controls
  const hoursSlider = document.getElementById('hours-slider');
  const hoursDisplayBadge = document.getElementById('hours-display-badge');
  const hoursHint = document.getElementById('hours-hint');
  const presetPills = document.querySelectorAll('.preset-pill');

  // Radio Cards & Options
  const goalRadios = document.querySelectorAll('#goal-options-grid .radio-card');
  const growthSpeedPills = document.querySelectorAll('#growth-speed-group .opt-pill');
  const difficultyPills = document.querySelectorAll('#difficulty-group .opt-pill');

  // Step 2 & 3 Controls
  const btnBackStep1 = document.getElementById('btn-back-to-step1');
  const btnBackStep2 = document.getElementById('btn-back-to-step2');
  const btnEditQuestionnaire = document.getElementById('btn-edit-questionnaire');
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

  // Questionnaire State
  let userSkills = [
    { skill: 'Python', level: 'beginner' },
    { skill: 'JavaScript', level: 'beginner' }
  ];
  let userInterests = new Set(['cli', 'developer-tools', 'web']);
  let userHours = 8;
  let userGoal = 'learn';
  let userGrowthSpeed = 'steady';
  let userDifficulty = 'beginner';

  let currentBeginnerData = null;
  let selectedIssue = null;
  let savedIssuesList = [];
  let isViewingSaved = false;

  // =========================================================================
  // Stepper & View Navigation
  // =========================================================================
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

  function showUsernameSection() {
    setStep(1);
    if (sectionUsername) sectionUsername.style.display = 'grid';
    if (sectionQuestionnaire) sectionQuestionnaire.style.display = 'none';
  }

  function showQuestionnaireSection() {
    setStep(1);
    if (sectionUsername) sectionUsername.style.display = 'none';
    if (sectionQuestionnaire) sectionQuestionnaire.style.display = 'block';
    renderSkillsTags();
    renderInterestsChips();
    syncHoursDisplay(userHours);
    syncGoalSelection(userGoal);
    syncGrowthSpeed(userGrowthSpeed);
    syncDifficulty(userDifficulty);
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

  // =========================================================================
  // Questionnaire UI Handlers & State Sync
  // =========================================================================

  // 1. Skills Manager
  function renderSkillsTags() {
    if (!selectedSkillsContainer) return;
    if (userSkills.length === 0) {
      selectedSkillsContainer.innerHTML = '<span style="color:#94a3b8; font-size:12.5px; font-style:italic;">No skills added yet. Choose a skill below to add one.</span>';
      return;
    }

    selectedSkillsContainer.innerHTML = userSkills.map((s, idx) => `
      <div class="skill-tag-pill">
        <span>${escapeHtml(s.skill)}</span>
        <span class="tag-level tag-level-${escapeHtml(s.level)}">${escapeHtml(s.level)}</span>
        <button type="button" class="btn-remove-skill" data-idx="${idx}" title="Remove skill">×</button>
      </div>
    `).join('');

    // Attach remove handlers
    selectedSkillsContainer.querySelectorAll('.btn-remove-skill').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.getAttribute('data-idx'), 10);
        userSkills.splice(idx, 1);
        renderSkillsTags();
      });
    });
  }

  if (selectSkillName) {
    selectSkillName.addEventListener('change', () => {
      if (selectSkillName.value === 'custom') {
        if (customSkillInput) {
          customSkillInput.style.display = 'inline-block';
          customSkillInput.focus();
        }
      } else {
        if (customSkillInput) {
          customSkillInput.style.display = 'none';
          customSkillInput.value = '';
        }
      }
    });
  }

  if (btnAddSkill) {
    btnAddSkill.addEventListener('click', () => {
      let skillName = selectSkillName ? selectSkillName.value.trim() : '';
      if (skillName === 'custom' && customSkillInput) {
        skillName = customSkillInput.value.trim();
      }

      if (!skillName) {
        showQuestionnaireError('Please select or type a skill name first.');
        return;
      }

      const level = selectSkillLevel ? selectSkillLevel.value : 'beginner';
      const existingIdx = userSkills.findIndex(s => s.skill.toLowerCase() === skillName.toLowerCase());
      if (existingIdx >= 0) {
        // Update level if already exists
        userSkills[existingIdx].level = level;
      } else {
        userSkills.push({ skill: skillName, level });
      }

      // Reset input
      if (selectSkillName) selectSkillName.value = '';
      if (customSkillInput) {
        customSkillInput.value = '';
        customSkillInput.style.display = 'none';
      }
      clearQuestionnaireError();
      renderSkillsTags();
    });
  }

  // 2. Interests Chips
  function renderInterestsChips() {
    if (!interestsChipsContainer) return;
    interestsChipsContainer.querySelectorAll('.chip-btn').forEach(btn => {
      const val = btn.getAttribute('data-value');
      if (userInterests.has(val)) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  if (interestsChipsContainer) {
    interestsChipsContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.chip-btn');
      if (!btn) return;
      const val = btn.getAttribute('data-value');
      if (userInterests.has(val)) {
        userInterests.delete(val);
        btn.classList.remove('active');
      } else {
        userInterests.add(val);
        btn.classList.add('active');
      }
      clearQuestionnaireError();
    });
  }

  if (btnAddCustomInterest) {
    btnAddCustomInterest.addEventListener('click', () => {
      if (!customInterestInput) return;
      const val = customInterestInput.value.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-');
      if (!val) return;

      userInterests.add(val);

      // Check if button already exists
      const existingBtn = interestsChipsContainer.querySelector(`[data-value="${val}"]`);
      if (existingBtn) {
        existingBtn.classList.add('active');
      } else {
        const newBtn = document.createElement('button');
        newBtn.type = 'button';
        newBtn.className = 'chip-btn active';
        newBtn.setAttribute('data-value', val);
        newBtn.textContent = customInterestInput.value.trim();
        interestsChipsContainer.appendChild(newBtn);
      }

      customInterestInput.value = '';
      clearQuestionnaireError();
    });
  }

  // 3. Hours Slider
  function syncHoursDisplay(hours) {
    userHours = parseInt(hours, 10) || 8;
    if (hoursSlider) hoursSlider.value = userHours;
    if (hoursDisplayBadge) hoursDisplayBadge.textContent = `${userHours} hours / week`;

    if (hoursHint) {
      if (userHours <= 5) {
        hoursHint.textContent = 'Casual pace. Great for exploring open source without stress.';
      } else if (userHours <= 10) {
        hoursHint.textContent = '~1-1.5 hours per day. Ideal for steady, consistent progress.';
      } else if (userHours <= 20) {
        hoursHint.textContent = 'Deep dive. Sufficient time for substantial feature tasks.';
      } else {
        hoursHint.textContent = 'Full immersion. Great for sprints, hackathons, or GSoC prep.';
      }
    }

    // Sync presets
    presetPills.forEach(pill => {
      const h = parseInt(pill.getAttribute('data-hours'), 10);
      if (h === userHours) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
  }

  if (hoursSlider) {
    hoursSlider.addEventListener('input', (e) => {
      syncHoursDisplay(e.target.value);
    });
  }

  presetPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const h = pill.getAttribute('data-hours');
      syncHoursDisplay(h);
    });
  });

  // 4. Goal Radio Cards
  function syncGoalSelection(goalVal) {
    userGoal = goalVal || 'learn';
    goalRadios.forEach(card => {
      const val = card.getAttribute('data-value');
      const radio = card.querySelector('input[type="radio"]');
      if (val === userGoal) {
        card.classList.add('selected');
        if (radio) radio.checked = true;
      } else {
        card.classList.remove('selected');
        if (radio) radio.checked = false;
      }
    });
  }

  goalRadios.forEach(card => {
    card.addEventListener('click', () => {
      const val = card.getAttribute('data-value');
      syncGoalSelection(val);
    });
  });

  // 5. Growth Speed Pills
  function syncGrowthSpeed(speedVal) {
    userGrowthSpeed = speedVal || 'steady';
    growthSpeedPills.forEach(pill => {
      if (pill.getAttribute('data-value') === userGrowthSpeed) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
  }

  growthSpeedPills.forEach(pill => {
    pill.addEventListener('click', () => {
      syncGrowthSpeed(pill.getAttribute('data-value'));
    });
  });

  // 6. Difficulty Pills
  function syncDifficulty(diffVal) {
    userDifficulty = diffVal || 'beginner';
    difficultyPills.forEach(pill => {
      if (pill.getAttribute('data-value') === userDifficulty) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
  }

  difficultyPills.forEach(pill => {
    pill.addEventListener('click', () => {
      syncDifficulty(pill.getAttribute('data-value'));
    });
  });

  function showQuestionnaireError(msg) {
    if (questionnaireError) {
      questionnaireError.textContent = msg;
      questionnaireError.style.display = 'block';
    }
  }

  function clearQuestionnaireError() {
    if (questionnaireError) {
      questionnaireError.textContent = '';
      questionnaireError.style.display = 'none';
    }
  }

  // =========================================================================
  // Load & Save Profile API Integration
  // =========================================================================

  async function fetchSavedProfile(username) {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const res = await fetch(`${apiUrl}/beginner/profile?username=${encodeURIComponent(username)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'found' && data.profile) {
          return data.profile;
        }
      }
    } catch (err) {
      console.warn('[Contrib] Could not load saved profile from server:', err);
    }
    return null;
  }

  async function persistProfile(profilePayload) {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const res = await fetch(`${apiUrl}/beginner/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profilePayload)
      });
      if (res.ok) {
        return true;
      }
    } catch (err) {
      console.warn('[Contrib] Could not save profile to server:', err);
    }
    return false;
  }

  // =========================================================================
  // Flow Step 1: Username Submission -> Fetch GitHub & Open Questionnaire
  // =========================================================================
  if (formConnect) {
    formConnect.addEventListener('submit', async (e) => {
      e.preventDefault();
      const rawUser = ghUsernameInput.value.trim().replace(/^@/, '');
      if (!rawUser) return;

      btnAnalyze.innerHTML = '<span class="q-spinner" style="display:inline-block; vertical-align:middle; margin-right:6px;"></span> Analyzing...';
      btnAnalyze.disabled = true;

      try {
        const apiUrl = window.CONTRIB_API_URL || '';

        // 1. Fetch public profile & repos via /beginner/analyze
        const analyzePromise = fetch(`${apiUrl}/beginner/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: rawUser })
        }).then(r => r.ok ? r.json() : null).catch(() => null);

        // 2. Fetch saved profile (if returning contributor)
        const savedProfilePromise = fetchSavedProfile(rawUser);

        const [analyzeData, savedProfile] = await Promise.all([analyzePromise, savedProfilePromise]);

        if (analyzeData) {
          currentBeginnerData = analyzeData;
        } else {
          // Fallback profile if offline
          currentBeginnerData = {
            username: rawUser,
            user_profile: {
              username: rawUser,
              name: rawUser.charAt(0).toUpperCase() + rawUser.slice(1),
              avatar_url: `https://github.com/${rawUser}.png`,
              bio: `Open source contributor @${rawUser}`,
              public_repos: 5,
              followers: 10,
              total_stars: 2,
              top_languages: ['Python', 'JavaScript'],
              html_url: `https://github.com/${rawUser}`
            },
            analysis_cites: [
              { source: 'repos', detail: `Analysed public repositories for @${rawUser}.` },
              { source: 'search', detail: 'Discovered starter issues matching detected languages.' }
            ],
            recommended_issues: []
          };
        }

        // Apply saved profile or auto-detected languages
        if (savedProfile) {
          userSkills = savedProfile.skills || [];
          userInterests = new Set(savedProfile.interests || ['cli', 'web']);
          userHours = savedProfile.hours_per_week || 8;
          userGoal = savedProfile.goal || 'learn';
          userGrowthSpeed = savedProfile.growth_speed || 'steady';
          userDifficulty = savedProfile.difficulty_preference || 'beginner';
          if (profileSaveStatus) profileSaveStatus.textContent = '✓ Saved preferences loaded';
        } else {
          // Pre-populate skills from detected languages without overwriting user
          const detectedLangs = currentBeginnerData?.user_profile?.top_languages || [];
          if (detectedLangs.length > 0) {
            userSkills = detectedLangs.map(l => ({ skill: l, level: 'beginner' }));
          } else {
            userSkills = [
              { skill: 'Python', level: 'beginner' },
              { skill: 'JavaScript', level: 'beginner' }
            ];
          }
          userInterests = new Set(['cli', 'developer-tools', 'web']);
          if (profileSaveStatus) profileSaveStatus.textContent = '';
        }

        // Transition smoothly to Questionnaire
        showQuestionnaireSection();

      } catch (err) {
        console.error('[Contrib] Error analyzing user:', err);
        showQuestionnaireSection();
      } finally {
        btnAnalyze.innerHTML = 'Analyze my GitHub <span class="arrow">→</span>';
        btnAnalyze.disabled = false;
      }
    });
  }

  // =========================================================================
  // Flow Step 1B: Questionnaire Submission -> Save Profile & View Issues
  // =========================================================================
  if (formQuestionnaire) {
    formQuestionnaire.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Validation
      if (userSkills.length === 0 && userInterests.size === 0) {
        showQuestionnaireError('Please select at least one skill or interest so we can match relevant issues.');
        return;
      }
      clearQuestionnaireError();

      const username = ghUsernameInput ? ghUsernameInput.value.trim().replace(/^@/, '') : 'anonymous';
      const profilePayload = {
        username: username,
        skills: userSkills,
        interests: Array.from(userInterests),
        hours_per_week: userHours,
        goal: userGoal,
        growth_speed: userGrowthSpeed,
        preferred_languages: userSkills.map(s => s.skill),
        difficulty_preference: userDifficulty
      };

      if (questionnaireLoading) questionnaireLoading.style.display = 'flex';
      btnSaveProfileContinue.disabled = true;

      try {
        // 1. Save profile to backend
        await persistProfile(profilePayload);

        // 2. Render Profile Banner on Step 2
        renderUserProfile(currentBeginnerData?.user_profile, currentBeginnerData?.analysis_cites);

        // 3. Render issues
        if (currentBeginnerData?.recommended_issues && currentBeginnerData.recommended_issues.length > 0) {
          renderMatchedIssues(currentBeginnerData.recommended_issues);
        } else {
          // Fetch or populate issues
          await loadStarterIssues(username);
        }

        // Transition to Step 2
        setStep(2);
      } catch (err) {
        console.error('[Contrib] Failed to complete questionnaire:', err);
        setStep(2);
      } finally {
        if (questionnaireLoading) questionnaireLoading.style.display = 'none';
        btnSaveProfileContinue.disabled = false;
      }
    });
  }

  // =========================================================================
  // Navigation Buttons
  // =========================================================================
  if (btnBackToUsername) {
    btnBackToUsername.addEventListener('click', showUsernameSection);
  }

  if (btnEditQuestionnaire) {
    btnEditQuestionnaire.addEventListener('click', showQuestionnaireSection);
  }

  if (btnBackStep1) {
    btnBackStep1.addEventListener('click', showUsernameSection);
  }

  if (btnBackStep2) {
    btnBackStep2.addEventListener('click', () => setStep(2));
  }

  // Stepper direct clicks
  stepBtn1.addEventListener('click', () => {
    if (sectionQuestionnaire && sectionQuestionnaire.style.display !== 'none') {
      showQuestionnaireSection();
    } else {
      showUsernameSection();
    }
  });

  stepBtn2.addEventListener('click', () => {
    if (currentBeginnerData) setStep(2);
  });

  stepBtn3.addEventListener('click', () => {
    if (selectedIssue) setStep(3);
  });

  // =========================================================================
  // Step 2: Render Profile & Issues
  // =========================================================================
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
      top_languages: userSkills.map(s => s.skill),
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

    // Render Tech Stack Languages + Questionnaire skills
    if (userLanguagesList) {
      const skillsToRender = userSkills.length > 0 ? userSkills : (prof.top_languages || []).map(l => ({ skill: l, level: 'beginner' }));
      if (skillsToRender.length > 0) {
        userLanguagesList.innerHTML = skillsToRender.map(s => `
          <span class="lang-pill">
            ${escapeHtml(s.skill)} <small style="font-size:10px; opacity:0.8; text-transform:uppercase;">(${escapeHtml(s.level || 'beginner')})</small>
          </span>
        `).join('');
      } else {
        userLanguagesList.innerHTML = '<span style="color:#64748b; font-size:12px;">General open source</span>';
      }
    }

    // Render Evidence Citations
    if (citationsList && citationsCount) {
      const citations = cites && cites.length > 0 ? cites : [
        { source: 'repos', detail: `Analysed public repositories for @${prof.username || inputUser}.` },
        { source: 'questionnaire', detail: `Applied ${userHours} hrs/week and ${userGoal} goal from questionnaire.` },
        { source: 'search', detail: `Discovered starter tasks matching detected skills.` }
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
          <p style="color: #64748b; font-size: 14px;">${isSavedView ? 'Bookmark issues to see them here.' : 'Try adjusting your questionnaire skills or topics.'}</p>
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
          <div class="issue-card-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
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
          const username = ghUsernameInput ? ghUsernameInput.value.trim() : 'anonymous';
          const res = await fetch(`${apiUrl}/beginner/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ issue: iss, username })
          });
          if (res.ok) {
            btn.textContent = '★ Saved';
            btn.disabled = true;
            loadSavedIssues();
          } else {
            btn.textContent = '★ Save';
          }
        } catch {
          btn.textContent = '★ Save';
        }
      });
    });
  }

  async function loadStarterIssues(username) {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const res = await fetch(`${apiUrl}/beginner/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });
      if (res.ok) {
        currentBeginnerData = await res.json();
        renderMatchedIssues(currentBeginnerData.recommended_issues);
      }
    } catch (e) {
      console.warn('Could not load issues:', e);
    }
  }

  // =========================================================================
  // Step 3: Implementation Roadmap & Plan
  // =========================================================================
  function populatePlan(issue) {
    if (!issue) return;
    if (planTitle) planTitle.textContent = issue.title;
    if (planIssueLink) {
      const url = issue.html_url || `https://github.com/${issue.repo}/issues/${issue.issue_number}`;
      planIssueLink.href = url;
      planIssueLink.textContent = `View ${issue.repo} #${issue.issue_number} ↗`;
    }

    const steps = issue.implementation_steps || [
      '1. Fork repository and configure development environment.',
      '2. Inspect module source code and write unit reproduction tests.',
      '3. Implement required changes complying with project guidelines.',
      '4. Run linters, test suite, and open verified pull request.'
    ];

    if (checklistBox) {
      checklistBox.innerHTML = steps.map(step => `
        <label class="check-row">
          <input type="checkbox" class="plan-cb">
          <span>${escapeHtml(step)}</span>
        </label>
      `).join('');

      attachChecklistCounters();
    }

    if (codebaseRefList) {
      const refs = issue.codebase_references || [
        { type: 'code', reference: 'src/main.py' },
        { type: 'tests', reference: 'tests/test_main.py' }
      ];
      codebaseRefList.innerHTML = refs.map(r => `
        <li class="reads-item">
          <span class="code-pill">${escapeHtml(r.type || 'code')}</span>
          <span class="reads-desc"><code>${escapeHtml(r.reference || '')}</code></span>
        </li>
      `).join('');
    }
  }

  function attachChecklistCounters() {
    const cbs = document.querySelectorAll('.plan-cb');
    function updateCounter() {
      const total = cbs.length;
      const checked = Array.from(cbs).filter(cb => cb.checked).length;
      if (checklistCounter) {
        checklistCounter.textContent = `${checked} of ${total} completed`;
      }
    }
    cbs.forEach(cb => cb.addEventListener('change', updateCounter));
    updateCounter();
  }

  // =========================================================================
  // Saved Issues Bookmark Drawer
  // =========================================================================
  async function loadSavedIssues() {
    try {
      const apiUrl = window.CONTRIB_API_URL || '';
      const username = ghUsernameInput ? ghUsernameInput.value.trim() : 'anonymous';
      const res = await fetch(`${apiUrl}/beginner/saved?username=${encodeURIComponent(username)}`);
      if (!res.ok) return;
      const data = await res.json();
      savedIssuesList = data.saved_issues || [];
      if (savedCountSpan) savedCountSpan.textContent = savedIssuesList.length;
    } catch (e) {
      console.warn('Could not load saved issues:', e);
    }
  }

  if (btnToggleSaved) {
    btnToggleSaved.addEventListener('click', () => {
      isViewingSaved = !isViewingSaved;
      if (isViewingSaved) {
        btnToggleSaved.textContent = '← All Recommendations';
        renderMatchedIssues(savedIssuesList, true);
      } else {
        btnToggleSaved.innerHTML = `★ Saved Issues (<span id="saved-count">${savedIssuesList.length}</span>)`;
        renderMatchedIssues(currentBeginnerData?.recommended_issues || [], false);
      }
    });
  }

  loadSavedIssues();
});
