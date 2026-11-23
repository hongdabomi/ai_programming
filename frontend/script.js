const API_BASE_URL = "http://127.0.0.1:8000";
const IMAGE_EXTRACTION_TIMEOUT_MS = 120_000;
const form = document.querySelector("#profile-form");
const fieldset = document.querySelector("#allergy-fieldset");
const optionsContainer = document.querySelector("#allergy-options");
const saveButton = document.querySelector("#save-button");
const profileNextButton = document.querySelector("#profile-next-button");
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
const dailyUploadDateInput = document.querySelector("#daily-upload-date-input");
const mealMonthInput = document.querySelector("#meal-month-input");
const monthlyTargetDateInput = document.querySelector(
  "#monthly-target-date-input",
);
const dailyImageForm = document.querySelector("#daily-image-form");
const dailyImageFieldset = document.querySelector("#daily-image-fieldset");
const dailyImageInput = document.querySelector("#daily-image-input");
const extractDailyButton = document.querySelector("#extract-daily-button");
const dailyExtractionStatus = document.querySelector("#daily-extraction-status");
const dailyExtractionProgress = document.querySelector(
  "#daily-extraction-progress",
);
const dailyExtractionResults = document.querySelector("#daily-extraction-results");
const monthlyImageForm = document.querySelector("#monthly-image-form");
const monthlyImageFieldset = document.querySelector("#monthly-image-fieldset");
const monthlyImageInput = document.querySelector("#monthly-image-input");
const extractMonthlyButton = document.querySelector("#extract-monthly-button");
const monthlyExtractionStatus = document.querySelector(
  "#monthly-extraction-status",
);
const monthlyExtractionProgress = document.querySelector(
  "#monthly-extraction-progress",
);
const monthlyExtractionResults = document.querySelector(
  "#monthly-extraction-results",
);
const monthCalendar = document.querySelector("#month-calendar");
const monthStatus = document.querySelector("#month-status");
const selectedDateBadge = document.querySelector("#selected-date-badge");
const selectedDateStatus = document.querySelector("#selected-date-status");
const legacyCard = document.querySelector("#unassigned-legacy-card");
const legacySummary = document.querySelector("#legacy-meal-sheet-summary");
const copyLegacyButton = document.querySelector("#copy-legacy-button");
const analysisResults = document.querySelector("#analysis-results");
const resultsHeading = document.querySelector("#results-heading");
const resultsDescription = document.querySelector("#results-description");
const contactRequestPanel = document.querySelector("#contact-request-panel");
const contactRequestText = document.querySelector("#contact-request-text");
const copyContactRequestStatus = document.querySelector("#copy-contact-request-status");
const progressWrap = document.querySelector("#progress-wrap");
const screens = {
  home: document.querySelector("#home-screen"),
  profile: document.querySelector("#profile-screen"),
  type: document.querySelector("#meal-type-screen"),
  dailyUpload: document.querySelector("#daily-upload-screen"),
  monthly: document.querySelector("#monthly-screen"),
  monthlyDate: document.querySelector("#monthly-date-screen"),
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
let isExtractingImage = false;
let selectedDate = "";
let currentDateStatus = "NO_DATA";
let legacyMealSheet = null;
let reviewReturnStep = "type";
let dateSelectionMode = "uploaded";
let monthlyUploadedFile = null;
let extractionDrafts = { daily: null, monthly: null };
const savedExtractionCandidateIds = new Set();

function showStep(step) {
  if (step === "review") {
    setMealSheetMode();
    document.querySelector("#review-back-button").textContent =
      reviewReturnStep === "dailyUpload"
        ? "← 하루 급식표 업로드"
        : reviewReturnStep === "monthlyDate"
          ? "← 날짜 선택"
          : "← 급식표 유형";
  }
  for (const [name, screen] of Object.entries(screens)) {
    screen.hidden = name !== step;
  }

  progressWrap.hidden = step === "home";
  const progressStep = ["dailyUpload", "monthly", "monthlyDate"].includes(step)
    ? "type"
    : step;
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
  title.textContent = reviewReturnStep === "monthlyDate"
    ? "선택한 날짜의 급식표 인식 결과입니다"
    : "하루 급식표 인식 결과입니다";
  description.textContent = selectedDate
    ? `${selectedDate} 메뉴와 알레르기 표시를 확인하고 필요한 내용을 수정해 주세요.`
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
  const tag = document.createElement("span");
  tag.className = "allergen-tag";
  if (allergens === null) {
    tag.textContent = "알레르기 표시를 읽지 못함";
    tag.classList.add("unknown");
  } else if (allergens.length === 0) {
    tag.textContent = "등록 알레르기 표시 없음";
  } else {
    const selectedNumbers = new Set(
      savedAllergies.map((allergy) => allergyNameToNumber.get(allergy)).filter(Boolean),
    );
    const matched = new Set();
    let hasUnclearMarking = false;
    for (const label of allergens) {
      const mapped = resolveNumberedAllergen(label);
      if (mapped) {
        if (savedAllergies.includes(mapped.name)) matched.add(mapped.name);
        continue;
      }
      const marking = label.replace(/^범례 확인 필요:\s*/, "").trim();
      if (/^[\u2460-\u2472]+$/u.test(marking)) {
        for (const character of marking) {
          const number = character.codePointAt(0) - 0x2460 + 1;
          if (selectedNumbers.has(number)) {
            matched.add(allergyNumberToName.get(number));
          }
        }
      } else {
        hasUnclearMarking = true;
      }
    }
    if (matched.size > 0) {
      tag.textContent = `등록 알레르기 표시 후보: ${Array.from(matched).join(", ")}`;
    } else if (hasUnclearMarking) {
      tag.textContent = "등록 알레르기 여부 확인 필요";
      tag.classList.add("unknown");
    } else {
      tag.textContent = "등록 알레르기 표시 없음";
    }
  }
  container.append(tag);
}

function isValidIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value;
}

