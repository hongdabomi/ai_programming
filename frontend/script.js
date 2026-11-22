const API_BASE_URL = "http://127.0.0.1:8000";
const form = document.querySelector("#profile-form");
const fieldset = document.querySelector("#allergy-fieldset");
const optionsContainer = document.querySelector("#allergy-options");
const saveButton = document.querySelector("#save-button");
const retryButton = document.querySelector("#retry-button");
const selectionSummary = document.querySelector("#selection-summary");
const saveStatus = document.querySelector("#save-status");
const menuForm = document.querySelector("#menu-form");
const menuEntryFieldset = document.querySelector("#menu-entry-fieldset");
const menuNameInput = document.querySelector("#menu-name");
const menuMealTypeInput = document.querySelector("#menu-meal-type");
const menuAllergensInput = document.querySelector("#menu-allergens");
const menuInformationComplete = document.querySelector(
  "#menu-information-complete",
);
const addMenuButton = document.querySelector("#add-menu-button");
const cancelMenuEditButton = document.querySelector(
  "#cancel-menu-edit-button",
);
const saveMealSheetButton = document.querySelector(
  "#save-meal-sheet-button",
);
const confirmMealSheetButton = document.querySelector(
  "#confirm-meal-sheet-button",
);
const analyzeDateButton = document.querySelector("#analyze-date-button");
const noMealButton = document.querySelector("#no-meal-button");
const analyzeLegacyButton = document.querySelector("#analyze-legacy-button");
const menuList = document.querySelector("#menu-list");
const analysisStatus = document.querySelector("#analysis-status");
const mealDateInput = document.querySelector("#meal-date-input");
const mealMonthInput = document.querySelector("#meal-month-input");
const monthCalendar = document.querySelector("#month-calendar");
const monthStatus = document.querySelector("#month-status");
const selectedDateBadge = document.querySelector("#selected-date-badge");
const selectedDateStatus = document.querySelector("#selected-date-status");
const legacyCard = document.querySelector("#unassigned-legacy-card");
const legacySummary = document.querySelector("#legacy-meal-sheet-summary");
const copyLegacyButton = document.querySelector("#copy-legacy-button");
const analysisResults = document.querySelector("#analysis-results");
const analysisDisclaimer = document.querySelector("#analysis-disclaimer");
const analysisResultsStatus = document.querySelector("#analysis-results-status");
const resultsHeading = document.querySelector("#results-heading");
const resultsDescription = document.querySelector("#results-description");
const progressWrap = document.querySelector("#progress-wrap");
const screens = {
  home: document.querySelector("#home-screen"),
  profile: document.querySelector("#profile-screen"),
  type: document.querySelector("#meal-type-screen"),
  monthly: document.querySelector("#monthly-screen"),
  review: document.querySelector("#meal-review-screen"),
  results: document.querySelector("#results-screen"),
};
const savedSheetAvailability = document.querySelector("#saved-sheet-availability");

let allergyOptions = [];
let allergyNumberToName = new Map();
let allergyNameToNumber = new Map();
let savedAllergies = [];
let menuItems = [];
let editingMenuId = null;
let isMealSheetLoaded = false;
let isMealSheetReviewed = false;
let isMealSheetDirty = false;
let isSavingMealSheet = false;
let isLoaded = false;
let isSaving = false;
let isAnalyzing = false;
let selectedDate = "";
let currentDateStatus = "NO_DATA";
let legacyMealSheet = null;
let reviewReturnStep = "type";

function showStep(step) {
  for (const [name, screen] of Object.entries(screens)) {
    screen.hidden = name !== step;
  }

  progressWrap.hidden = step === "home";
  const progressStep = step === "monthly" ? "type" : step;
  document.querySelectorAll(".progress li").forEach((item) => {
    if (item.dataset.step === progressStep) {
      item.setAttribute("aria-current", "step");
    } else {
      item.removeAttribute("aria-current");
    }
  });

  const navStep = step === "home"
    ? "home"
    : step === "profile"
      ? "profile"
      : "meal";
  for (const [button, isCurrent] of [
    [document.querySelector("#home-nav-button"), navStep === "home"],
    [document.querySelector("#profile-nav-button"), navStep === "profile"],
    [document.querySelector("#meal-nav-button"), navStep === "meal"],
  ]) {
    if (isCurrent) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  }
  window.scrollTo(0, 0);
}

function setMealSheetMode() {
  const title = document.querySelector("#meal-review-title");
  const description = document.querySelector("#meal-review-description");
  title.textContent = "하루치 급식 메뉴를 확인해요";
  description.textContent = selectedDate
    ? `${selectedDate} 하루치 메뉴를 확인하고 필요한 내용을 직접 입력·수정해 주세요.`
    : "하루의 모든 메뉴를 한 목록으로 확인하고, 필요한 내용을 직접 입력·수정해 주세요.";
}

function getAllergyDisplayName(allergy) {
  return allergy === "난류(가금류)"
    ? "난류(달걀 등 가금류 알)"
    : allergy;
}

function normalizeAllergenEntry(allergen) {
  return allergen === "달걀" ||
      allergen === "난류(달걀 등 가금류 알)"
    ? "난류(가금류)"
    : allergen;
}

function isValidNumberedAllergenItems(numberedItems, items) {
  return (
    Array.isArray(numberedItems) &&
    numberedItems.length === items.length &&
    numberedItems.every(
      (item, index) =>
        item &&
        typeof item.number === "number" &&
        Number.isInteger(item.number) &&
        item.number === index + 1 &&
        typeof item.name === "string" &&
        items.includes(item.name),
    ) &&
    new Set(numberedItems.map((item) => item.name)).size === items.length
  );
}

