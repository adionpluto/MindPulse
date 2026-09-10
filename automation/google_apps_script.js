/**
 * MindPulse - Psychological Welfare Assessment Platform
 * Community Engagement Project (CEP)
 */
const CONFIG = {
  GITHUB_OWNER: "adionpluto",
  GITHUB_REPO: "MindPulse",
  GITHUB_TOKEN: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",
  COHORT: "CEP Cohort 2026"
};

/**
 * Triggered automatically on every form submission.
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
    }

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
    Logger.log("Dispatched report for " + participantName + " (" + slug + ") | Status: " + response.getResponseCode());
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err.toString());
  }
}

/**
 * ??? 1-CLICK CLEAN RESET & BUILD:
 * Clears any old duplicate questions and perfectly creates:
 * Page 1: Welcome & Overview (No questions, just Next button)
 * Page 2: Demographics (Full Name, Age, Gender)
 * Page 3: Welfare Assessment (Questions 1 to 8)
 */
function resetAndBuildForm() {
  const form = FormApp.getActiveForm();
  if (!form) return;

  // 1. Delete all previous duplicate/old questions
  const items = form.getItems();
  for (let i = items.length - 1; i >= 0; i--) {
    form.deleteItem(items[i]);
  }

  // 2. Section 1 (Welcome Page - purely informational)
  form.setTitle("MindPulse: Psychological Welfare Assessment");
  form.setDescription(
    "Welcome to MindPulse ? a Community Engagement Project (CEP) focused on evaluating emotional wellbeing, stress patterns, and resilience to deliver personalized self-improvement reports.\n\n" +
    "?? Time required: ~2 minutes\n" +
    "?? Confidentiality: Data is processed securely to generate your individual report.\n\n" +
    "Click 'Next' below to begin."
  );

  // Section 2: Demographics Page
  const sec2 = form.addPageBreakItem();
  sec2.setTitle("Participant Demographics");
  sec2.setHelpText("Please enter your basic details so we can personalize your digital report.");

  const nameItem = form.addTextItem();
  nameItem.setTitle("Full Name");
  nameItem.setHelpText("Enter your name as you'd like it to appear on your report.");
  nameItem.setRequired(true);

  const ageItem = form.addTextItem();
  ageItem.setTitle("Age");
  ageItem.setHelpText("Enter your age (e.g. 21)");
  ageItem.setRequired(true);

  const genderItem = form.addMultipleChoiceItem();
  genderItem.setTitle("Gender");
  genderItem.setChoiceValues(["Male", "Female", "Non-binary", "Prefer not to say", "Other"]);
  genderItem.setRequired(true);

  // Section 3: Psychological Assessment Questions
  const sec3 = form.addPageBreakItem();
  sec3.setTitle("Psychological Welfare & Wellbeing Assessment");
  sec3.setHelpText("Please answer honestly based on your experience over the past two weeks.");

  const q1 = form.addMultipleChoiceItem();
  q1.setTitle("1. How often do you feel overwhelmed by your daily responsibilities or academic deadlines?");
  q1.setChoiceValues(["1 - Never", "2 - Rarely", "3 - Sometimes", "4 - Often", "5 - Almost Always"]);
  q1.setRequired(true);

  const q2 = form.addMultipleChoiceItem();
  q2.setTitle("2. How frequently do you experience physical tension, nervousness, or racing thoughts?");
  q2.setChoiceValues(["1 - Almost Never", "2 - Rarely", "3 - Sometimes", "4 - Fairly Often", "5 - Very Often"]);
  q2.setRequired(true);

  const q3 = form.addMultipleChoiceItem();
  q3.setTitle("3. How would you rate your overall mood stability and positivity over the past two weeks?");
  q3.setChoiceValues(["1 - Poor", "2 - Fair", "3 - Neutral", "4 - Good", "5 - Excellent"]);
  q3.setRequired(true);

  const q4 = form.addMultipleChoiceItem();
  q4.setTitle("4. How often do you wake up feeling well-rested and energized for the day?");
  q4.setChoiceValues(["1 - Never", "2 - Rarely", "3 - Sometimes", "4 - Often", "5 - Almost Always"]);
  q4.setRequired(true);

  const q5 = form.addMultipleChoiceItem();
  q5.setTitle("5. When facing intense stress, how effectively do you use proactive coping strategies?");
  q5.setChoiceValues(["1 - Never", "2 - Rarely", "3 - Sometimes", "4 - Often", "5 - Always"]);
  q5.setRequired(true);

  const q6 = form.addMultipleChoiceItem();
  q6.setTitle("6. How connected and supported do you feel by your friends, family, or community?");
  q6.setChoiceValues(["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"]);
  q6.setRequired(true);

  const q7 = form.addParagraphTextItem();
  q7.setTitle("7. What are your primary sources of stress or concern currently?");
  q7.setHelpText("e.g., Exam deadlines, career uncertainty, sleep issues, workload.");
  q7.setRequired(false);

  const q8 = form.addParagraphTextItem();
  q8.setTitle("8. What activities or habits currently bring you the most peace of mind?");
  q8.setHelpText("e.g., Music, evening walks, workout, reading, spending time with peers.");
  q8.setRequired(false);

  Logger.log("Google Form cleanly reset and rebuilt with 3 distinct pages!");
}