function isValidImageExtraction(value, scope, selectedDate) {
  const validMealTypes = new Set([
    "morning_snack",
    "lunch",
    "afternoon_snack",
  ]);
  return (
    value !== null &&
    typeof value === "object" &&
    value.source === "uploaded-image" &&
    value.reviewed === false &&
    value.scope === scope &&
    value.selected_date === selectedDate &&
    isValidIsoDate(value.selected_date) &&
    (value.reference_date === null ||
      isValidIsoDate(value.reference_date)) &&
    (value.reference_month === null ||
      /^\d{4}-(0[1-9]|1[0-2])$/.test(value.reference_month)) &&
    ["NO_LEGEND", "VERIFIED", "NEEDS_CONFIRMATION"].includes(
      value.legend_status,
    ) &&
    Array.isArray(value.legend_warnings) &&
    value.legend_warnings.every((warning) => typeof warning === "string") &&
    Array.isArray(value.extraction_warnings) &&
    value.extraction_warnings.every((warning) => typeof warning === "string") &&
    Array.isArray(value.menus) &&
    value.menus.every(
      (menu) =>
        menu &&
        typeof menu.id === "string" &&
        typeof menu.name === "string" &&
        (menu.date === null || isValidIsoDate(menu.date)) &&
        (menu.date_text === null || typeof menu.date_text === "string") &&
        typeof menu.date_requires_confirmation === "boolean" &&
        (menu.meal_type === null || validMealTypes.has(menu.meal_type)) &&
        (menu.allergen_marking === null ||
          typeof menu.allergen_marking === "string") &&
        Array.isArray(menu.allergen_numbers) &&
        menu.allergen_numbers.every(Number.isInteger) &&
        (menu.allergens === null ||
          (Array.isArray(menu.allergens) &&
            menu.allergens.every((item) => typeof item === "string"))) &&
        Array.isArray(menu.warnings) &&
        menu.warnings.every((warning) => typeof warning === "string") &&
        menu.is_information_complete === false,
    ) &&
    new Set(value.menus.map((menu) => menu.id)).size === value.menus.length
  );
}