function renderAllergyNumberReference(numberedItems) {
  const list = document.querySelector("#allergy-number-reference");
  list.replaceChildren();
  numberedItems.forEach(({ number, name }) => {
    const item = document.createElement("li");
    item.textContent = `${number}. ${getAllergyDisplayName(name)}`;
    list.append(item);
  });
}

function resolveNumberedAllergen(allergen) {
  const normalized = normalizeAllergenEntry(allergen.trim());
  const knownNumber = allergyNameToNumber.get(normalized);
  if (knownNumber) {
    return { number: knownNumber, name: normalized };
  }

  const match = /^(?<number>[1-9]|1[0-9])(?:\.\s*(?<name>.+))?$/.exec(
    allergen.trim(),
  );
  if (!match?.groups) {
    return null;
  }

  const number = Number(match.groups.number);
  const name = allergyNumberToName.get(number);
  if (!name) {
    return null;
  }
  const providedName = match.groups.name?.trim();
  if (
    providedName &&
    normalizeAllergenEntry(providedName) !== name
  ) {
    return null;
  }
  return { number, name };
}

function renderAllergenTags(container, allergens) {
  container.className = "allergen-tags";
  if (!allergens || allergens.length === 0) {
    const tag = document.createElement("span");
    tag.className = "allergen-tag unknown";
    tag.textContent = "알레르기 표시 입력 없음";
    container.append(tag);
    return;
  }

  for (const allergen of allergens) {
    const mapped = resolveNumberedAllergen(allergen);
    const tag = document.createElement("span");
    tag.className = mapped ? "allergen-tag" : "allergen-tag unknown";
    tag.textContent = mapped
      ? `${mapped.number}. ${getAllergyDisplayName(mapped.name)}`
      : `확인 필요 · ${allergen}`;
    container.append(tag);
  }
}

function getSelectedAllergies() {
  return Array.from(
    optionsContainer.querySelectorAll('input[type="checkbox"]:checked'),
    (input) => input.value,
  );
}

function renderOptions(options, selectedAllergies) {
  const selected = new Set(selectedAllergies);
  optionsContainer.replaceChildren();

  for (const allergy of options) {
    const label = document.createElement("label");
    label.className = "allergy-option";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "allergies";
    checkbox.value = allergy;
    checkbox.checked = selected.has(allergy);
    checkbox.addEventListener("change", () => {
      updateFormState();
      analysisResults.replaceChildren();
      analysisDisclaimer.hidden = true;
      analysisResultsStatus.textContent = "";
    });

    const text = document.createElement("span");
    text.textContent = allergy === "난류(가금류)"
      ? "난류(달걀 등 가금류 알)"
      : allergy;

    label.append(checkbox, text);
    optionsContainer.append(label);
  }
}

function updateFormState(statusMessage) {
  const current = getSelectedAllergies();
  const hasUnsavedChanges =
    current.length !== savedAllergies.length ||
    current.some((allergy, index) => allergy !== savedAllergies[index]);

  selectionSummary.textContent = current.length
    ? `선택한 항목: ${current.join(", ")}`
    : "선택한 알레르기 항목이 없습니다.";

  if (statusMessage) {
    saveStatus.textContent = statusMessage;
  } else if (!isSaving) {
    saveStatus.textContent = hasUnsavedChanges
      ? "저장되지 않은 변경 사항이 있습니다."
      : current.length
        ? "저장된 상태입니다."
        : "저장된 알레르기 항목이 없습니다.";
  }

  saveButton.disabled = !isLoaded || isSaving || !hasUnsavedChanges;
  if (hasUnsavedChanges) {
    analysisStatus.textContent =
      "알레르기 정보에 저장되지 않은 변경 사항이 있습니다. 저장 후 비교할 수 있습니다.";
  } else if (
    analysisStatus.textContent.includes("저장되지 않은 변경 사항")
  ) {
    analysisStatus.textContent = savedAllergies.length
      ? "저장된 알레르기 정보를 사용할 수 있습니다."
      : "비교하려면 먼저 알레르기 정보를 등록해 주세요.";
  }
  updateAnalysisControls();
}

function updateAnalysisControls() {
  const currentAllergies = getSelectedAllergies();
  const hasUnsavedAllergyChanges =
    currentAllergies.length !== savedAllergies.length ||
    currentAllergies.some(
      (allergy, index) => allergy !== savedAllergies[index],
    );
  const canConfirmMealSheet =
    menuItems.length > 0 &&
    menuItems.every((menu) => menu.name.trim().length > 0);

  addMenuButton.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing ||
    !menuNameInput.value.trim();
  saveMealSheetButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing ||
    !isMealSheetDirty ||
    editingMenuId !== null;
  confirmMealSheetButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing ||
    !canConfirmMealSheet ||
    (isMealSheetReviewed && !isMealSheetDirty) ||
    editingMenuId !== null;
  noMealButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing ||
    editingMenuId !== null;
  analyzeDateButton.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    currentDateStatus !== "REVIEWED" ||
    !isMealSheetReviewed ||
    isSavingMealSheet ||
    isAnalyzing ||
    isMealSheetDirty ||
    editingMenuId !== null ||
    savedAllergies.length === 0 ||
    hasUnsavedAllergyChanges;
  analyzeLegacyButton.disabled =
    !isLoaded ||
    isAnalyzing ||
    isSavingMealSheet ||
    !legacyMealSheet ||
    !legacyMealSheet.reviewed ||
    savedAllergies.length === 0 ||
    hasUnsavedAllergyChanges;
  menuEntryFieldset.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing;
}

