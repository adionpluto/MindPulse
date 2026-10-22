/**
 * MindPulse - Psychological Welfare Assessment Platform
 * Community Engagement Project (CEP)
 * =========================================================================
 * 12-Question Standardized MCQ Psychological Welfare Assessment
 * Scale: "1 - Highly Unlikely" to "5 - Highly Likely" (100% Single Choice)
 * =========================================================================
 */

const CONFIG = {
  GITHUB_OWNER: "adionpluto",
  GITHUB_REPO: "MindPulse",
  GITHUB_TOKEN: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",
  COHORT: "CEP Cohort 2026"
};

/**
 * ??? 1-CLICK CLEAN FORM SETUP:
 * Clears old vague/subjective questions and instantly builds:
 * Page 1: Welcome Page (Overview & Next button)
 * Page 2: Participant Demographics (Full Name, Age, Gender)
 * Page 3: 12 Precise MCQ Psychological Assessment Questions
 */
function resetAndBuildForm() {
  const form = FormApp.getActiveForm();
  if (!form) {
    Logger.log("Error: Open this from the Google Form's Script Editor.");
    return;
  }

  // 1. Delete all previous questions
  const items = form.getItems();
  for (let i = items.length - 1; i >= 0; i--) {
    form.deleteItem(items[i]);
  }

  // 2. Section 1: Welcome Page
  form.setTitle("MindPulse: Psychological Welfare Assessment");
  form.setDescription(
    "Welcome to MindPulse ? a Community Engagement Project (CEP) focused on evaluating emotional wellbeing, stress patterns, sleep quality, and daily self-care to deliver personalized self-improvement reports.\n\n" +
    "?? Time required: ~2 minutes (12 quick single-choice questions)\n" +
    "?? Outcome: An instant personalized digital report with radar analytics and tailored self-improvement strategies.\n\n" +
    "Click 'Next' below to enter your basic details and begin."
  );

  // Section 2: Demographics
  const sec2 = form.addPageBreakItem();
  sec2.setTitle("Participant Demographics");
  sec2.setHelpText("Please enter your basic details so we can personalize your digital welfare report.");

  const nameItem = form.addTextItem();
  nameItem.setTitle("Full Name");
  nameItem.setHelpText("Enter your name as you'd like it to appear on your report.");
  nameItem.setRequired(true);

  const ageItem = form.addTextItem();
  ageItem.setTitle("Age");
  ageItem.setHelpText("Enter your age (e.g., 20)");
  ageItem.setRequired(true);

  const genderItem = form.addMultipleChoiceItem();
  genderItem.setTitle("Gender");
  genderItem.setChoiceValues(["Male", "Female", "Non-binary", "Prefer not to say", "Other"]);
  genderItem.setRequired(true);

  // Section 3: 12 MCQ Welfare Assessment Questions
  const sec3 = form.addPageBreakItem();
  sec3.setTitle("Psychological Welfare & Wellbeing Assessment");
  sec3.setHelpText("Please select the choice that best matches your feelings and habits over the past two weeks.");

  const mcqScale = [
    "1 - Highly Unlikely",
    "2 - Unlikely",
    "3 - Moderately / Sometimes",
    "4 - Likely",
    "5 - Highly Likely"
  ];

  const questions = [
    "1. How likely are you to wake up feeling well-rested, energized, and refreshed for the day?",
    "2. How likely are you to take dedicated personal time for yourself each day to unwind and relax?",
    "3. How likely are you to feel genuinely happy, content, and positive in your day-to-day routine?",
    "4. How likely are you to feel overwhelmed or weighed down by your daily academic or personal responsibilities?",
    "5. How likely are you to experience physical tension, nervousness, or racing thoughts under pressure?",
    "6. When unexpected challenges or setbacks occur, how likely are you to stay calm and emotionally balanced?",
    "7. How likely are you to maintain mental clarity, concentration, and motivation throughout your daily tasks?",
    "8. When facing difficult stress, how likely are you to actively use healthy coping habits (e.g. exercise, walks, hobbies, mindfulness)?",
    "9. How likely are you to reach out to friends, family, or mentors when you need emotional comfort or guidance?",
    "10. How likely do you feel valued, respected, and socially connected within your peer community?",
    "11. How likely are you to get trapped in repetitive overthinking, self-doubt, or worry about future outcomes?",
    "12. How likely are you to feel hopeful, motivated, and optimistic about your future and personal growth?"
  ];

  for (let i = 0; i < questions.length; i++) {
    const q = form.addMultipleChoiceItem();
    q.setTitle(questions[i]);
    q.setChoiceValues(mcqScale);
    q.setRequired(true);
  }

  Logger.log("?? SUCCESS: Form cleanly rebuilt with 3 sections and 12 standardized MCQs!");
}

