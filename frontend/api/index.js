const request = require("../utils/request");

function getInstitutions(params) {
  return request.get("/institutions", params);
}

function getInstitution(id) {
  return request.get(`/institutions/${id}`);
}

function getMajors(params) {
  return request.get("/majors", params);
}

function getMajor(id) {
  return request.get(`/majors/${id}`);
}

function getInstitutionMajors(params) {
  return request.get("/institution-majors", params);
}

function getInstitutionMajor(id, params) {
  return request.get(`/institution-majors/${id}`, params);
}

function compareInstitutionMajors(ids, year) {
  return request.get("/institution-majors/compare", { ids, year });
}

function createAssessment(payload) {
  return request.post("/assessments", payload);
}

function getAssessment(id) {
  return request.get(`/assessments/${id}`);
}

function getRecommendations(id) {
  return request.get(`/assessments/${id}/recommendations`);
}

function generatePlan(payload) {
  return request.post("/plans/generate", payload);
}

function getPlan(id) {
  return request.get(`/plans/${id}`);
}

function getPlanCalendar(id, params) {
  return request.get(`/plans/${id}/calendar`, params);
}

function createCheckIn(payload) {
  return request.post("/check-ins", payload);
}

function getProgress(params) {
  return request.get("/progress", params);
}

function getReport(period, params) {
  return request.get(`/reports/${period}`, params);
}

function getCurrentTimeline(params) {
  return request.get("/timeline/current", params);
}

function getProcessNodes(params) {
  return request.get("/process-nodes", params);
}

function createSubscription(payload) {
  return request.post("/subscriptions", payload);
}

function getSubscriptions(params) {
  return request.get("/subscriptions", params);
}

function getUpcomingReminders(params) {
  return request.get("/reminders/upcoming", params);
}

module.exports = {
  getInstitutions,
  getInstitution,
  getMajors,
  getMajor,
  getInstitutionMajors,
  getInstitutionMajor,
  compareInstitutionMajors,
  createAssessment,
  getAssessment,
  getRecommendations,
  generatePlan,
  getPlan,
  getPlanCalendar,
  createCheckIn,
  getProgress,
  getReport,
  getCurrentTimeline,
  getProcessNodes,
  createSubscription,
  getSubscriptions,
  getUpcomingReminders
};