function isValidMealSheet(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    value.source === "manual" &&
    typeof value.reviewed === "boolean" &&
    Array.isArray(value.menus) &&
    value.menus.every(
      (menu) =>
        menu &&
        typeof menu.id === "string" &&
        menu.id.length > 0 &&
        typeof menu.name === "string" &&
        (menu.allergens === null ||
          (Array.isArray(menu.allergens) &&
            menu.allergens.every((item) => typeof item === "string"))) &&
        typeof menu.is_information_complete === "boolean",
    ) &&
    new Set(value.menus.map((menu) => menu.id)).size ===
      value.menus.length &&
    (!value.reviewed ||
      (value.menus.length > 0 &&
        value.menus.every((menu) => menu.name.trim().length > 0)))
  );
}

function isValidDateMealSheet(value, expectedDate) {
  const validStatuses = new Set([
    "NO_DATA",
    "DRAFT",
    "REVIEWED",
    "NO_MEAL",
  ]);
  const validMealTypes = new Set([
    "morning_snack",
    "lunch",
    "afternoon_snack",
  ]);
  return (
    value !== null &&
    typeof value === "object" &&
    value.date === expectedDate &&
    validStatuses.has(value.status) &&
    value.source === "manual" &&
    (value.service_status === null ||
      value.service_status === "provided" ||
      value.service_status === "no_meal") &&
    typeof value.reviewed === "boolean" &&
    Array.isArray(value.menus) &&
    value.menus.every(
      (menu) =>
        menu &&
        typeof menu.id === "string" &&
        menu.id.length > 0 &&
        typeof menu.name === "string" &&
        (menu.allergens === null ||
          (Array.isArray(menu.allergens) &&
            menu.allergens.every((item) => typeof item === "string"))) &&
        typeof menu.is_information_complete === "boolean" &&
        (menu.meal_type === null || validMealTypes.has(menu.meal_type)),
    ) &&
    new Set(value.menus.map((menu) => menu.id)).size ===
      value.menus.length &&
    (value.status !== "NO_DATA" ||
      (!value.reviewed && value.menus.length === 0)) &&
    (value.status !== "NO_MEAL" ||
      (value.service_status === "no_meal" &&
        value.reviewed &&
        value.menus.length === 0)) &&
    (value.status !== "DRAFT" ||
      (value.service_status === "provided" && !value.reviewed)) &&
    (value.status !== "REVIEWED" ||
      (value.service_status === "provided" &&
        value.reviewed &&
        value.menus.length > 0 &&
        value.menus.every((menu) => menu.name.trim().length > 0)))
  );
}

function getDateStatusLabel(status) {
  return {
    NO_DATA: "정보 없음",
    DRAFT: "검토 전",
    REVIEWED: "검토 완료",
    NO_MEAL: "급식 없음",
  }[status] || "상태 확인 필요";
}

function hasPendingDateEdits() {
  return isMealSheetDirty ||
    editingMenuId !== null ||
    menuNameInput.value.trim().length > 0 ||
    menuAllergensInput.value.trim().length > 0 ||
    menuInformationComplete.checked;
}

function confirmDateNavigation() {
  return !hasPendingDateEdits() ||
    window.confirm("저장되지 않은 변경 사항을 버리고 다른 날짜로 이동할까요?");
}

function updateSelectedDateStatus(message) {
  selectedDateBadge.textContent = getDateStatusLabel(currentDateStatus);
  selectedDateStatus.textContent = message || {
    NO_DATA: "이 날짜에는 저장된 급식 정보가 없습니다.",
    DRAFT: "검토 전 정보입니다. 내용을 확인하고 저장해 주세요.",
    REVIEWED: "검토 완료로 저장된 하루치 메뉴입니다.",
    NO_MEAL: "사용자가 확인한 급식 없음 상태입니다.",
  }[currentDateStatus];
}

function markMealSheetDirty() {
  isMealSheetDirty = true;
  isMealSheetReviewed = false;
  currentDateStatus = "DRAFT";
  updateSelectedDateStatus("저장되지 않은 변경 사항이 있습니다. 저장하면 검토 전 상태가 됩니다.");
  analysisResults.replaceChildren();
  analysisDisclaimer.hidden = true;
  analysisResultsStatus.textContent = "";
  analysisStatus.textContent =
    "저장되지 않은 메뉴 변경 사항이 있습니다. 저장하거나 검토 완료로 저장해 주세요.";
  updateAnalysisControls();
}

function resetMenuEditor() {
  editingMenuId = null;
  menuForm.reset();
  menuMealTypeInput.value = "";
  addMenuButton.textContent = "메뉴 추가";
  cancelMenuEditButton.hidden = true;
  updateAnalysisControls();
}

function renderMenuItems() {
  menuList.replaceChildren();

  if (menuItems.length === 0) {
    const emptyItem = document.createElement("li");
    emptyItem.className = "menu-item";
    emptyItem.textContent =
      "아직 등록된 메뉴가 없습니다. 하루치 메뉴를 하나 이상 추가해 주세요.";
    menuList.append(emptyItem);
  }

  for (const menu of menuItems) {
    const item = document.createElement("li");
    item.className = "menu-item";

    const header = document.createElement("div");
    header.className = "menu-item-header";
    const name = document.createElement("strong");
    name.textContent = menu.name;
    const actions = document.createElement("div");
    actions.className = "actions";
    const editButton = document.createElement("button");
    editButton.type = "button";
    editButton.className = "button-secondary";
    editButton.textContent = "수정";
    editButton.setAttribute("aria-label", `${menu.name} 메뉴 수정`);
    editButton.disabled = isSavingMealSheet || isAnalyzing;
    editButton.addEventListener("click", () => {
      editingMenuId = menu.id;
      menuNameInput.value = menu.name;
      menuMealTypeInput.value = menu.mealType || "";
      menuAllergensInput.value = (menu.allergens || []).join(", ");
      menuInformationComplete.checked =
        menu.isInformationComplete;
      addMenuButton.textContent = "수정 적용";
      cancelMenuEditButton.hidden = false;
      analysisStatus.textContent =
        "메뉴를 수정 중입니다. 적용한 뒤 저장 또는 검토 완료로 저장해 주세요.";
      updateAnalysisControls();
      menuNameInput.focus();
    });
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "button-secondary";
    removeButton.textContent = "삭제";
    removeButton.setAttribute("aria-label", `${menu.name} 메뉴 삭제`);
    removeButton.disabled = isSavingMealSheet || isAnalyzing;
    removeButton.addEventListener("click", () => {
      menuItems = menuItems.filter((item) => item.id !== menu.id);
      if (editingMenuId === menu.id) {
        resetMenuEditor();
      }
      markMealSheetDirty();
      renderMenuItems();
    });
    actions.append(editButton, removeButton);
    header.append(name, actions);

    const label = document.createElement("p");
    label.textContent = "알레르기 표시 번호와 항목";
    const tags = document.createElement("div");
    renderAllergenTags(tags, menu.allergens);
    const details = document.createElement("p");
    details.textContent = menu.isInformationComplete
      ? "표시 확인 완료"
      : "표시 추가 확인 필요";
    const mealType = document.createElement("span");
    mealType.className = "meal-type-label";
    mealType.textContent = `식사 구분 · ${{
      morning_snack: "오전 간식",
      lunch: "점심",
      afternoon_snack: "오후 간식",
    }[menu.mealType] || "미분류"}`;
    item.append(header, mealType, label, tags, details);
    menuList.append(item);
  }

  updateAnalysisControls();
}

