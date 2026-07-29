/**
 * Sejong City Cultural Heritage Service
 * Google Apps Script - Admin Portal Backend (Code.gs)
 * 
 * This script serves the HTML Dashboard UI and connects to the FastAPI backend.
 */

// Config: Replace this with your actual Google Cloud Run deployed backend URL when live
var API_BASE_URL = "http://localhost:8080"; 

/**
 * Serves the HTML frontend on web app deployment
 */
function doGet() {
  var template = HtmlService.createTemplateFromFile('Index');
  return template.evaluate()
    .setTitle('세종시 문화유산 제보 관리자 포털')
    .setSandboxMode(HtmlService.SandboxMode.IFRAME)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Helper to get active API URL (checks script properties first, falls back to default)
 */
function getApiBaseUrl() {
  var scriptProperties = PropertiesService.getScriptProperties();
  var customUrl = scriptProperties.getProperty('API_BASE_URL');
  return customUrl ? customUrl : API_BASE_URL;
}

/**
 * Helper to get active Admin token (checks script properties first, falls back to default)
 */
function getAdminToken() {
  var scriptProperties = PropertiesService.getScriptProperties();
  var customToken = scriptProperties.getProperty('ADMIN_TOKEN');
  return customToken ? customToken : "admin-super-token";
}

/**
 * Fetches all pending citizen reports from the FastAPI backend
 */
function fetchPendingReports() {
  var url = getApiBaseUrl() + "/api/v1/reports/pending";
  try {
    var response = UrlFetchApp.fetch(url, {
      "method": "get",
      "headers": {
        "Authorization": "Bearer " + getAdminToken()
      },
      "muteHttpExceptions": true
    });
    
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    if (responseCode !== 200) {
      throw new Error("서버 오류 (" + responseCode + "): " + responseBody);
    }
    
    var result = JSON.parse(responseBody);
    return result.data;
  } catch (e) {
    Logger.log("fetchPendingReports Error: " + e.toString());
    throw new Error("FastAPI 백엔드 연결 실패. 서버가 실행 중인지 확인하세요. (오류: " + e.message + ")");
  }
}

/**
 * Reviews (Approves/Rejects) a citizen report via FastAPI backend
 */
function reviewReport(reportId, status, adminComment) {
  var url = getApiBaseUrl() + "/api/v1/reports/review";
  var payload = {
    "report_id": parseInt(reportId, 10),
    "status": status,
    "admin_comment": adminComment || ""
  };
  
  try {
    var response = UrlFetchApp.fetch(url, {
      "method": "post",
      "contentType": "application/json",
      "headers": {
        "Authorization": "Bearer " + getAdminToken()
      },
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    });
    
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    if (responseCode !== 200) {
      throw new Error("서버 오류 (" + responseCode + "): " + responseBody);
    }
    
    return JSON.parse(responseBody);
  } catch (e) {
    Logger.log("reviewReport Error: " + e.toString());
    throw new Error("리뷰 제출 실패: " + e.message);
  }
}

/**
 * Utility to dynamically update the backend endpoint URL in properties
 */
function setBackendUrl(newUrl) {
  PropertiesService.getScriptProperties().setProperty('API_BASE_URL', newUrl);
  return "API URL이 다음으로 성공적으로 설정되었습니다: " + newUrl;
}

/**
 * Fetches all system settings including GAS and FastAPI backend keys
 */
function getSettings() {
  var result = {
    "API_BASE_URL": getApiBaseUrl(),
    "ADMIN_TOKEN": getAdminToken(),
    "GOOGLE_API_KEY": "",
    "TOURAPI_KEY": "",
    "SEJONG_BUS_API_KEY": "",
    "CULTURAL_API_KEY": "",
    "SUPABASE_URL": "",
    "SUPABASE_KEY": "",
    "NEO4J_URI": "",
    "NEO4J_USERNAME": "",
    "NEO4J_PASSWORD": ""
  };
  
  var url = getApiBaseUrl() + "/api/v1/admin/settings";
  try {
    var response = UrlFetchApp.fetch(url, {
      "method": "get",
      "headers": {
        "Authorization": "Bearer " + getAdminToken()
      },
      "muteHttpExceptions": true
    });
    
    var responseCode = response.getResponseCode();
    if (responseCode === 200) {
      var backendSettings = JSON.parse(response.getContentText());
      result["GOOGLE_API_KEY"] = backendSettings["GOOGLE_API_KEY"] || "";
      result["TOURAPI_KEY"] = backendSettings["TOURAPI_KEY"] || "";
      result["SEJONG_BUS_API_KEY"] = backendSettings["SEJONG_BUS_API_KEY"] || "";
      result["CULTURAL_API_KEY"] = backendSettings["CULTURAL_API_KEY"] || "";
      result["SUPABASE_URL"] = backendSettings["SUPABASE_URL"] || "";
      result["SUPABASE_KEY"] = backendSettings["SUPABASE_KEY"] || "";
      result["NEO4J_URI"] = backendSettings["NEO4J_URI"] || "";
      result["NEO4J_USERNAME"] = backendSettings["NEO4J_USERNAME"] || "";
      result["NEO4J_PASSWORD"] = backendSettings["NEO4J_PASSWORD"] || "";
    }
  } catch (e) {
    Logger.log("getSettings error: " + e.toString());
  }
  
  return result;
}

/**
 * Saves both GAS level and backend level settings
 */
function saveSettings(settings) {
  var scriptProperties = PropertiesService.getScriptProperties();
  
  // 1. Save GAS properties
  if (settings["API_BASE_URL"]) {
    scriptProperties.setProperty('API_BASE_URL', settings["API_BASE_URL"]);
  }
  if (settings["ADMIN_TOKEN"]) {
    scriptProperties.setProperty('ADMIN_TOKEN', settings["ADMIN_TOKEN"]);
  }
  
  // 2. Save Backend properties
  var url = (settings["API_BASE_URL"] || getApiBaseUrl()) + "/api/v1/admin/settings";
  var payload = {
    "GOOGLE_API_KEY": settings["GOOGLE_API_KEY"] || "",
    "TOURAPI_KEY": settings["TOURAPI_KEY"] || "",
    "SEJONG_BUS_API_KEY": settings["SEJONG_BUS_API_KEY"] || "",
    "CULTURAL_API_KEY": settings["CULTURAL_API_KEY"] || "",
    "SUPABASE_URL": settings["SUPABASE_URL"] || "",
    "SUPABASE_KEY": settings["SUPABASE_KEY"] || "",
    "NEO4J_URI": settings["NEO4J_URI"] || "",
    "NEO4J_USERNAME": settings["NEO4J_USERNAME"] || "",
    "NEO4J_PASSWORD": settings["NEO4J_PASSWORD"] || ""
  };
  
  try {
    var response = UrlFetchApp.fetch(url, {
      "method": "post",
      "contentType": "application/json",
      "headers": {
        "Authorization": "Bearer " + (settings["ADMIN_TOKEN"] || getAdminToken())
      },
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    });
    
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    if (responseCode !== 200) {
      throw new Error("백엔드 설정 저장 실패 (" + responseCode + "): " + responseBody);
    }
    
    return "설정이 성공적으로 저장되었습니다.";
  } catch (e) {
    Logger.log("saveSettings error: " + e.toString());
    throw new Error("백엔드 연동 설정 실패: " + e.message);
  }
}

/**
 * Fetches real-time statistics from backend
 */
function fetchHeritageStats() {
  var url = getApiBaseUrl() + "/api/heritages/stats";
  try {
    var response = UrlFetchApp.fetch(url, {
      "method": "get",
      "headers": {
        "Authorization": "Bearer " + getAdminToken()
      },
      "muteHttpExceptions": true
    });
    
    var responseCode = response.getResponseCode();
    if (responseCode === 200) {
      return JSON.parse(response.getContentText());
    }
  } catch (e) {
    Logger.log("fetchHeritageStats error: " + e.toString());
  }
  return { "official_count": 0, "citizen_count": 0 };
}
