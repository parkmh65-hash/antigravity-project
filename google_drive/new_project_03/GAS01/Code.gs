/**
 * Google Apps Script Backend (Code.gs)
 *
 * Serves the HTML UI and handles server-side execution (e.g. proxying RAG requests to Cloud Run).
 */

function doGet(e) {
  // Load index.html and evaluate any template variables (e.g., style, script imports)
  return HtmlService.createTemplateFromFile('index')
      .evaluate()
      .setTitle('RAG AI Assistant')
      // Crucial: ALLOWALL enables embedding the Web App in Google Sites iframe!
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * Sends the user question to the FastAPI backend hosted on Google Cloud Run.
 * 
 * @param {string} question The question asked by the user.
 * @return {string} The reply from the AI agent.
 */
function askAI(question) {
  // Fetch the backend URL from script properties (recommended) or fallback
  var backendUrl = PropertiesService.getScriptProperties().getProperty('BACKEND_URL');
  if (!backendUrl || backendUrl === "https://your-cloud-run-url.run.app/chat") {
    // Fallback URL placeholder
    backendUrl = "https://your-cloud-run-url.run.app/chat";
    return "💡 [안내] Google Apps Script 프로젝트 설정(Project Settings) -> Script Properties에 'BACKEND_URL' 키와 실제 배포된 Cloud Run URL(/chat 포함)을 설정해 주세요.\n\n현재 임시 설정된 URL: " + backendUrl;
  }
  
  // Auto-append '/chat' if missing to avoid routing errors
  if (backendUrl && !backendUrl.match(/\/chat\/?$/)) {
    backendUrl = backendUrl.replace(/\/$/, '') + '/chat';
  }
  
  var payload = {
    "message": question
  };
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };
  
  try {
    var response = UrlFetchApp.fetch(backendUrl, options);
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    if (responseCode === 200) {
      var data = JSON.parse(responseBody);
      return data.reply;
    } else {
      return "⚠️ 백엔드 오류 발생 (HTTP " + responseCode + "):\n" + responseBody;
    }
  } catch (error) {
    return "❌ 백엔드 서버와 통신할 수 없습니다:\n" + error.toString();
  }
}