function renderAnalysisResults(payload) {
  const validStatuses = new Set([
    "MATCH",
    "CHECK_NEEDED",
    "NOT_IDENTIFIED",
  ]);
  if (
    !Array.isArray(payload.results) ||
    payload.results.some(
      (result) =>
        !result ||
        typeof result !== "object" ||
        typeof result.menu_id !== "string" ||
        typeof result.menu_name !== "string" ||
        !validStatuses.has(result.status) ||
        !Array.isArray(result.matched_allergens) ||
        !Array.isArray(result.evidence) ||
        result.matched_allergens.some((item) => typeof item !== "string") ||
        result.evidence.some((item) => typeof item !== "string") ||
        typeof result.reason !== "string",
    ) ||
    typeof payload.disclaimer !== "string"
  ) {
    throw new Error("비교 결과 형식이 올바르지 않습니다.");
  }

  analysisResults.replaceChildren();
  const list = document.createElement("ul");
  list.className = "result-list";
  const statusLabels = {
    MATCH: "일치 항목 확인",
    CHECK_NEEDED: "추가 확인 필요",
    NOT_IDENTIFIED: "일치 표시 미확인",
  };
  const statusClasses = {
    MATCH: "match",
    CHECK_NEEDED: "check-needed",
    NOT_IDENTIFIED: "not-identified",
  };

  for (const result of payload.results) {
    const item = document.createElement("li");
    item.className = "result-item";
    const header = document.createElement("div");
    header.className = "result-item-header";
    const name = document.createElement("strong");
    name.textContent = result.menu_name || "이름 없는 메뉴";
    const status = document.createElement("span");
    status.className = `result-status ${statusClasses[result.status]}`;
    status.textContent = statusLabels[result.status];
    header.append(name, status);

    const matches = document.createElement("p");
    matches.textContent = result.matched_allergens.length
      ? `일치 항목: ${result.matched_allergens.join(", ")}`
      : "일치 항목: 없음";
    const evidence = document.createElement("p");
    evidence.textContent = result.evidence.length
      ? `확인한 표시: ${result.evidence.join(", ")}`
      : "확인한 표시: 없음";
    const reason = document.createElement("p");
    reason.textContent = result.reason;
    item.append(header, matches, evidence, reason);
    list.append(item);
  }

  analysisResults.append(list);
  analysisDisclaimer.textContent = payload.disclaimer;
  analysisDisclaimer.hidden = false;
}

async function requestJson(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  let payload;

  try {
    payload = await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error("서버 응답 형식이 올바르지 않습니다.");
    }
    throw error;
  }

  if (
    payload === null ||
    typeof payload !== "object" ||
    Array.isArray(payload)
  ) {
    throw new Error("서버 응답 형식이 올바르지 않습니다.");
  }

  if (!response.ok) {
    const detail = typeof payload.detail === "string"
      ? payload.detail
      : "요청한 정보를 처리하지 못했습니다.";
    const error = new Error(`${detail} (HTTP ${response.status})`);
    error.status = response.status;
    throw error;
  }

  return payload;
}

function getLocalDateString(date = new Date()) {
  const localDate = new Date(
    date.getTime() - date.getTimezoneOffset() * 60000,
  );
  return localDate.toISOString().slice(0, 10);
}

async function loadDateMealSheet(dateValue) {
  selectedDate = dateValue;
  mealDateInput.value = dateValue;
  mealMonthInput.value = dateValue.slice(0, 7);
  isMealSheetLoaded = false;
  isMealSheetReviewed = false;
  isMealSheetDirty = false;
  menuItems = [];
  resetMenuEditor();
  renderMenuItems();
  analysisResults.replaceChildren();
  analysisResultsStatus.textContent = "";
  analysisDisclaimer.hidden = true;
  resultsHeading.textContent = "알레르기 비교 결과";
  resultsDescription.textContent =
    "선택한 날짜의 검토 완료 메뉴만 비교합니다.";
  currentDateStatus = "NO_DATA";
  updateSelectedDateStatus("날짜별 급식표 정보를 불러오는 중입니다.");
  updateAnalysisControls();

  const mealSheet = await requestJson(
    `/api/meal-sheets/${encodeURIComponent(dateValue)}`,
  );
  if (!isValidDateMealSheet(mealSheet, dateValue)) {
    throw new Error("날짜별 급식표 응답 형식을 확인할 수 없습니다.");
  }

  currentDateStatus = mealSheet.status;
  menuItems = mealSheet.menus.map((menu) => ({
    id: menu.id,
    name: menu.name,
    allergens: menu.allergens,
    isInformationComplete: menu.is_information_complete,
    mealType: menu.meal_type,
  }));
  isMealSheetReviewed = mealSheet.status === "REVIEWED";
  isMealSheetLoaded = true;
  renderMenuItems();
  updateSelectedDateStatus();
  savedSheetAvailability.textContent =
    `${dateValue} · ${getDateStatusLabel(mealSheet.status)}`;
  analysisStatus.textContent = {
    NO_DATA: "이 날짜에 메뉴를 입력하거나 급식 없음 상태를 저장할 수 있습니다.",
    DRAFT: "저장된 초안입니다. 내용을 확인한 뒤 검토 완료로 저장해 주세요.",
    REVIEWED: "검토 완료된 메뉴를 불러왔습니다. 선택한 날짜를 비교할 수 있습니다.",
    NO_MEAL: "급식 없음으로 확인된 날짜입니다. 메뉴를 추가하면 검토 전 상태가 됩니다.",
  }[mealSheet.status];
  setMealSheetMode();
  updateAnalysisControls();
}

