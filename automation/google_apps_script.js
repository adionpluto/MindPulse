/**
 * MindPulse (Psyche-Reports) - Google Apps Script Webhook Trigger
 * ================================================================
 * This script automatically triggers whenever a participant submits your Google Form.
 * It sends the survey responses directly to GitHub Actions to evaluate metrics,
 * generate the HTML report (user-XX.html), and publish it to GitHub Pages.
 * 
 * SETUP INSTRUCTIONS:
 * 1. In your Google Form (or linked Google Sheet), click Extensions -> Apps Script.
 * 2. Delete any code in Code.gs and paste this entire file.
 * 3. Update the CONFIG variables below with your GitHub details.
 * 4. Click 'Triggers' (the clock icon on the left menu) -> Add Trigger:
 *    - Choose which function to run: onFormSubmit
 *    - Select event source: From form (or From spreadsheet)
 *    - Select event type: On form submit
 * 5. Save and grant necessary permissions. Done!
 */

const CONFIG = {
  // Your GitHub username or organization (e.g. 'octocat')
  GITHUB_OWNER: "adionpluto",

  // Your repository name (e.g. 'psyche-reports')
  GITHUB_REPO: "MindPulse",

  // Personal Access Token (PAT) with 'repo' scope or fine-grained Actions/Contents write permissions.
  // Tip: In Apps Script, you can also store this securely in Project Settings -> Script Properties -> GH_PAT
  GITHUB_TOKEN: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN",

  // Cohort or semester tag
  COHORT: "CEP Cohort 2026"
};

/**
 * Triggered on every form submission.
 */
function onFormSubmit(e) {
  try {
    let answers = {};
    let timestamp = new Date().toISOString();
    let participantId = "user-" + Utilities.getUuid().substring(0, 6);

    // Retrieve token from Script Properties if configured, or fallback to CONFIG
    const token = PropertiesService.getScriptProperties().getProperty("GH_PAT") || CONFIG.GITHUB_TOKEN;

    if (e && e.response) {
      // Triggered directly from Google Form
      const itemResponses = e.response.getItemResponses();
      timestamp = e.response.getTimestamp().toISOString();
      for (let i = 0; i < itemResponses.length; i++) {
        const item = itemResponses[i];
        const question = item.getItem().getTitle();
        const response = item.getResponse();
        answers[question] = Array.isArray(response) ? response.join(", ") : response;
      }
    } else if (e && e.values && e.range) {
      // Triggered from linked Google Sheet
      const sheet = e.range.getSheet();
      const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      const rowValues = e.values;
      timestamp = rowValues[0] || timestamp;
      for (let i = 1; i < headers.length; i++) {
        if (headers[i] && rowValues[i]) {
          answers[headers[i]] = rowValues[i];
        }
      }
      const rowIndex = e.range.getRow();
      participantId = "user-" + String(rowIndex - 1).padStart(2, '0');
    } else {
      // Manual test run in Apps Script editor
      Logger.log("Running in test mode...");
      answers = {
        "How often do you feel overwhelmed by your daily responsibilities?": "Often",
        "How frequently do you experience physical tension or racing thoughts?": "Sometimes",
        "How would you rate your overall mood stability and positivity?": "Good",
        "How often do you wake up feeling well-rested and energized?": "Sometimes",
        "When facing intense stress, how effectively do you use proactive coping strategies?": "Agree",
        "How connected and supported do you feel by your community?": "Agree",
        "What are your primary sources of stress currently?": "Project deadlines and exams",
        "What activities bring you the most peace of mind?": "Jogging and reading"
      };
    }

    const payload = {
      event_type: "new_form_response",
      client_payload: {
        submission_id: participantId,
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
        "Authorization": "token " + token,
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MindPulse-GoogleAppsScript"
      },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    Logger.log("GitHub Dispatch Response Code: " + responseCode);
    Logger.log("GitHub Dispatch Response Body: " + response.getContentText());

    if (responseCode >= 200 && responseCode < 300) {
      Logger.log("Successfully dispatched response for: " + participantId);
    } else {
      Logger.log("Failed to dispatch to GitHub. Check token and repo permissions.");
    }
  } catch (err) {
    Logger.log("Error in onFormSubmit: " + err.toString());
  }
}

/**
 * Test function to verify your connection to GitHub
 */
function testDispatch() {
  onFormSubmit(null);
}
