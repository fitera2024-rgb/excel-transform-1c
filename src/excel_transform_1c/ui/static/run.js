(() => {
  const catalogElement = document.getElementById("erp-catalog-data");
  if (!catalogElement) return;

  const catalog = JSON.parse(catalogElement.textContent);
  const collator = new Intl.Collator("ru");
  const unique = (values) => [...new Set(values)].sort(collator.compare);

  function replaceOptions(select, items, placeholder, valueOf, labelOf) {
    select.replaceChildren(new Option(placeholder, ""));
    items.forEach((item) => select.add(new Option(labelOf(item), valueOf(item))));
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
      return catalog
        .filter(
          (article) =>
            article.expenseType === typeSelect.value &&
            article.expenseGroup === groupSelect.value &&
            article.sourceArticle === articleSelect.value,
        )
        .sort((left, right) => collator.compare(left.code, right.code));
    }

    function updateSelection(candidates, preferredCode = "") {
      replaceOptions(
        codeSelect,
        candidates,
        candidates.length ? "Выберите ERP-код" : "Нет кодов в выбранной ветке",
        (article) => article.code,
        (article) => `${article.code} · ${article.name}`,
      );

      if (preferredCode && candidates.some((article) => article.code === preferredCode)) {
        codeSelect.value = preferredCode;
      } else if (candidates.length === 1) {
        codeSelect.value = candidates[0].code;
      }

      clearConfirmation();
      const selected = candidates.find((article) => article.code === codeSelect.value);
      confirmation.disabled = !selected;
      if (!selected) {
        selection.textContent = candidates.length
          ? "Выберите один из ERP-кодов в этой ветке."
          : "Для выбранного полного пути ERP-коды отсутствуют.";
        confirmationHint.textContent = "ERP-сопоставление останется без изменения.";
        return;
      }

      selection.textContent =
        `${selected.expenseType} → ${selected.expenseGroup} → ` +
        `${selected.sourceArticle} → ${selected.code} · ${selected.name}`;
      confirmationHint.textContent =
        candidates.length === 1
          ? "Единственный код предварительно выбран. Подтвердите его явно и отправьте форму."
          : "Подтвердите выбранный код явно и отправьте форму.";
    }

    function updateCodes(preferredCode = "") {
      updateSelection(matchingCodes(), preferredCode);
    }

    function updateArticles(preferredArticle = "", preferredCode = "") {
      const articles = unique(
        catalog
          .filter(
            (article) =>
              article.expenseType === typeSelect.value &&
              article.expenseGroup === groupSelect.value,
          )
          .map((article) => article.sourceArticle),
      );
      replaceOptions(
        articleSelect,
        articles,
        groupSelect.value ? "Выберите статью" : "Сначала выберите группу",
        (value) => value,
        (value) => value,
      );
      if (articles.includes(preferredArticle)) articleSelect.value = preferredArticle;
      updateCodes(preferredCode);
    }

    function updateGroups(preferredGroup = "", preferredArticle = "", preferredCode = "") {
      const groups = unique(
        catalog
          .filter((article) => article.expenseType === typeSelect.value)
          .map((article) => article.expenseGroup),
      );
      replaceOptions(
        groupSelect,
        groups,
        typeSelect.value ? "Выберите группу" : "Сначала выберите тип",
        (value) => value,
        (value) => value,
      );
      if (groups.includes(preferredGroup)) groupSelect.value = preferredGroup;
      updateArticles(preferredArticle, preferredCode);
    }

    const types = unique(catalog.map((article) => article.expenseType));
    replaceOptions(
      typeSelect,
      types,
      "Выберите тип расходов",
      (value) => value,
      (value) => value,
    );
    if (types.includes(current.expenseType)) typeSelect.value = current.expenseType;
    updateGroups(current.expenseGroup, current.sourceArticle, current.code);

    typeSelect.addEventListener("change", () => updateGroups());
    groupSelect.addEventListener("change", () => updateArticles());
    articleSelect.addEventListener("change", () => updateCodes());
    codeSelect.addEventListener("change", () => updateSelection(matchingCodes(), codeSelect.value));
    confirmation.addEventListener("change", () => {
      confirmedCode.value = confirmation.checked ? codeSelect.value : "";
    });
  });
})();