function renderMonthCalendar(month, sheets) {
  monthCalendar.replaceChildren();
  const weekdays = ["일", "월", "화", "수", "목", "금", "토"];
  for (const weekday of weekdays) {
    const heading = document.createElement("span");
    heading.className = "month-calendar-heading";
    heading.textContent = weekday;
    monthCalendar.append(heading);
  }

  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(year, monthNumber - 1, 1).getDay();
  const daysInMonth = new Date(year, monthNumber, 0).getDate();
  const sheetsByDate = new Map(
    sheets.map((sheet) => [sheet.date, sheet]),
  );
  for (let blank = 0; blank < firstWeekday; blank += 1) {
    const empty = document.createElement("span");
    empty.className = "calendar-empty";
    empty.setAttribute("aria-hidden", "true");
    monthCalendar.append(empty);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateValue = `${month}-${String(day).padStart(2, "0")}`;
    const sheet = sheetsByDate.get(dateValue);
    const status = sheet ? sheet.status : "NO_DATA";
    const button = document.createElement("button");
    button.type = "button";
    button.className = `calendar-day status-${status}`;
    button.setAttribute(
      "aria-label",
      `${dateValue}, ${getDateStatusLabel(status)}`,
    );
    if (dateValue === selectedDate) {
      button.setAttribute("aria-current", "date");
    }
    const number = document.createElement("span");
    number.className = "day-number";
    number.textContent = String(day);
    const label = document.createElement("span");
    label.className = "day-status";
    label.textContent = getDateStatusLabel(status);
    button.append(number, label);
    button.addEventListener("click", async () => {
      if (!confirmDateNavigation()) {
        return;
      }
      reviewReturnStep = "monthly";
      try {
        await loadDateMealSheet(dateValue);
        showStep("review");
      } catch (error) {
        monthStatus.textContent = `날짜 정보를 불러오지 못했습니다. ${error.message}`;
      }
    });
    monthCalendar.append(button);
  }
}

async function loadMonthCalendar(month) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) {
    monthStatus.textContent = "조회할 월을 선택해 주세요.";
    return;
  }
  monthStatus.textContent = "날짜별 저장 상태를 불러오는 중입니다.";
  try {
    const payload = await requestJson(
      `/api/meal-sheets?month=${encodeURIComponent(month)}`,
    );
    if (
      payload.month !== month ||
      !Array.isArray(payload.sheets) ||
      payload.sheets.some(
        (sheet) =>
          !sheet ||
          typeof sheet.date !== "string" ||
          !sheet.date.startsWith(`${month}-`) ||
          !isValidDateMealSheet(sheet, sheet.date) ||
          sheet.status === "NO_DATA",
      )
    ) {
      throw new Error("월별 급식표 응답 형식을 확인할 수 없습니다.");
    }
    renderMonthCalendar(month, payload.sheets);
    monthStatus.textContent = payload.sheets.length
      ? `${month} · 저장된 날짜 ${payload.sheets.length}개`
      : `${month} · 저장된 날짜가 없습니다. 날짜를 선택해 메뉴를 입력하세요.`;
  } catch (error) {
    monthCalendar.replaceChildren();
    monthStatus.textContent = `월별 급식표를 불러오지 못했습니다. ${error.message}`;
  }
}

async function loadUnassignedLegacyMealSheet() {
  const payload = await requestJson("/api/meal-sheets/unassigned");
  const normalizedMenus = Array.isArray(payload.menus)
    ? payload.menus.map((menu) => ({
        id: menu.id,
        name: menu.name,
        allergens: menu.allergens,
        is_information_complete: menu.is_information_complete,
      }))
    : [];
  if (
    !["NO_DATA", "UNASSIGNED"].includes(payload.status) ||
    payload.date !== null ||
    payload.source !== "manual" ||
    typeof payload.reviewed !== "boolean" ||
    !isValidMealSheet({
      source: payload.source,
      reviewed: payload.reviewed,
      menus: normalizedMenus,
    })
  ) {
    throw new Error("날짜 미지정 급식표 응답 형식을 확인할 수 없습니다.");
  }

  legacyMealSheet = payload.status === "UNASSIGNED"
    ? {
        reviewed: payload.reviewed,
        menus: normalizedMenus,
      }
    : null;
  legacyCard.hidden = !legacyMealSheet;
  if (legacyMealSheet) {
    legacySummary.textContent =
      `이전 메뉴 ${normalizedMenus.length}개가 날짜 없이 보존되어 있습니다. 원본 파일은 유지되며 날짜를 자동 지정하지 않았습니다.`;
  }
  updateAnalysisControls();
}

