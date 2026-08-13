(() => {
  const catalogElement = document.getElementById("erp-catalog-data");
  if (!catalogElement) return;

  const catalog = JSON.parse(catalogElement.textContent);
  const collator = new Intl.Collator("ru");
  const unique = (values) => [...new Set(values)].sort(collator.compare);
  const EMPTY_LEVEL = "__EMPTY__";
  const VALUE_PREFIX = "__VALUE__:";
  const editors = [...document.querySelectorAll('[data-testid="attention-editor"]')];
  const bulkForm = document.querySelector("[data-bulk-confirm-form]");
  const bulkConfirmation = bulkForm?.querySelector("[data-bulk-confirm]");
  const bulkSelections = bulkForm?.querySelector("[data-bulk-confirm-selections]");
  const bulkCount = bulkForm?.querySelector("[data-bulk-confirm-count]");
  const bulkEmpty = bulkForm?.querySelector("[data-bulk-confirm-empty]");
  const bulkSubmit = bulkForm?.querySelector("[data-bulk-confirm-submit]");

  function encodeLevelValue(value) {
    return value === "" ? EMPTY_LEVEL : `${VALUE_PREFIX}${encodeURIComponent(value)}`;
  }

  function decodeLevelValue(value) {
    if (value === EMPTY_LEVEL) return "";
    if (value.startsWith(VALUE_PREFIX)) {
      return decodeURIComponent(value.slice(VALUE_PREFIX.length));
    }
    return null;
  }

  function selectedLevelValue(select) {
    return decodeLevelValue(select.value);
  }

  function displayLevel(value, emptyLabel) {
    return value === "" ? emptyLabel : value;
  }

  function replaceOptions(select, items, placeholder, valueOf, labelOf) {
    select.replaceChildren(new Option(placeholder, ""));
    items.forEach((item) =>
      select.add(new Option(labelOf(item), encodeLevelValue(valueOf(item)))),
    );
    select.disabled = items.length === 0;
  }

  function filledSelection(form) {
    const typeSelect = form.querySelector('[data-erp-level="type"]');
    const groupSelect = form.querySelector('[data-erp-level="group"]');
    const articleSelect = form.querySelector('[data-erp-level="article"]');
    const codeSelect = form.querySelector('[data-erp-level="code"]');
    const sourceRow = Number(form.dataset.sourceRow);
    const expenseType = selectedLevelValue(typeSelect);
    const expenseGroup = selectedLevelValue(groupSelect);
    const sourceArticle = selectedLevelValue(articleSelect);
    const erpCode = selectedLevelValue(codeSelect);

    if (
      !Number.isInteger(sourceRow) ||
      expenseType === null ||
      expenseGroup === null ||
      sourceArticle === null ||
      erpCode === null ||
      erpCode === ""
    ) {
      return null;
    }

    const exactCatalogEntry = catalog.find(
      (article) =>
        article.expenseType === expenseType &&
        article.expenseGroup === expenseGroup &&
        article.sourceArticle === sourceArticle &&
        article.code === erpCode,
    );
    if (!exactCatalogEntry) return null;

    return {
      source_row: sourceRow,
      expense_type: expenseType,
      expense_group: expenseGroup,
      source_article: sourceArticle,
      erp_code: erpCode,
    };
  }

  function currentBulkSelections() {
    const bySourceRow = new Map();
    editors.forEach((form) => {
      const selection = filledSelection(form);
      if (selection) bySourceRow.set(selection.source_row, selection);
    });
    return [...bySourceRow.values()].sort((left, right) => left.source_row - right.source_row);
  }

  function refreshBulkConfirmation() {
    if (!bulkForm) return;
    const selections = currentBulkSelections();
    const hasSelections = selections.length > 0;
    bulkSelections.value = JSON.stringify(selections);
    bulkCount.textContent = `Будет подтверждено: ${selections.length} строк`;
    bulkEmpty.hidden = hasSelections;
    bulkConfirmation.disabled = !hasSelections;
    if (!hasSelections) bulkConfirmation.checked = false;
    bulkSubmit.disabled = !hasSelections || !bulkConfirmation.checked;
  }

  editors.forEach((form) => {
    const typeSelect = form.querySelector('[data-erp-level="type"]');
    const groupSelect = form.querySelector('[data-erp-level="group"]');
    const articleSelect = form.querySelector('[data-erp-level="article"]');
    const codeSelect = form.querySelector('[data-erp-level="code"]');
    const confirmation = form.querySelector("[data-erp-confirm]");
    const confirmedCode = form.querySelector("[data-erp-confirmed-code]");
    const selection = form.querySelector("[data-erp-selection]");
    const confirmationHint = form.querySelector("[data-erp-confirm-hint]");

    const current = {
      expenseType: form.dataset.currentErpType,
      expenseGroup: form.dataset.currentErpGroup,
      sourceArticle: form.dataset.currentErpArticle,
      code: form.dataset.currentErpCode,
    };

    function clearConfirmation() {
      confirmation.checked = false;
      confirmedCode.value = "";
    }

    function matchingCodes() {
      const expenseType = selectedLevelValue(typeSelect);
      const expenseGroup = selectedLevelValue(groupSelect);
      const sourceArticle = selectedLevelValue(articleSelect);
      if (expenseType === null || expenseGroup === null || sourceArticle === null) return [];
      return catalog
        .filter(
          (article) =>
            article.expenseType === expenseType &&
            article.expenseGroup === expenseGroup &&
            article.sourceArticle === sourceArticle,
        )
        .sort((left, right) => collator.compare(left.code, right.code));
    }

    function updateSelection(candidates, preferredCode) {
      replaceOptions(
        codeSelect,
        candidates,
        candidates.length ? "Выберите ERP-код" : "Нет кодов в выбранной ветке",
        (article) => article.code,
        (article) =>
          `${displayLevel(article.code, "Без кода")} · ` +
          `${displayLevel(article.name, "Без официального наименования")}`,
      );

      if (
        preferredCode !== undefined &&
        candidates.some((article) => article.code === preferredCode)
      ) {
        codeSelect.value = encodeLevelValue(preferredCode);
      } else if (candidates.length === 1) {
        codeSelect.value = encodeLevelValue(candidates[0].code);
      }

      clearConfirmation();
      const selectedCode = selectedLevelValue(codeSelect);
      const selected = candidates.find((article) => article.code === selectedCode);
      confirmation.disabled = !selected;
      if (!selected) {
        selection.textContent = candidates.length
          ? "Выберите один из ERP-кодов в этой ветке."
          : "Для выбранного полного пути ERP-коды отсутствуют.";
        confirmationHint.textContent = "ERP-сопоставление останется без изменения.";
        refreshBulkConfirmation();
        return;
      }

      selection.textContent =
        `${displayLevel(selected.expenseType, "Корневой уровень")} → ` +
        `${displayLevel(selected.expenseGroup, "Без группы")} → ` +
        `${displayLevel(selected.sourceArticle, "Без статьи")} → ` +
        `${displayLevel(selected.code, "Без кода")} · ` +
        `${displayLevel(selected.name, "Без официального наименования")}`;
      confirmationHint.textContent =
        candidates.length === 1
          ? "Единственный код предварительно выбран. Подтвердите его явно и отправьте форму."
          : "Подтвердите выбранный код явно и отправьте форму.";
      refreshBulkConfirmation();
    }

    function updateCodes(preferredCode) {
      updateSelection(matchingCodes(), preferredCode);
    }

    function updateArticles(preferredArticle, preferredCode) {
      const expenseType = selectedLevelValue(typeSelect);
      const expenseGroup = selectedLevelValue(groupSelect);
      const articles = unique(
        catalog
          .filter(
            (article) =>
              expenseType !== null &&
              expenseGroup !== null &&
              article.expenseType === expenseType &&
              article.expenseGroup === expenseGroup,
          )
          .map((article) => article.sourceArticle),
      );
      replaceOptions(
        articleSelect,
        articles,
        expenseGroup !== null ? "Выберите статью" : "Сначала выберите группу",
        (value) => value,
        (value) => displayLevel(value, "Без статьи"),
      );
      if (preferredArticle !== undefined && articles.includes(preferredArticle)) {
        articleSelect.value = encodeLevelValue(preferredArticle);
      }
      updateCodes(preferredCode);
    }

    function updateGroups(preferredGroup, preferredArticle, preferredCode) {
      const expenseType = selectedLevelValue(typeSelect);
      const groups = unique(
        catalog
          .filter(
            (article) => expenseType !== null && article.expenseType === expenseType,
          )
          .map((article) => article.expenseGroup),
      );
      replaceOptions(
        groupSelect,
        groups,
        expenseType !== null ? "Выберите группу" : "Сначала выберите тип",
        (value) => value,
        (value) => displayLevel(value, "Без группы"),
      );
      if (preferredGroup !== undefined && groups.includes(preferredGroup)) {
        groupSelect.value = encodeLevelValue(preferredGroup);
      }
      updateArticles(preferredArticle, preferredCode);
    }

    const types = unique(catalog.map((article) => article.expenseType));
    replaceOptions(
      typeSelect,
      types,
      "Выберите тип расходов",
      (value) => value,
      (value) => displayLevel(value, "Корневой уровень"),
    );
    if (types.includes(current.expenseType)) {
      typeSelect.value = encodeLevelValue(current.expenseType);
    }
    updateGroups(current.expenseGroup, current.sourceArticle, current.code);

    typeSelect.addEventListener("change", () => updateGroups());
    groupSelect.addEventListener("change", () => updateArticles());
    articleSelect.addEventListener("change", () => updateCodes());
    codeSelect.addEventListener("change", () =>
      updateSelection(matchingCodes(), selectedLevelValue(codeSelect)),
    );
    confirmation.addEventListener("change", () => {
      confirmedCode.value = confirmation.checked
        ? (selectedLevelValue(codeSelect) ?? "")
        : "";
    });
  });

  bulkConfirmation?.addEventListener("change", refreshBulkConfirmation);
  bulkForm?.addEventListener("submit", (event) => {
    refreshBulkConfirmation();
    if (bulkSubmit.disabled) {
      event.preventDefault();
      return;
    }
    bulkSubmit.disabled = true;
    bulkSubmit.textContent = "Применение…";
  });
  refreshBulkConfirmation();
})();
