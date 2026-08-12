(() => {
  const catalogElement = document.getElementById("erp-catalog-data");
  if (!catalogElement) return;

  const catalog = JSON.parse(catalogElement.textContent);
  const collator = new Intl.Collator("ru");
  const unique = (values) => [...new Set(values)].sort(collator.compare);
  const EMPTY_LEVEL = "__EMPTY__";
  const VALUE_PREFIX = "__VALUE__:";

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

  document.querySelectorAll('[data-testid="attention-editor"]').forEach((form) => {
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
})();