function showLoadError(error) {
  const message = error instanceof TypeError
    ? "API 서버에 연결할 수 없습니다. README의 실행 안내를 확인해 주세요."
    : `정보를 불러오지 못했습니다. ${error.message}`;
  saveStatus.textContent = message;
  retryButton.hidden = false;
}

async function loadProfile() {
  isLoaded = false;
  isMealSheetLoaded = false;
  isMealSheetReviewed = false;
  isMealSheetDirty = false;
  menuItems = [];
  editingMenuId = null;
  legacyMealSheet = null;
  legacyCard.hidden = true;
  fieldset.disabled = true;
  saveButton.disabled = true;
  retryButton.hidden = true;
  saveStatus.textContent = "저장된 정보를 불러오는 중입니다.";
  analysisResults.replaceChildren();
  analysisDisclaimer.hidden = true;
  analysisResultsStatus.textContent = "";
  savedSheetAvailability.textContent = "저장 상태 확인 중";
  menuList.replaceChildren();
  menuForm.reset();
  addMenuButton.textContent = "메뉴 추가";
  cancelMenuEditButton.hidden = true;
  analysisStatus.textContent = "저장된 급식표 정보를 불러오는 중입니다.";
  updateAnalysisControls();

  try {
    const [allergens, profile] = await Promise.all([
      requestJson("/api/allergens"),
      requestJson("/api/profile"),
    ]);

    if (
      !Array.isArray(allergens.items) ||
      allergens.items.some((item) => typeof item !== "string") ||
      !isValidNumberedAllergenItems(
        allergens.numbered_items,
        allergens.items,
      ) ||
      profile.id !== "demo-child" ||
      !Array.isArray(profile.allergies) ||
      profile.allergies.some((item) => typeof item !== "string") ||
      profile.allergies.some((item) => !allergens.items.includes(item))
    ) {
      throw new Error("알레르기 정보 응답을 확인할 수 없습니다.");
    }

    allergyOptions = allergens.items;
    allergyNumberToName = new Map(
      allergens.numbered_items.map(({ number, name }) => [number, name]),
    );
    allergyNameToNumber = new Map(
      allergens.numbered_items.map(({ number, name }) => [name, number]),
    );
    renderOptions(allergyOptions, profile.allergies);
    renderAllergyNumberReference(allergens.numbered_items);
    savedAllergies = getSelectedAllergies();
    fieldset.disabled = false;
    isLoaded = true;
    updateFormState();
    analysisStatus.textContent = savedAllergies.length
      ? "저장된 알레르기 정보를 사용할 수 있습니다."
      : "비교하려면 먼저 알레르기 정보를 등록해 주세요.";
  } catch (error) {
    showLoadError(error);
    updateAnalysisControls();
    return;
  }

  selectedDate = getLocalDateString();
  mealDateInput.value = selectedDate;
  mealMonthInput.value = selectedDate.slice(0, 7);
  try {
    await loadDateMealSheet(selectedDate);
    await loadUnassignedLegacyMealSheet();
    await loadMonthCalendar(mealMonthInput.value);
  } catch (error) {
    savedSheetAvailability.textContent = "저장 상태 확인 실패";
    analysisStatus.textContent = error instanceof TypeError
      ? "급식표 API에 연결할 수 없습니다. 서버 상태를 확인해 주세요."
      : `날짜별 급식표를 불러오지 못했습니다. ${error.message}`;
    retryButton.hidden = false;
    updateAnalysisControls();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!isLoaded || isSaving) {
    return;
  }

  const allergies = getSelectedAllergies();
  isSaving = true;
  fieldset.disabled = true;
  saveButton.disabled = true;
  saveStatus.textContent = "알레르기 정보를 저장하고 있습니다.";
  let resultMessage;

  try {
    const profile = await requestJson("/api/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ allergies }),
    });

    if (
      profile.id !== "demo-child" ||
      !Array.isArray(profile.allergies) ||
      profile.allergies.some((item, index) => item !== allergies[index]) ||
      profile.allergies.length !== allergies.length
    ) {
      throw new Error("저장 결과를 확인할 수 없습니다.");
    }

    savedAllergies = allergies;
    resultMessage = "저장했습니다. 새로고침 후에도 선택 내용이 유지됩니다.";
  } catch (error) {
    resultMessage = error instanceof TypeError
      ? "API 서버에 연결할 수 없어 저장하지 못했습니다."
      : `저장하지 못했습니다. ${error.message}`;
  } finally {
    isSaving = false;
    fieldset.disabled = !isLoaded;
    updateFormState(resultMessage);
  }
});

menuNameInput.addEventListener("input", updateAnalysisControls);

menuForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const name = menuNameInput.value.trim();
  if (
    !isLoaded ||
    !isMealSheetLoaded ||
    !name ||
    isSavingMealSheet ||
    isAnalyzing
  ) {
    return;
  }

  const updatedMenu = {
    id: editingMenuId || crypto.randomUUID(),
    name,
    mealType: menuMealTypeInput.value || null,
    allergens: menuAllergensInput.value
      .split(",")
      .map((allergen) => allergen.trim())
      .filter(Boolean)
      .map(normalizeAllergenEntry),
    isInformationComplete: menuInformationComplete.checked,
  };
  if (editingMenuId) {
    menuItems = menuItems.map((menu) =>
      menu.id === editingMenuId ? updatedMenu : menu
    );
  } else {
    menuItems.push(updatedMenu);
  }
  resetMenuEditor();
  markMealSheetDirty();
  renderMenuItems();
});

cancelMenuEditButton.addEventListener("click", () => {
  resetMenuEditor();
  analysisStatus.textContent =
    isMealSheetReviewed
      ? "검토 완료된 급식표입니다."
      : "메뉴 수정을 취소했습니다.";
});