function renderExtractionResults(scope) {
  const draft = extractionDrafts[scope];
  const container = scope === "daily"
    ? dailyExtractionResults
    : monthlyExtractionResults;
  container.replaceChildren();
  container.hidden = !draft;
  if (!draft) {
    return;
  }

  const summary = document.createElement("div");
  summary.className = "notice";
  const summaryTitle = document.createElement("strong");
  summaryTitle.textContent = "급식표에서 읽은 메뉴";
  const summaryText = document.createElement("p");
  summaryText.textContent =
    `선택한 날짜: ${draft.selected_date}. 등록한 ${savedAllergies.join(", ")} 표시를 중심으로 확인해 주세요. 메뉴 옆 숫자는 급식표 원본의 알레르기 식품 번호예요.`;
  summary.append(summaryTitle, summaryText);
  if (draft.extraction_warnings.length) {
    const extractionWarnings = document.createElement("ul");
    for (const warning of draft.extraction_warnings) {
      const item = document.createElement("li");
      item.textContent = warning;
      extractionWarnings.append(item);
    }
    summary.append(extractionWarnings);
  }
  container.append(summary);

  if (draft.menus.length === 0) {
    const empty = document.createElement("p");
    empty.className = "help-text";
    empty.textContent =
      "선택한 날짜에 연결된 메뉴를 확인하지 못했습니다. 급식 없음으로 단정하지 말고 날짜와 이미지를 확인하거나 메뉴를 직접 입력해 주세요.";
    container.append(empty);
    return;
  }

  const importAllButton = document.createElement("button");
  importAllButton.className = "button-primary";
  importAllButton.type = "button";
  const updateImportAllButton = () => {
    const available = draft.menus.filter(
      (menu) =>
        menu.assignedDate === draft.selected_date &&
        !savedExtractionCandidateIds.has(menu.id) &&
        !menuItems.some((item) => item.sourceCandidateId === menu.id),
    );
    importAllButton.textContent =
      `선택 날짜 후보 ${available.length}개를 한 번에 검토하기`;
    importAllButton.disabled = available.length === 0 || isExtractingImage;
  };
  updateImportAllButton();
  importAllButton.addEventListener("click", () => {
    importExtractedCandidates(scope);
  });
  container.append(importAllButton);

  const datedGroup = document.createElement("section");
  datedGroup.className = "extraction-group";
  const datedHeading = document.createElement("h3");
  datedHeading.textContent = "이미지에서 날짜를 인식한 메뉴";
  const datedCards = document.createElement("div");
  datedCards.className = "extraction-group";
  datedGroup.append(datedHeading, datedCards);

  const unassignedGroup = document.createElement("section");
  unassignedGroup.className = "extraction-group";
  const unassignedHeading = document.createElement("h3");
  unassignedHeading.textContent = "날짜 미지정 후보";
  const unassignedCards = document.createElement("div");
  unassignedCards.className = "extraction-group";
  unassignedGroup.append(unassignedHeading, unassignedCards);

  for (const menu of draft.menus) {
    const selectedNumbers = new Set(
      savedAllergies.map((allergy) => allergyNameToNumber.get(allergy)).filter(Boolean),
    );
    const clearCircledMarking = menu.allergen_marking &&
      /^[\u2460-\u2472]+$/u.test(menu.allergen_marking.trim());
    const selectedMarkingNumbers = menu.allergen_numbers.filter(
      (number) => selectedNumbers.has(number),
    );
    const unrelatedMarking = clearCircledMarking &&
      selectedMarkingNumbers.length === 0;
    const card = document.createElement("article");
    card.className = "image-extraction-candidate";

    const header = document.createElement("div");
    header.className = "menu-item-header";
    const name = document.createElement("strong");
    name.textContent = menu.name || "읽기 어려운 메뉴명";
    const status = document.createElement("span");
    status.className = "badge";
    status.textContent = unrelatedMarking
      ? "등록 알레르기 표시 없음"
      : selectedMarkingNumbers.length > 0
        ? "등록 알레르기 표시 후보"
        : menu.allergen_marking ? "번호 확인 필요" : "표시 미인식";
    header.append(name, status);

    const sourceDate = document.createElement("p");
    sourceDate.className = "candidate-source";
    sourceDate.textContent = menu.date_text
      ? `이미지 날짜 표기: ${menu.date_text}`
      : "이미지에서 메뉴 날짜를 확인하지 못했습니다.";
    const sourceMarking = document.createElement("p");
    sourceMarking.className = "candidate-source";
    sourceMarking.textContent = menu.allergen_marking
      ? `급식표 원본의 알레르기 번호: ${menu.allergen_marking}`
      : "급식표의 알레르기 표시를 읽지 못했어요.";
    sourceMarking.hidden = Boolean(unrelatedMarking);

    const mappedNumbers = document.createElement("p");
    mappedNumbers.className = "candidate-source";
    mappedNumbers.textContent = selectedMarkingNumbers.length
      ? `등록 알레르기 번호 후보: ${selectedMarkingNumbers.map((number) =>
        `${number}. ${allergyNumberToName.get(number) || "확인 필요"}`
      ).join(" · ")}`
      : "";
    mappedNumbers.hidden = selectedMarkingNumbers.length === 0;

    const markingNote = document.createElement("p");
    markingNote.className = "candidate-marking-note";
    markingNote.textContent = unrelatedMarking
      ? `읽힌 원형 번호에는 등록한 ${savedAllergies.join(", ")} 항목이 없어요.`
      : selectedMarkingNumbers.length > 0
        ? `등록한 ${savedAllergies.join(", ")} 번호가 보입니다. 원본 급식표에서 확인해 주세요.`
        : menu.allergen_marking
          ? "번호를 정확히 읽지 못했어요. 원본 급식표를 확인해 주세요."
          : "원본에 표시가 없는지 확인해 주세요. 표시가 없으면 검토 화면에서 ‘표시 없음 확인’을 누를 수 있어요.";

    const dateLabel = document.createElement("label");
    dateLabel.className = "form-field";
    dateLabel.textContent = "저장할 날짜 선택 (이미지 날짜는 후보)";
    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.value = menu.assignedDate;
    dateLabel.append(dateInput);

    if (
      menu.date &&
      menu.date !== draft.selected_date
    ) {
      const mismatch = document.createElement("p");
      mismatch.className = "candidate-warnings";
      mismatch.textContent =
        "선택한 날짜와 이미지에서 읽은 날짜가 다릅니다. 저장 날짜를 확인해 주세요.";
      card.append(mismatch);
    } else if (!menu.date) {
      const unassigned = document.createElement("p");
      unassigned.className = "candidate-warnings";
      unassigned.textContent =
        "날짜 미지정 상태입니다. 직접 날짜를 선택해야 저장할 수 있습니다.";
      card.append(unassigned);
    }

    const importButton = document.createElement("button");
    importButton.className = "button-secondary";
    importButton.type = "button";
    const isInEditor = menuItems.some(
      (item) => item.sourceCandidateId === menu.id,
    );
    const alreadySaved = savedExtractionCandidateIds.has(menu.id);
    importButton.textContent = alreadySaved
      ? "저장 완료"
      : isInEditor
        ? "검토 화면에 있음"
        : "이 메뉴를 검토 화면에 가져오기";
    importButton.disabled =
      !isValidIsoDate(menu.assignedDate) ||
      isInEditor ||
      alreadySaved ||
      isExtractingImage;
    dateInput.disabled = isInEditor || alreadySaved || isExtractingImage;
    dateInput.addEventListener("change", () => {
      menu.assignedDate = dateInput.value;
      updateImportAllButton();
      importButton.disabled =
        !isValidIsoDate(menu.assignedDate) ||
        isInEditor ||
        alreadySaved ||
        isExtractingImage;
    });
    importButton.addEventListener("click", () => {
      importExtractedCandidate(scope, menu.id);
    });

    card.append(
      header,
      sourceDate,
      sourceMarking,
      mappedNumbers,
      markingNote,
      dateLabel,
      importButton,
    );
    (menu.date ? datedCards : unassignedCards).append(card);
  }

  if (datedCards.childElementCount) {
    container.append(datedGroup);
  }
  if (unassignedCards.childElementCount) {
    container.append(unassignedGroup);
  }
}