/**
 * ? Send single payload to GitHub Actions
 */
function sendToGitHub(participantName, age, gender, answers, timestamp) {
  let slug = participantName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  if (!slug || slug === "participant") {
    slug = "user-" + Utilities.getUuid().substring(0, 6);
  }

  const payload = {
    event_type: "new_form_response",
    client_payload: {
      submission_id: slug,
      participant_name: participantName,
      age: age,
      gender: gender,
      timestamp: timestamp,
      cohort: CONFIG.COHORT,
      answers: answers
    }
  };

  const url = "https://api.github.com/repos/" + CONFIG.GITHUB_OWNER + "/" + CONFIG.GITHUB_REPO + "/dispatches";
  const options = {
    method: "post",
    contentType: "application/json",
    headers: {
      "Authorization": "token " + CONFIG.GITHUB_TOKEN,
      "Accept": "application/vnd.github.v3+json",
      "User-Agent": "MindPulse-GoogleAppsScript"
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  if (code >= 200 && code < 300) {
    Logger.log("? Dispatched report for " + participantName + " (" + slug + ") | Status: " + code);
    return true;
  } else {
    Logger.log("? Failed for " + participantName + " | Status " + code + ": " + response.getContentText());
    return false;
  }
}

/**
 * ?? Automatically triggered on form submit
 */
function onFormSubmit(e) {
  try {
    let answers = {};
    let timestamp = new Date().toISOString();
    let participantName = "Participant";
    let age = "N/A";
    let gender = "N/A";

    if (e && e.response) {
      const itemResponses = e.response.getItemResponses();
      timestamp = e.response.getTimestamp().toISOString();
      for (let i = 0; i < itemResponses.length; i++) {
        const item = itemResponses[i];
        const question = item.getItem().getTitle();
        const response = item.getResponse();
        const val = Array.isArray(response) ? response.join(", ") : String(response);
        answers[question] = val;

        const qLower = question.toLowerCase();
        if (qLower.includes("name")) {
          participantName = val.trim();
        } else if (qLower.includes("age")) {
          age = val.trim();
        } else if (qLower.includes("gender")) {
          gender = val.trim();
        }
      }
    } else if (e && e.values && e.range) {
      const sheet = e.range.getSheet();
      const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      const rowValues = e.values;
      timestamp = rowValues[0] || timestamp;
      for (let i = 1; i < headers.length; i++) {
        if (headers[i] && rowValues[i]) {
          const q = headers[i];
          const val = String(rowValues[i]);
          answers[q] = val;
          const qLower = q.toLowerCase();
          if (qLower.includes("name")) {
            participantName = val.trim();
          } else if (qLower.includes("age")) {
            age = val.trim();
          } else if (qLower.includes("gender")) {
            gender = val.trim();
          }
        }
      }
    }

    sendToGitHub(participantName, age, gender, answers, timestamp);
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err.toString());
  }
}

/**
 * ?? BATCH SYNC: Reads all past responses stored in Google Forms and syncs them to GitHub
 */
function syncAllResponses() {
  const form = FormApp.getActiveForm();
  if (!form) {
    Logger.log("Error: Must run from Apps Script attached to Google Form.");
    return;
  }

  const responses = form.getResponses();
  Logger.log("Found " + responses.length + " total responses in Google Form. Starting sync...");

  let successCount = 0;
  for (let i = 0; i < responses.length; i++) {
    const itemResponses = responses[i].getItemResponses();
    const timestamp = responses[i].getTimestamp().toISOString();
    let answers = {};
    let participantName = "Participant";
    let age = "N/A";
    let gender = "N/A";

    for (let j = 0; j < itemResponses.length; j++) {
      const item = itemResponses[j];
      const question = item.getItem().getTitle();
      const response = item.getResponse();
      const val = Array.isArray(response) ? response.join(", ") : String(response);
      answers[question] = val;

      const qLower = question.toLowerCase();
      if (qLower.includes("name")) {
        participantName = val.trim();
      } else if (qLower.includes("age")) {
        age = val.trim();
      } else if (qLower.includes("gender")) {
        gender = val.trim();
      }
    }

    const ok = sendToGitHub(participantName, age, gender, answers, timestamp);
    if (ok) successCount++;
    Utilities.sleep(1500);
  }

  Logger.log("?? Complete! " + successCount + " / " + responses.length + " responses successfully synced to GitHub!");
}
