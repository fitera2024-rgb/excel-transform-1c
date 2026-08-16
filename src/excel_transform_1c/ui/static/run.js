(() => {
  const catalogElement = document.getElementById("erp-catalog-data");
  const catalog = catalogElement ? JSON.parse(catalogElement.textContent) : [];
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
  let bulkConfirmableRows = new Set();
  try {
    bulkConfirmableRows = new Set(
      JSON.parse(bulkForm?.dataset.bulkConfirmableRows || "[]").map((value) => Number(value)),
    );
  } catch {
    bulkConfirmableRows = new Set();
  }

  function encodeLevelValue(value) {
    return value === "" ? EMPTY_LEVEL : `${VALUE_PREFIX}${encodeURIComponent(value)}`;
  }

  function decodeLevelValue(value) {
    if (value === EMPTY_LEVEL) return "";
    if (value?.startsWith(VALUE_PREFIX)) {
      return decodeURIComponent(value.slice(VALUE_PREFIX.length));
    }
    return null;
  }

  function selectedLevelValue(select) {
    return select ? decodeLevelValue(select.value) : null;
  }

  function displayLevel(value, emptyLabel) {
    return value === "" ? emptyLabel : value;
  }

  function replaceOptions(select, items, placeholder, valueOf, labelOf) {
    if (!select) return;
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
    if (!typeSelect || !groupSelect || !articleSelect || !codeSelect) return null;

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

  function correctionHasChange(form) {
    const confirmedCode = form.querySelector("[data-erp-confirmed-code]");
    if (confirmedCode?.value) return true;
    return [...form.querySelectorAll("[data-correction-control]")].some((control) =>
      control.type === "checkbox" ? control.checked : control.value !== "",
    );
  }

  function refreshCorrectionForm(form) {
    const submit = form.querySelector("[data-correction-submit]");
    if (!submit) return;
    const ready = correctionHasChange(form);
    submit.disabled = !ready;
    submit.textContent = ready
      ? "Применить к этой строке и всем месяцам"
      : "Применить к исходной строке и всем месяцам";
  }

  editors.forEach((form) => {
    form.querySelectorAll("[data-correction-control]").forEach((control) => {
      control.addEventListener("change", () => refreshCorrectionForm(form));
    });
    form.addEventListener("submit", (event) => {
      refreshCorrectionForm(form);
      const submit = form.querySelector("[data-correction-submit]");
      if (!correctionHasChange(form)) {
        event.preventDefault();
        return;
      }
      if (submit) {
        submit.disabled = true;
        submit.textContent = "Применение…";
      }
    });
  });

  // ERP hierarchy editors.
  editors.forEach((form) => {
    const typeSelect = form.querySelector('[data-erp-level="type"]');
    const groupSelect = form.querySelector('[data-erp-level="group"]');
    const articleSelect = form.querySelector('[data-erp-level="article"]');
    const codeSelect = form.querySelector('[data-erp-level="code"]');
    const confirmation = form.querySelector("[data-erp-confirm]");
    const confirmedCode = form.querySelector("[data-erp-confirmed-code]");
    const selection = form.querySelector("[data-erp-selection]");
    const confirmationHint = form.querySelector("[data-erp-confirm-hint]");
    if (!typeSelect || !groupSelect || !articleSelect || !codeSelect || !confirmation) {
      refreshCorrectionForm(form);
      return;
    }

    const current = {
      expenseType: form.dataset.currentErpType,
      expenseGroup: form.dataset.currentErpGroup,
      sourceArticle: form.dataset.currentErpArticle,
      code: form.dataset.currentErpCode,
    };

    function clearConfirmation() {
      confirmation.checked = false;
      if (confirmedCode) confirmedCode.value = "";
      refreshCorrectionForm(form);
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
        if (selection) {
          selection.textContent = candidates.length
            ? "Выберите один из ERP-кодов в этой ветке."
            : "Для выбранного полного пути ERP-коды отсутствуют.";
        }
        if (confirmationHint) {
          confirmationHint.textContent = "ERP-сопоставление останется без изменения.";
        }
        refreshBulkConfirmation();
        return;
      }

      if (selection) {
        selection.textContent =
          `${displayLevel(selected.expenseType, "Корневой уровень")} → ` +
          `${displayLevel(selected.expenseGroup, "Без группы")} → ` +
          `${displayLevel(selected.sourceArticle, "Без статьи")} → ` +
          `${displayLevel(selected.code, "Без кода")} · ` +
          `${displayLevel(selected.name, "Без официального наименования")}`;
      }
      if (confirmationHint) {
        confirmationHint.textContent =
          candidates.length === 1
            ? "Единственный код предварительно выбран. Подтвердите его явно и отправьте форму."
            : "Подтвердите выбранный код явно и отправьте форму.";
      }
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
          .filter((article) => expenseType !== null && article.expenseType === expenseType)
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
      if (confirmedCode) {
        confirmedCode.value = confirmation.checked
          ? (selectedLevelValue(codeSelect) ?? "")
          : "";
      }
      refreshCorrectionForm(form);
    });
    refreshCorrectionForm(form);
  });

  // ERP bulk confirmation.
  function currentBulkSelections() {
    const bySourceRow = new Map();
    editors.forEach((form) => {
      const sourceRow = Number(form.dataset.sourceRow);
      if (!bulkConfirmableRows.has(sourceRow)) return;
      const selection = filledSelection(form);
      if (selection) bySourceRow.set(selection.source_row, selection);
    });
    return [...bySourceRow.values()].sort((left, right) => left.source_row - right.source_row);
  }

  function refreshBulkConfirmation() {
    if (!bulkForm) return;
    const selections = currentBulkSelections();
    const hasSelections = selections.length > 0;
    if (bulkSelections) bulkSelections.value = JSON.stringify(selections);
    if (bulkCount) bulkCount.textContent = `Будет подтверждено: ${selections.length} строк`;
    if (bulkEmpty) bulkEmpty.hidden = hasSelections;
    if (bulkConfirmation) {
      bulkConfirmation.disabled = !hasSelections;
      if (!hasSelections) bulkConfirmation.checked = false;
    }
    if (bulkSubmit) {
      bulkSubmit.disabled = !hasSelections || !bulkConfirmation?.checked;
      bulkSubmit.textContent = !hasSelections
        ? "Нет новых сопоставлений"
        : !bulkConfirmation?.checked
          ? "Сначала поставьте галку"
          : "Применить все заполненные";
    }
  }

  bulkConfirmation?.addEventListener("change", refreshBulkConfirmation);
  bulkForm?.addEventListener("submit", (event) => {
    refreshBulkConfirmation();
    if (bulkSubmit?.disabled) {
      event.preventDefault();
      return;
    }
    bulkSubmit.disabled = true;
    bulkSubmit.textContent = "Применение…";
  });

  // Tax bulk confirmation.
  const taxBulkForm = document.querySelector("[data-tax-bulk-form]");
  const taxBulkConfirm = taxBulkForm?.querySelector("[data-tax-bulk-confirm]");
  const taxBulkSubmit = taxBulkForm?.querySelector("[data-tax-bulk-submit]");
  taxBulkConfirm?.addEventListener("change", () => {
    if (!taxBulkSubmit) return;
    taxBulkSubmit.disabled = !taxBulkConfirm.checked;
    taxBulkSubmit.textContent = taxBulkConfirm.checked
      ? "Применить всё"
      : "Сначала поставьте галку";
  });
  taxBulkForm?.addEventListener("submit", (event) => {
    if (!taxBulkConfirm?.checked) {
      event.preventDefault();
      return;
    }
    if (taxBulkSubmit) {
      taxBulkSubmit.disabled = true;
      taxBulkSubmit.textContent = "Применение…";
    }
  });

  // CFO individual and bulk mapping.
  const cfoEntries = [...document.querySelectorAll("[data-cfo-entry]")];
  const cfoBulkForm = document.querySelector("[data-cfo-bulk-form]");
  const cfoBulkSelections = cfoBulkForm?.querySelector("[data-cfo-bulk-selections]");
  const cfoBulkConfirm = cfoBulkForm?.querySelector("[data-cfo-bulk-confirm]");
  const cfoBulkCount = cfoBulkForm?.querySelector("[data-cfo-bulk-count]");
  const cfoBulkEmpty = cfoBulkForm?.querySelector("[data-cfo-bulk-empty]");
  const cfoBulkSubmit = cfoBulkForm?.querySelector("[data-cfo-bulk-submit]");

  function currentCfoSelections() {
    const byEntryKey = new Map();
    cfoEntries.forEach((entry) => {
      if (entry.dataset.confirmed === "true") return;
      const entryKey = entry.dataset.entryKey || "";
      const intalevSourceKey = entry.querySelector("[data-cfo-intalev]")?.value || "";
      const target = entry.querySelector("[data-cfo-target]")?.value || "";
      if (entryKey && intalevSourceKey && target) {
        byEntryKey.set(entryKey, {
          source_reporting_unit: entry.dataset.sourceReportingUnit || "",
          source_cfo: entry.dataset.sourceCfo || "",
          intalev_source_key: intalevSourceKey,
          target_node_id: target,
        });
      }
    });
    return [...byEntryKey.values()].sort((left, right) =>
      collator.compare(
        `${left.source_reporting_unit}\u0000${left.source_cfo}`,
        `${right.source_reporting_unit}\u0000${right.source_cfo}`,
      ),
    );
  }

  function refreshCfoBulk() {
    if (!cfoBulkForm) return;
    const selections = currentCfoSelections();
    const hasSelections = selections.length > 0;
    if (cfoBulkSelections) cfoBulkSelections.value = JSON.stringify(selections);
    if (cfoBulkCount) cfoBulkCount.textContent = `Будет применено: ${selections.length} ЦФО`;
    if (cfoBulkEmpty) {
      cfoBulkEmpty.hidden = hasSelections;
      cfoBulkEmpty.textContent = "Сначала заполните хотя бы одно новое соответствие.";
    }
    if (cfoBulkConfirm) {
      cfoBulkConfirm.disabled = !hasSelections;
      if (!hasSelections) cfoBulkConfirm.checked = false;
    }
    if (cfoBulkSubmit) {
      cfoBulkSubmit.disabled = !hasSelections || !cfoBulkConfirm?.checked;
      cfoBulkSubmit.textContent = !hasSelections
        ? "Нет заполненных соответствий"
        : !cfoBulkConfirm?.checked
          ? "Сначала поставьте галку"
          : "Применить всё";
    }
  }

  cfoEntries.forEach((entry) => {
    const form = entry.querySelector("[data-cfo-form]");
    if (!form) return;
    const intalev = form.querySelector("[data-cfo-intalev]");
    const target = form.querySelector("[data-cfo-target]");
    const confirmation = form.querySelector("[data-cfo-confirm]");
    const submit = form.querySelector("[data-cfo-submit]");

    function refreshCfoForm() {
      const hasBoth = Boolean(intalev?.value && target?.value);
      if (confirmation) {
        confirmation.disabled = !hasBoth;
        if (!hasBoth) confirmation.checked = false;
      }
      if (submit) {
        submit.disabled = !hasBoth || !confirmation?.checked;
        submit.textContent = !hasBoth
          ? "Сначала выберите оба значения"
          : !confirmation?.checked
            ? "Сначала поставьте галку"
            : "Применить соответствие";
      }
      refreshCfoBulk();
    }

    intalev?.addEventListener("change", refreshCfoForm);
    target?.addEventListener("change", refreshCfoForm);
    confirmation?.addEventListener("change", refreshCfoForm);
    form.addEventListener("submit", (event) => {
      refreshCfoForm();
      if (submit?.disabled) {
        event.preventDefault();
        return;
      }
      submit.disabled = true;
      submit.textContent = "Применение…";
    });
    refreshCfoForm();
  });

  cfoBulkConfirm?.addEventListener("change", refreshCfoBulk);
  cfoBulkForm?.addEventListener("submit", (event) => {
    refreshCfoBulk();
    if (cfoBulkSubmit?.disabled) {
      event.preventDefault();
      return;
    }
    cfoBulkSubmit.disabled = true;
    cfoBulkSubmit.textContent = "Применение…";
  });

  refreshBulkConfirmation();
  refreshCfoBulk();
  editors.forEach(refreshCorrectionForm);
})();