async function extractMealImage(scope) {
  const isDaily = scope === "daily";
  const input = isDaily ? dailyImageInput : monthlyImageInput;
  const status = isDaily ? dailyExtractionStatus : monthlyExtractionStatus;
  const progress = isDaily
    ? dailyExtractionProgress
    : monthlyExtractionProgress;
  const file = isDaily
    ? input.files && input.files[0]
    : monthlyUploadedFile || (input.files && input.files[0]);
  if (!file || isExtractingImage) {
    return;
  }
  if (file.size === 0) {
    status.textContent = "빈 이미지 파일은 처리할 수 없습니다.";
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    status.textContent = "이미지 파일은 10MB 이하로 업로드해 주세요.";
    return;
  }

  const existingDraft = extractionDrafts[scope];
  const hasUnreviewedCandidates = existingDraft &&
    existingDraft.menus.some(
      (menu) =>
        !savedExtractionCandidateIds.has(menu.id) &&
        !menuItems.some((item) => item.sourceCandidateId === menu.id),
    );
  if (
    hasUnreviewedCandidates &&
    !window.confirm("아직 검토하지 않은 후보를 새 이미지 결과로 바꿀까요?")
  ) {
    status.textContent =
      "기존 이미지 후보를 유지했습니다. 저장된 급식표는 변경되지 않았습니다.";
    return;
  }

  const formData = new FormData();
  formData.append("image", file);
  formData.append("scope", scope);
  const requestedDate = isDaily
    ? dailyUploadDateInput.value
    : monthlyTargetDateInput.value;
  if (!isValidIsoDate(requestedDate)) {
    status.textContent = "이미지에서 확인할 날짜를 먼저 선택해 주세요.";
    return;
  }
  formData.append("selected_date", requestedDate);
  if (isDaily) {
    formData.append("reference_date", requestedDate);
  } else {
    if (requestedDate.slice(0, 7) !== mealMonthInput.value) {
      status.textContent = "조회 월과 이미지에서 확인할 날짜를 맞춰 주세요.";
      return;
    }
    formData.append("reference_month", requestedDate.slice(0, 7));
  }

  isExtractingImage = true;
  let timedOut = false;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, IMAGE_EXTRACTION_TIMEOUT_MS);
  status.textContent = "";
  progress.hidden = false;
  updateAnalysisControls();
  renderExtractionResults(scope);
  try {
    const payload = await requestJson("/api/meal-sheets/extract", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    if (!isValidImageExtraction(payload, scope, requestedDate)) {
      throw new Error("이미지 추출 응답 형식을 확인할 수 없습니다.");
    }

    extractionDrafts[scope] = {
      ...payload,
      menus: payload.menus.map((menu) => ({
        ...menu,
        assignedDate: menu.date || "",
      })),
    };
    if (isDaily) {
      input.value = "";
    }
    renderExtractionResults(scope);
    status.textContent = payload.menus.length
      ? `${requestedDate}에 연결된 ${payload.menus.length}개 후보를 추출했습니다. 아직 저장하지 않았으며 날짜와 표시를 직접 검토해 주세요.`
      : `${requestedDate}에 연결된 메뉴를 확인하지 못했습니다. 급식 없음으로 단정하지 말고 이미지를 확인해 주세요.`;
    if (payload.menus.some((menu) => menu.date === requestedDate)) {
      await importExtractedCandidates(scope);
    }
  } catch (error) {
    if (timedOut || error.name === "AbortError") {
      status.textContent =
        "이미지 분석 시간이 초과되어 요청을 종료했습니다. 이미지를 확인한 뒤 다시 시도해 주세요. 기존 저장 데이터는 변경되지 않았습니다.";
    } else if (error instanceof TypeError) {
      status.textContent =
        "API 서버에 연결할 수 없어 이미지를 처리하지 못했습니다. 기존 저장 데이터는 변경되지 않았습니다. 다시 시도해 주세요.";
    } else {
      status.textContent =
        `이미지 추출에 실패했습니다. ${error.message} 이미지를 확인한 뒤 다시 시도해 주세요. 기존 저장 데이터는 변경되지 않았습니다.`;
    }
  } finally {
    window.clearTimeout(timeoutId);
    progress.hidden = true;
    isExtractingImage = false;
    updateAnalysisControls();
    renderExtractionResults(scope);
  }
}