async function saveMealSheet(status) {
  if (
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isAnalyzing ||
    editingMenuId !== null
  ) {
    return;
  }
  if (
    status === "REVIEWED" &&
    (menuItems.length === 0 ||
      menuItems.some((menu) => !menu.name.trim()))
  ) {
    analysisStatus.textContent =
      "메뉴명을 확인하고 메뉴를 하나 이상 추가해 주세요.";
    return;
  }
  if (
    status === "NO_MEAL" &&
    hasPendingDateEdits() &&
    !window.confirm("현재 메뉴를 지우고 이 날짜를 급식 없음으로 저장할까요?")
  ) {
    return;
  }

  const submittedMenus = (status === "NO_MEAL" ? [] : menuItems).map((menu) => ({
    id: menu.id,
    name: menu.name,
    allergens: menu.allergens,
    is_information_complete: menu.isInformationComplete,
    meal_type: menu.mealType,
  }));
  isSavingMealSheet = true;
  analysisStatus.textContent = {
    DRAFT: "급식표 초안을 저장하고 있습니다.",
    REVIEWED: "검토 완료한 급식표를 저장하고 있습니다.",
    NO_MEAL: "급식 없음 상태를 저장하고 있습니다.",
  }[status];
  updateAnalysisControls();

  try {
    const sendSaveRequest = (replaceExisting) =>
      requestJson(`/api/meal-sheets/${encodeURIComponent(selectedDate)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status,
          menus: submittedMenus,
          replace_existing: replaceExisting,
        }),
      });
    let savedSheet;
    try {
      savedSheet = await sendSaveRequest(false);
    } catch (error) {
      if (error.status !== 409) {
        throw error;
      }
      if (
        !window.confirm(
          `${selectedDate}에 저장된 급식표가 있습니다. 기존 데이터를 덮어쓸까요?`,
        )
      ) {
        analysisStatus.textContent =
          "덮어쓰기를 취소했습니다. 기존 저장 데이터는 그대로 유지됩니다.";
        return;
      }
      savedSheet = await sendSaveRequest(true);
    }

    if (!isValidDateMealSheet(savedSheet, selectedDate) ||
        savedSheet.status !== status ||
        JSON.stringify(savedSheet.menus) !== JSON.stringify(submittedMenus)) {
      throw new Error("저장 결과를 확인할 수 없습니다.");
    }

    currentDateStatus = savedSheet.status;
    menuItems = savedSheet.menus.map((menu) => ({
      id: menu.id,
      name: menu.name,
      allergens: menu.allergens,
      isInformationComplete: menu.is_information_complete,
      mealType: menu.meal_type,
    }));
    if (savedSheet.status === "NO_MEAL") {
      resetMenuEditor();
    }
    isMealSheetReviewed = savedSheet.status === "REVIEWED";
    isMealSheetDirty = false;
    savedSheetAvailability.textContent =
      `${selectedDate} · ${getDateStatusLabel(savedSheet.status)}`;
    analysisStatus.textContent = {
      DRAFT: "검토 전 상태로 저장했습니다.",
      REVIEWED: "검토 완료로 저장했습니다. 선택한 날짜를 비교할 수 있습니다.",
      NO_MEAL: "사용자가 확인한 급식 없음 상태로 저장했습니다.",
    }[savedSheet.status];
    updateSelectedDateStatus();
    await loadMonthCalendar(mealMonthInput.value);
  } catch (error) {
    analysisStatus.textContent = error instanceof TypeError
      ? "급식표 API에 연결할 수 없어 저장하지 못했습니다."
      : `급식표를 저장하지 못했습니다. ${error.message}`;
  } finally {
    isSavingMealSheet = false;
    renderMenuItems();
  }
}

saveMealSheetButton.addEventListener("click", () => {
  saveMealSheet("DRAFT");
});
confirmMealSheetButton.addEventListener("click", () => {
  saveMealSheet("REVIEWED");
});
noMealButton.addEventListener("click", () => {
  saveMealSheet("NO_MEAL");
});

copyLegacyButton.addEventListener("click", () => {
  if (!legacyMealSheet || !isMealSheetLoaded || isSavingMealSheet) {
    return;
  }
  if (
    (menuItems.length > 0 || hasPendingDateEdits()) &&
    !window.confirm("현재 편집 중인 메뉴를 보존된 이전 메뉴로 바꿀까요?")
  ) {
    return;
  }
  menuItems = legacyMealSheet.menus.map((menu) => ({
    id: crypto.randomUUID(),
    name: menu.name,
    allergens: menu.allergens,
    isInformationComplete: menu.is_information_complete,
    mealType: null,
  }));
  resetMenuEditor();
  markMealSheetDirty();
  renderMenuItems();
  analysisStatus.textContent =
    `날짜 미지정 메뉴를 ${selectedDate}의 초안으로 복사했습니다. 확인 후 저장해 주세요.`;
});

analyzeLegacyButton.addEventListener("click", async () => {
  if (
    !isLoaded ||
    isAnalyzing ||
    isSavingMealSheet ||
    !legacyMealSheet ||
    !legacyMealSheet.reviewed ||
    savedAllergies.length === 0
  ) {
    return;
  }

  isAnalyzing = true;
  analysisStatus.textContent = "날짜 미지정 이전 급식표를 기존 방식으로 비교하고 있습니다.";
  analysisResults.replaceChildren();
  analysisDisclaimer.hidden = true;
  updateAnalysisControls();

  try {
    const payload = await requestJson("/api/analyze", {
      method: "POST",
    });

    renderAnalysisResults(payload);
    resultsHeading.textContent = "날짜 미지정 급식표의 기존 비교";
    resultsDescription.textContent =
      "날짜가 배정되지 않은 기존 정보에 대한 비교 결과이며, 선택 날짜의 비교가 아닙니다.";
    analysisStatus.textContent =
      `날짜 미지정 메뉴 ${payload.results.length}개의 기존 비교 결과입니다.`;
    analysisResultsStatus.textContent = analysisStatus.textContent;
    showStep("results");
  } catch (error) {
    analysisStatus.textContent = error instanceof TypeError
      ? "API 서버에 연결할 수 없어 비교하지 못했습니다."
      : `비교하지 못했습니다. ${error.message}`;
  } finally {
    isAnalyzing = false;
    updateAnalysisControls();
  }
});

analyzeDateButton.addEventListener("click", async () => {
  if (
    !isLoaded ||
    !isMealSheetLoaded ||
    currentDateStatus !== "REVIEWED" ||
    !isMealSheetReviewed ||
    isAnalyzing ||
    isSavingMealSheet ||
    isMealSheetDirty ||
    editingMenuId !== null ||
    savedAllergies.length === 0
  ) {
    analysisStatus.textContent = {
      NO_DATA: "이 날짜에는 저장된 급식 정보가 없습니다.",
      DRAFT: "비교하려면 이 날짜의 메뉴를 검토 완료로 저장해 주세요.",
      NO_MEAL: "급식 없음으로 확인된 날짜에는 비교할 메뉴가 없습니다.",
    }[currentDateStatus] ||
      "저장된 알레르기 정보를 확인하고 날짜별 메뉴를 검토 완료로 저장해 주세요.";
    return;
  }

  const requestedDate = selectedDate;
  isAnalyzing = true;
  analysisStatus.textContent =
    `${requestedDate}의 검토 완료 메뉴를 비교하고 있습니다.`;
  analysisResults.replaceChildren();
  analysisResultsStatus.textContent = "";
  analysisDisclaimer.hidden = true;
  updateAnalysisControls();

  try {
    const payload = await requestJson(
      `/api/meal-sheets/${encodeURIComponent(requestedDate)}/analyze`,
      { method: "POST" },
    );
    if (payload.date !== requestedDate) {
      throw new Error("선택 날짜와 비교 결과의 날짜가 일치하지 않습니다.");
    }
    if (selectedDate !== requestedDate) {
      return;
    }

    renderAnalysisResults(payload);
    resultsHeading.textContent = `${requestedDate} 알레르기 비교 결과`;
    resultsDescription.textContent =
      `${requestedDate}에 검토 완료로 저장한 하루치 전체 메뉴의 비교 결과입니다.`;
    analysisStatus.textContent =
      `${requestedDate} · 메뉴 ${payload.results.length}개의 비교 결과입니다.`;
    analysisResultsStatus.textContent = analysisStatus.textContent;
    showStep("results");
  } catch (error) {
    if (selectedDate !== requestedDate) {
      return;
    }
    analysisStatus.textContent = error instanceof TypeError
      ? "API 서버에 연결할 수 없어 비교하지 못했습니다."
      : error.status === 409
        ? error.message.replace(/ \(HTTP 409\)$/, "")
        : `비교하지 못했습니다. ${error.message}`;
  } finally {
    isAnalyzing = false;
    updateAnalysisControls();
  }
});

document.querySelector("#brand-home").addEventListener("click", (event) => {
  event.preventDefault();
  showStep("home");
});
document.querySelector("#home-nav-button").addEventListener("click", () => {
  showStep("home");
});
document.querySelector("#profile-nav-button").addEventListener("click", () => {
  showStep("profile");
});
document.querySelector("#meal-nav-button").addEventListener("click", () => {
  showStep("type");
});
document.querySelector("#start-button").addEventListener("click", () => {
  showStep("profile");
});
document.querySelector("#header-start-button").addEventListener("click", () => {
  showStep("profile");
});
document.querySelector("#profile-home-button").addEventListener("click", () => {
  showStep("home");
});
document.querySelector("#profile-next-button").addEventListener("click", () => {
  showStep("type");
});
document.querySelector("#type-back-button").addEventListener("click", () => {
  showStep("profile");
});
document.querySelector("#choose-daily-button").addEventListener("click", () => {
  reviewReturnStep = "type";
  setMealSheetMode();
  showStep("review");
});
document.querySelector("#choose-monthly-button").addEventListener("click", () => {
  mealMonthInput.value = selectedDate
    ? selectedDate.slice(0, 7)
    : getLocalDateString().slice(0, 7);
  loadMonthCalendar(mealMonthInput.value);
  showStep("monthly");
});
document.querySelector("#choose-saved-button").addEventListener("click", () => {
  mealMonthInput.value = selectedDate.slice(0, 7);
  loadMonthCalendar(mealMonthInput.value);
  showStep("monthly");
});
document.querySelector("#monthly-back-button").addEventListener("click", () => {
  showStep("type");
});
document.querySelector("#review-back-button").addEventListener("click", () => {
  showStep(reviewReturnStep);
});
document.querySelector("#result-edit-button").addEventListener("click", () => {
  showStep("review");
});
document.querySelector("#result-edit-button-bottom").addEventListener("click", () => {
  showStep("review");
});
document.querySelector("#result-profile-button").addEventListener("click", () => {
  showStep("profile");
});
mealDateInput.addEventListener("change", async () => {
  const nextDate = mealDateInput.value;
  if (!nextDate) {
    mealDateInput.value = selectedDate;
    return;
  }
  if (!confirmDateNavigation()) {
    mealDateInput.value = selectedDate;
    return;
  }
  reviewReturnStep = "type";
  try {
    await loadDateMealSheet(nextDate);
    await loadMonthCalendar(mealMonthInput.value);
  } catch (error) {
    analysisStatus.textContent =
      `날짜별 급식표를 불러오지 못했습니다. ${error.message}`;
  }
});
mealMonthInput.addEventListener("change", () => {
  loadMonthCalendar(mealMonthInput.value);
});

retryButton.addEventListener("click", loadProfile);
loadProfile();
