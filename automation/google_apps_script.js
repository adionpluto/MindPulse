/**
 * MindPulse - Psychological Welfare Assessment Platform
 * Community Engagement Project (CEP)
 * 
 * Instructions:
 * 1. Open your Google Form (or linked Google Sheet) -> Extensions -> Apps Script.
 * 2. Replace all code in Code.gs with this file.
 * 3. (Optional) Run `setupMindPulseForm()` once to automatically structure your Google Form
 *    with a Welcome Page, Demographic Fields (Name, Age, Gender), and Assessment Questions!
 * 4. Add Trigger: onFormSubmit -> From form -> On form submit.
 */

const CONFIG = {
  GITHUB_OWNER: "adionpluto",
  GITHUB_REPO: "MindPulse",
  GITHUB_TOKEN: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",
  COHORT: "CEP Cohort 2026"
};

/**
 * Triggered on every form submission.
 */
function onFormSubmit(e) {
  try {
    let answers = {};
    let timestamp = new Date().toISOString();
    let participantName = "Participant";
    let age = "N/A";
    let gender = "N/A";

    if (e && e.response) {
      // Triggered directly from Google Form
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
      // Triggered from linked Google Sheet
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
    } else {
      // Manual test run
      participantName = "Aditya Choubey";
      age = "21";
      gender = "Male";
      answers = {
        "Full Name": "Aditya Choubey",
        "Age": "21",
        "Gender": "Male",
        "How often do you feel overwhelmed by your daily responsibilities?": "Often",
        "How frequently do you experience physical tension or racing thoughts?": "Very Often",
        "How would you rate your overall mood stability and positivity?": "Neutral",
        "How often do you wake up feeling well-rested and energized?": "Rarely",
        "When facing intense stress, how effectively do you use proactive coping strategies?": "Sometimes",
        "How connected and supported do you feel by your community?": "Agree",
        "What are your primary sources of stress currently?": "Project deadlines and exams",
        "What activities bring you the most peace of mind?": "Evening walks and music"
      };
    }

    // Generate clean slug from participant's name
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
    Logger.log("Dispatched " + slug + " | Response: " + response.getResponseCode());
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err.toString());
  }
}

/**
 * ??? UTILITY: Auto-configure Google Form with 3 Multi-Page Sections!
 * Run this function directly in Apps Script to automatically build the form layout.
 */
function setupMindPulseForm() {
  const form = FormApp.getActiveForm();
  if (!form) {
    Logger.log("Error: Must be run in an Apps Script attached to a Google Form.");
    return;
  }

  // 1. Configure Header / Welcome
  form.setTitle("MindPulse: Psychological Welfare Assessment");
  form.setDescription(
    "Welcome to MindPulse ? a Community Engagement Project (CEP) initiative dedicated to evaluating emotional wellbeing, stress patterns, and resilience.\n\n" +
    "?? What to Expect:\n" +
    "? Takes only 2-3 minutes to complete.\n" +
    "? Upon submission, an individual psychological report with interactive radar charts and personalized self-improvement strategies is automatically generated.\n\n" +
    "Click 'Next' to begin with your basic information."
  );

  // Clear existing items if desired or append structured sections
  // Section 2: Demographics
  const sec2 = form.addPageBreakItem();
  sec2.setTitle("Participant Demographics");
  sec2.setHelpText("Please provide your basic details so we can personalize your welfare report.");

  const nameItem = form.addTextItem();
  nameItem.setTitle("Full Name");
  nameItem.setHelpText("Enter your name (or preferred nickname) as you would like it to appear on your report.");
  nameItem.setRequired(true);

  const ageItem = form.addTextItem();
  ageItem.setTitle("Age");
  ageItem.setHelpText("Enter your age (e.g., 20)");
  ageItem.setRequired(true);

  const genderItem = form.addMultipleChoiceItem();
  genderItem.setTitle("Gender");
  genderItem.setChoiceValues(["Male", "Female", "Non-binary", "Prefer not to say", "Other"]);
  genderItem.setRequired(true);

  // Section 3: Psychological Assessment
  const sec3 = form.addPageBreakItem();
  sec3.setTitle("Psychological Welfare & Wellbeing Assessment");
  sec3.setHelpText("Answer honestly based on how you have felt over the past 2 weeks.");

  const q1 = form.addMultipleChoiceItem();
  q1.setTitle("How often do you feel overwhelmed by your daily responsibilities or academic deadlines?");
  q1.setChoiceValues(["Never", "Rarely", "Sometimes", "Often", "Always"]);
  q1.setRequired(true);

  const q2 = form.addMultipleChoiceItem();
  q2.setTitle("How frequently do you experience physical tension, nervousness, or racing thoughts?");
  q2.setChoiceValues(["Almost Never", "Rarely", "Sometimes", "Fairly Often", "Very Often"]);
  q2.setRequired(true);

  const q3 = form.addMultipleChoiceItem();
  q3.setTitle("How would you rate your overall mood stability and positivity over the past two weeks?");
  q3.setChoiceValues(["Poor", "Fair", "Neutral", "Good", "Excellent"]);
  q3.setRequired(true);

  const q4 = form.addMultipleChoiceItem();
  q4.setTitle("How often do you wake up feeling well-rested and energized for the day?");
  q4.setChoiceValues(["Never", "Rarely", "Sometimes", "Often", "Always"]);
  q4.setRequired(true);

  const q5 = form.addMultipleChoiceItem();
  q5.setTitle("When facing intense stress, how effectively do you use proactive coping strategies (e.g., exercise, planning, mindfulness)?");
  q5.setChoiceValues(["Never", "Rarely", "Sometimes", "Often", "Always"]);
  q5.setRequired(true);

  const q6 = form.addMultipleChoiceItem();
  q6.setTitle("How connected and supported do you feel by your friends, family, or community?");
  q6.setChoiceValues(["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]);
  q6.setRequired(true);

  const q7 = form.addParagraphTextItem();
  q7.setTitle("What are your primary sources of stress or concern currently?");
  q7.setHelpText("e.g., Exam pressure, workload, sleep issues, career anxiety.");
  q7.setRequired(false);

  const q8 = form.addParagraphTextItem();
  q8.setTitle("What activities or habits currently bring you the most peace of mind?");
  q8.setHelpText("e.g., Listening to music, workout, reading, spending time outdoors.");
  q8.setRequired(false);

  Logger.log("MindPulse Google Form successfully structured into 3 sections!");
}

function testDispatch() {
  onFormSubmit(null);
}