async function importExtractedCandidate(scope, candidateId) {
  if (isExtractingImage) {
    return;
  }
  const draft = extractionDrafts[scope];
  const candidateMenu = draft?.menus.find((menu) => menu.id === candidateId);
  if (!candidateMenu || !isValidIsoDate(candidateMenu.assignedDate)) {
    const status = scope === "daily"
      ? dailyExtractionStatus
      : monthlyExtractionStatus;
    status.textContent =
      "날짜가 지정되지 않았습니다. 저장할 날짜를 선택한 뒤 가져와 주세요.";
    return;
  }
  if (
    savedExtractionCandidateIds.has(candidateId) ||
    menuItems.some((menu) => menu.sourceCandidateId === candidateId)
  ) {
    return;
  }

  if (selectedDate !== candidateMenu.assignedDate) {
    if (!confirmDateNavigation()) {
      return;
    }
    try {
      await loadDateMealSheet(candidateMenu.assignedDate);
      await loadMonthCalendar(candidateMenu.assignedDate.slice(0, 7));
    } catch (error) {
      analysisStatus.textContent =
        `선택한 날짜를 불러오지 못했습니다. ${error.message} 저장된 내용은 변경되지 않았습니다.`;
      return;
    }
  }

  menuItems.push({
    id: candidateMenu.id,
    name: candidateMenu.name,
    allergens: candidateMenu.allergens,
    isInformationComplete: false,
    mealType: candidateMenu.meal_type,
    sourceCandidateId: candidateMenu.id,
  });
  markMealSheetDirty();
  renderMenuItems();
  renderExtractionResults(scope);
  reviewReturnStep = scope === "monthly" ? "monthlyDate" : "dailyUpload";
  analysisStatus.textContent =
    "AI 후보를 검토 목록에 가져왔습니다. 메뉴명과 알레르기 표시를 수정하고 사용자가 확인한 뒤 저장해 주세요.";
  showStep("review");
}

async function importExtractedCandidates(scope) {
  if (isExtractingImage || isSavingMealSheet) {
    return;
  }
  const draft = extractionDrafts[scope];
  if (!draft) {
    return;
  }
  const candidates = draft.menus.filter(
    (menu) =>
      menu.assignedDate === draft.selected_date &&
      !savedExtractionCandidateIds.has(menu.id) &&
      !menuItems.some((item) => item.sourceCandidateId === menu.id),
  );
  if (candidates.length === 0) {
    return;
  }

  if (selectedDate !== draft.selected_date) {
    if (!confirmDateNavigation()) {
      return;
    }
    try {
      await loadDateMealSheet(draft.selected_date);
      await loadMonthCalendar(draft.selected_date.slice(0, 7));
    } catch (error) {
      const status = scope === "daily"
        ? dailyExtractionStatus
        : monthlyExtractionStatus;
      status.textContent =
        `선택한 날짜를 불러오지 못했습니다. ${error.message}`;
      return;
    }
  }

  for (const menu of candidates) {
    menuItems.push({
      id: menu.id,
      name: menu.name,
      allergens: menu.allergens,
      isInformationComplete: false,
      mealType: menu.meal_type,
      sourceCandidateId: menu.id,
    });
  }
  markMealSheetDirty();
  renderMenuItems();
  reviewReturnStep = scope === "monthly" ? "monthlyDate" : "dailyUpload";
  analysisStatus.textContent =
    `${candidates.length}개 후보를 검토 목록에 가져왔습니다. 내용을 확인하고 검토 완료로 저장한 뒤 비교해 주세요.`;
  showStep("review");
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
  profileNextButton.disabled =
    !isLoaded || isSaving || hasUnsavedChanges || savedAllergies.length === 0;
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
    isExtractingImage ||
    isAnalyzing ||
    !menuNameInput.value.trim();
  saveMealSheetButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isExtractingImage ||
    isAnalyzing ||
    !isMealSheetDirty ||
    editingMenuId !== null;
  confirmMealSheetButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isExtractingImage ||
    isAnalyzing ||
    !canConfirmMealSheet ||
    (isMealSheetReviewed && !isMealSheetDirty) ||
    editingMenuId !== null;
  noMealButton.disabled =
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isExtractingImage ||
    isAnalyzing ||
    editingMenuId !== null;
  analyzeDateButton.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    currentDateStatus !== "REVIEWED" ||
    !isMealSheetReviewed ||
    isSavingMealSheet ||
    isExtractingImage ||
    isAnalyzing ||
    isMealSheetDirty ||
    editingMenuId !== null ||
    savedAllergies.length === 0 ||
    hasUnsavedAllergyChanges;
  analyzeLegacyButton.disabled =
    !isLoaded ||
    isAnalyzing ||
    isExtractingImage ||
    isSavingMealSheet ||
    !legacyMealSheet ||
    !legacyMealSheet.reviewed ||
    savedAllergies.length === 0 ||
    hasUnsavedAllergyChanges;
  menuEntryFieldset.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    isSavingMealSheet ||
    isExtractingImage ||
    isAnalyzing;
  updateImageUploadControls();
}

function updateImageUploadControls() {
  const imageRequestBusy = isExtractingImage || isSavingMealSheet || isAnalyzing;
  mealDateInput.disabled = !isLoaded || imageRequestBusy;
  mealMonthInput.disabled = !isLoaded || imageRequestBusy;
  monthlyTargetDateInput.disabled = !isLoaded || imageRequestBusy;
  dailyImageFieldset.disabled =
    !isLoaded ||
    !isMealSheetLoaded ||
    imageRequestBusy;
  extractDailyButton.disabled =
    dailyImageFieldset.disabled ||
    !dailyImageInput.files ||
    dailyImageInput.files.length === 0;
  monthlyImageFieldset.disabled = !isLoaded || imageRequestBusy;
  extractMonthlyButton.disabled =
    monthlyImageFieldset.disabled ||
    !monthlyImageInput.files ||
    monthlyImageInput.files.length === 0;
  document.querySelector("#view-monthly-results-button").disabled =
    !isLoaded || imageRequestBusy ||
    !isValidIsoDate(monthlyTargetDateInput.value) ||
    monthlyTargetDateInput.value.slice(0, 7) !== mealMonthInput.value ||
    (dateSelectionMode === "uploaded" && !monthlyUploadedFile);
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
  analysisStatus.textContent =
    "저장되지 않은 메뉴 변경 사항이 있습니다. 저장하거나 검토 완료로 저장해 주세요.";
  updateAnalysisControls();
}

function resetMenuEditor() {
  editingMenuId = null;
  document.querySelector("#review-editor").open = false;
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
      document.querySelector("#review-editor").open = true;
      menuNameInput.value = menu.name;
      menuMealTypeInput.value = menu.mealType || "";
      menuAllergensInput.value = (menu.allergens || [])
        .map((item) => item.replace(/^범례 확인 필요:\s*/, ""))
        .join(", ");
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
    let candidateStatus = null;
    if (menu.sourceCandidateId && !menu.isInformationComplete) {
      candidateStatus = document.createElement("p");
      candidateStatus.className = "candidate-warnings";
      candidateStatus.textContent =
        "AI 추출 후보입니다. 메뉴명과 표시를 직접 확인한 뒤 저장해 주세요.";
    }
    const mealType = document.createElement("span");
    mealType.className = "meal-type-label";
    mealType.textContent = `식사 구분 · ${{
      morning_snack: "오전 간식",
      lunch: "점심",
      afternoon_snack: "오후 간식",
    }[menu.mealType] || "미분류"}`;
    item.append(
      header,
      mealType,
      label,
      tags,
      details,
      ...(candidateStatus ? [candidateStatus] : []),
    );
    if (menu.allergens === null) {
      const confirmation = document.createElement("div");
      confirmation.className = "no-marking-confirmation";
      const explanation = document.createElement("p");
      explanation.textContent =
        "급식표 원본에서 이 메뉴에 알레르기 표시가 없는 것을 확인했나요?";
      const confirmButton = document.createElement("button");
      confirmButton.type = "button";
      confirmButton.className = "button-secondary";
      confirmButton.textContent = "표시 없음 확인";
      confirmButton.setAttribute("aria-label", `${menu.name} 알레르기 표시 없음 확인`);
      confirmButton.disabled = isSavingMealSheet || isAnalyzing;
      confirmButton.addEventListener("click", () => {
        menuItems = menuItems.map((item) => item.id === menu.id
          ? { ...item, allergens: [], isInformationComplete: true }
          : item);
        markMealSheetDirty();
        renderMenuItems();
        analysisStatus.textContent =
          `${menu.name}의 표시 없음을 확인했습니다. 검토 완료로 저장하면 비교 결과에 반영됩니다.`;
      });
      confirmation.append(explanation, confirmButton);
      item.append(confirmation);
    }
    menuList.append(item);
  }

  updateAnalysisControls();
  renderExtractionResults("daily");
  renderExtractionResults("monthly");
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

  const mayMentionRegisteredAllergy = (evidence) => evidence.some((label) =>
    savedAllergies.some((allergy) => {
      const number = allergyNameToNumber.get(allergy);
      return label.includes(allergy) || Boolean(number && (
        label.includes(String.fromCharCode(0x2460 + number - 1)) ||
        new RegExp(`(?<!\\d)${number}(?!\\d)`).test(label)
      ));
    }));
  analysisResults.replaceChildren();
  const attentionResults = payload.results.filter(
    (result) => result.status === "MATCH" ||
      (result.status === "CHECK_NEEDED" &&
        mayMentionRegisteredAllergy(result.evidence)),
  );
  const unreadResults = payload.results.filter(
    (result) => result.status === "CHECK_NEEDED" &&
      !mayMentionRegisteredAllergy(result.evidence),
  );
  const overview = document.createElement("p");
  overview.className = "result-overview";
  overview.textContent =
    `등록 알레르기: ${savedAllergies.join(", ") || "없음"} · 주의 표시 ${attentionResults.filter((result) => result.status === "MATCH").length}개 · 번호 확인 ${attentionResults.filter((result) => result.status === "CHECK_NEEDED").length}개`;
  analysisResults.append(overview);
  if (attentionResults.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent =
      "등록한 알레르기와 일치하는 표시가 확인된 메뉴는 없습니다.";
    analysisResults.append(empty);
  }
  const list = document.createElement("ul");
  list.className = "result-list";
  const statusLabels = {
    MATCH: "주의 표시",
    CHECK_NEEDED: "추가 확인 필요",
    NOT_IDENTIFIED: "표시 항목상 일치 없음",
  };
  const statusClasses = {
    MATCH: "match",
    CHECK_NEEDED: "check-needed",
    NOT_IDENTIFIED: "not-identified",
  };

  for (const result of attentionResults) {
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

    const reason = document.createElement("p");
    reason.textContent = result.status === "MATCH"
      ? `급식표 표시에 등록한 ${result.matched_allergens.join(", ")} 항목이 있습니다. 원재료와 조리 과정은 담당자에게 확인해 주세요.`
      : `알레르기 번호를 충분히 읽지 못해 ${savedAllergies.join(", ")} 포함 여부를 확인할 수 없습니다. 원본 급식표를 확인해 주세요.`;
    item.append(header, reason);
    list.append(item);
  }

  analysisResults.append(list);
  if (unreadResults.length > 0) {
    const unread = document.createElement("details");
    unread.className = "result-unread-details";
    const summary = document.createElement("summary");
    summary.textContent = `등록 알레르기 여부가 불명확한 메뉴 ${unreadResults.length}개 보기`;
    const description = document.createElement("p");
    description.textContent =
      `${savedAllergies.join(", ")} 표시가 있는지 판단할 정보가 부족합니다. 원본에서 표시가 없는 것을 확인했다면 ‘메뉴 다시 확인’에서 확정할 수 있어요.`;
    const names = document.createElement("p");
    names.textContent = unreadResults.map((result) => result.menu_name).join(" · ");
    unread.append(summary, description, names);
    analysisResults.append(unread);
  }
  contactRequestPanel.hidden = !payload.date || attentionResults.length === 0;
  if (payload.date && attentionResults.length > 0) {
    const menuNames = attentionResults
      .map((result) => result.menu_name)
      .filter(Boolean);
    contactRequestText.value =
      `안녕하세요. ${payload.date} 급식 메뉴 중 ${menuNames.join(", ") || "선택한 메뉴"}에 ` +
      `아이의 알레르기 항목(${savedAllergies.join(", ")})이 포함되는지, ` +
      "원재료와 조리 과정까지 확인 부탁드립니다. 감사합니다.";
    copyContactRequestStatus.textContent = "";
  }
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
  dailyUploadDateInput.value = dateValue;
  mealMonthInput.value = dateValue.slice(0, 7);
  monthlyTargetDateInput.value = dateValue;
  isMealSheetLoaded = false;
  isMealSheetReviewed = false;
  isMealSheetDirty = false;
  menuItems = [];
  resetMenuEditor();
  renderMenuItems();
  analysisResults.replaceChildren();
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
    sourceCandidateId: null,
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
    if (dateValue === (dateSelectionMode === "uploaded"
      ? monthlyTargetDateInput.value
      : selectedDate)) {
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
      if (dateSelectionMode === "uploaded") {
        monthlyTargetDateInput.value = dateValue;
        for (const dayButton of monthCalendar.querySelectorAll(".calendar-day")) {
          dayButton.removeAttribute("aria-current");
        }
        button.setAttribute("aria-current", "date");
        updateImageUploadControls();
        return;
      }
      if (!confirmDateNavigation()) {
        return;
      }
      reviewReturnStep = "monthlyDate";
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
  dailyUploadDateInput.value = selectedDate;
  mealMonthInput.value = selectedDate.slice(0, 7);
  monthlyTargetDateInput.value = selectedDate;
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
    if (allergies.length > 0) {
      showStep("type");
    }
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
    isExtractingImage ||
    isAnalyzing
  ) {
    return;
  }

  const existingMenu = menuItems.find((menu) => menu.id === editingMenuId);
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
    sourceCandidateId: existingMenu?.sourceCandidateId || null,
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
    isExtractingImage ||
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
  const importedCandidateIds = status === "NO_MEAL"
    ? []
    : menuItems
      .map((menu) => menu.sourceCandidateId)
      .filter(Boolean);
  isSavingMealSheet = true;
  let shouldAnalyzeAfterSave = false;
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

    for (const candidateId of importedCandidateIds) {
      savedExtractionCandidateIds.add(candidateId);
    }
    currentDateStatus = savedSheet.status;
    menuItems = savedSheet.menus.map((menu) => ({
      id: menu.id,
      name: menu.name,
      allergens: menu.allergens,
      isInformationComplete: menu.is_information_complete,
      mealType: menu.meal_type,
      sourceCandidateId: null,
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
    shouldAnalyzeAfterSave = savedSheet.status === "REVIEWED";
  } catch (error) {
    analysisStatus.textContent = error instanceof TypeError
      ? "급식표 API에 연결할 수 없어 저장하지 못했습니다."
      : `급식표를 저장하지 못했습니다. ${error.message}`;
  } finally {
    isSavingMealSheet = false;
    renderMenuItems();
    if (shouldAnalyzeAfterSave) {
      analyzeDateButton.click();
    }
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
  updateAnalysisControls();

  try {
    const payload = await requestJson("/api/analyze", {
      method: "POST",
    });

    renderAnalysisResults(payload);
    resultsHeading.textContent = "날짜 미지정 급식표의 기존 비교";
    resultsDescription.textContent =
      `메뉴 ${payload.results.length}개를 비교했습니다. 등록 알레르기와 관련된 결과를 표시합니다.`;
    analysisStatus.textContent =
      `메뉴 ${payload.results.length}개를 비교했습니다. 등록 알레르기와 관련된 결과를 표시합니다.`;
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
      `${requestedDate} · 메뉴 ${payload.results.length}개를 비교했습니다. 등록 알레르기와 관련된 결과를 표시합니다.`;
    analysisStatus.textContent =
      `${requestedDate} · 메뉴 ${payload.results.length}개를 비교했습니다. 등록 알레르기와 관련된 결과를 표시합니다.`;
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
  if (profileNextButton.disabled) {
    saveStatus.textContent = "알레르기 항목을 저장한 뒤 급식표를 확인해 주세요.";
    return;
  }
  showStep("type");
});
document.querySelector("#type-back-button").addEventListener("click", () => {
  showStep("profile");
});
document.querySelector("#choose-daily-button").addEventListener("click", () => {
  dailyUploadDateInput.value = selectedDate || getLocalDateString();
  showStep("dailyUpload");
});
document.querySelector("#choose-monthly-button").addEventListener("click", () => {
  const targetDate = selectedDate || getLocalDateString();
  monthlyTargetDateInput.value = targetDate;
  mealMonthInput.value = targetDate.slice(0, 7);
  showStep("monthly");
});
document.querySelector("#choose-saved-button").addEventListener("click", () => {
  dateSelectionMode = "saved";
  mealMonthInput.value = selectedDate.slice(0, 7);
  monthlyTargetDateInput.value = selectedDate;
  document.querySelector("#view-monthly-results-button").textContent =
    "저장된 급식표 보기";
  document.querySelector("#monthly-date-back-button").textContent =
    "← 유형 다시 선택";
  loadMonthCalendar(mealMonthInput.value);
  updateImageUploadControls();
  showStep("monthlyDate");
});
document.querySelector("#daily-upload-back-button").addEventListener("click", () => {
  showStep("type");
});
document.querySelector("#daily-manual-button").addEventListener("click", async () => {
  const dateValue = dailyUploadDateInput.value;
  if (!isValidIsoDate(dateValue) || !confirmDateNavigation()) {
    dailyExtractionStatus.textContent = "급식 날짜를 확인해 주세요.";
    return;
  }
  try {
    await loadDateMealSheet(dateValue);
    reviewReturnStep = "dailyUpload";
    showStep("review");
  } catch (error) {
    dailyExtractionStatus.textContent = `날짜 정보를 불러오지 못했습니다. ${error.message}`;
  }
});
document.querySelector("#monthly-back-button").addEventListener("click", () => {
  showStep("type");
});
document.querySelector("#monthly-date-back-button").addEventListener("click", () => {
  showStep(dateSelectionMode === "saved" ? "type" : "monthly");
});
document.querySelector("#view-monthly-results-button").addEventListener("click", async () => {
  const dateValue = monthlyTargetDateInput.value;
  if (!isValidIsoDate(dateValue)) {
    monthlyExtractionStatus.textContent = "날짜를 선택해 주세요.";
    return;
  }
  if (dateSelectionMode === "uploaded") {
    await extractMealImage("monthly");
    return;
  }
  if (!confirmDateNavigation()) {
    return;
  }
  try {
    await loadDateMealSheet(dateValue);
    reviewReturnStep = "monthlyDate";
    showStep("review");
  } catch (error) {
    monthlyExtractionStatus.textContent = `날짜 정보를 불러오지 못했습니다. ${error.message}`;
  }
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
document.querySelector("#copy-contact-request-button").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(contactRequestText.value);
    copyContactRequestStatus.textContent = "문의 문장을 복사했습니다.";
  } catch (error) {
    copyContactRequestStatus.textContent =
      "복사하지 못했습니다. 문장을 직접 선택해 복사해 주세요.";
  }
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
  try {
    await loadDateMealSheet(nextDate);
    await loadMonthCalendar(mealMonthInput.value);
  } catch (error) {
    analysisStatus.textContent =
      `날짜별 급식표를 불러오지 못했습니다. ${error.message}`;
  }
});
mealMonthInput.addEventListener("change", () => {
  if (
    monthlyTargetDateInput.value &&
    monthlyTargetDateInput.value.slice(0, 7) !== mealMonthInput.value
  ) {
    monthlyTargetDateInput.value = "";
  }
  loadMonthCalendar(mealMonthInput.value);
  updateImageUploadControls();
});

monthlyTargetDateInput.addEventListener("change", () => {
  if (isValidIsoDate(monthlyTargetDateInput.value)) {
    mealMonthInput.value = monthlyTargetDateInput.value.slice(0, 7);
    loadMonthCalendar(mealMonthInput.value);
  }
  updateImageUploadControls();
});

dailyImageInput.addEventListener("change", () => {
  const file = dailyImageInput.files && dailyImageInput.files[0];
  dailyExtractionStatus.textContent = file
    ? `선택한 이미지: ${file.name}`
    : "이미지를 선택해 주세요.";
  updateImageUploadControls();
});
monthlyImageInput.addEventListener("change", () => {
  const file = monthlyImageInput.files && monthlyImageInput.files[0];
  document.querySelector("#monthly-upload-file-status").textContent = file
    ? `선택한 이미지: ${file.name}`
    : "이미지를 선택해 주세요.";
  updateImageUploadControls();
});
dailyImageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  extractMealImage("daily");
});
monthlyImageForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const file = monthlyImageInput.files && monthlyImageInput.files[0];
  if (!file) {
    return;
  }
  if (file.size === 0 || file.size > 10 * 1024 * 1024) {
    document.querySelector("#monthly-upload-file-status").textContent =
      file.size === 0 ? "빈 이미지 파일은 업로드할 수 없습니다." : "이미지 크기는 10MB 이하여야 합니다.";
    return;
  }
  monthlyUploadedFile = file;
  dateSelectionMode = "uploaded";
  extractionDrafts.monthly = null;
  renderExtractionResults("monthly");
  monthlyExtractionStatus.textContent = "날짜를 선택해 인식 결과를 확인해 주세요.";
  document.querySelector("#view-monthly-results-button").textContent =
    "급식표 인식 결과 보기";
  document.querySelector("#monthly-date-back-button").textContent =
    "← 급식표 업로드";
  loadMonthCalendar(mealMonthInput.value);
  updateImageUploadControls();
  showStep("monthlyDate");
});

retryButton.addEventListener("click", loadProfile);
loadProfile();
