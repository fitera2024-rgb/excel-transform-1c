const fs = require("node:fs");
const vm = require("node:vm");

class MockElement {
  constructor({ value = "", checked = false, disabled = false, dataset = {} } = {}) {
    this.value = value;
    this.checked = checked;
    this.disabled = disabled;
    this.dataset = dataset;
    this.hidden = false;
    this.textContent = "";
    this.options = [];
    this.listeners = new Map();
    this.selectors = new Map();
    this.selectorLists = new Map();
    this.type = "";
  }

  addEventListener(type, handler) {
    const handlers = this.listeners.get(type) || [];
    handlers.push(handler);
    this.listeners.set(type, handlers);
  }

  dispatch(type) {
    const event = { preventDefault() {} };
    for (const handler of this.listeners.get(type) || []) handler(event);
  }

  querySelector(selector) {
    return this.selectors.get(selector) || null;
  }

  querySelectorAll(selector) {
    return this.selectorLists.get(selector) || [];
  }

  replaceChildren(...items) {
    this.options = items;
    this.value = items[0]?.value || "";
  }

  add(item) {
    this.options.push(item);
  }
}

global.Option = class Option {
  constructor(text, value) {
    this.text = text;
    this.value = value;
  }
};

const catalog = [
  {
    code: "ERP-001",
    name: "Интернет ERP",
    expenseType: "Административные",
    expenseGroup: "Связь",
    sourceArticle: "Интернет",
  },
];

const typeSelect = new MockElement();
const groupSelect = new MockElement({ disabled: true });
const articleSelect = new MockElement({ disabled: true });
const codeSelect = new MockElement({ disabled: true });
const erpConfirmation = new MockElement({ disabled: true });
const confirmedCode = new MockElement();
const correctionSubmit = new MockElement({ disabled: true });
const selection = new MockElement();
const confirmationHint = new MockElement();
const editor = new MockElement({
  dataset: {
    sourceRow: "3",
    currentErpType: "Административные",
    currentErpGroup: "Связь",
    currentErpArticle: "Интернет",
    currentErpCode: "ERP-001",
  },
});
editor.selectors = new Map([
  ['[data-erp-level="type"]', typeSelect],
  ['[data-erp-level="group"]', groupSelect],
  ['[data-erp-level="article"]', articleSelect],
  ['[data-erp-level="code"]', codeSelect],
  ["[data-erp-confirm]", erpConfirmation],
  ["[data-erp-confirmed-code]", confirmedCode],
  ["[data-correction-submit]", correctionSubmit],
  ["[data-erp-selection]", selection],
  ["[data-erp-confirm-hint]", confirmationHint],
]);
editor.selectorLists.set("[data-correction-control]", []);

function formWith(selectors, dataset = {}) {
  const form = new MockElement({ dataset });
  form.selectors = new Map(selectors);
  return form;
}

const bulkConfirmation = new MockElement({ disabled: true });
const bulkSelections = new MockElement();
const bulkCount = new MockElement();
const bulkEmpty = new MockElement();
const bulkSubmit = new MockElement({ disabled: true });
const bulkForm = formWith(
  [
    ["[data-bulk-confirm]", bulkConfirmation],
    ["[data-bulk-confirm-selections]", bulkSelections],
    ["[data-bulk-confirm-count]", bulkCount],
    ["[data-bulk-confirm-empty]", bulkEmpty],
    ["[data-bulk-confirm-submit]", bulkSubmit],
  ],
  { bulkConfirmableRows: "[3]" },
);

const taxConfirmation = new MockElement();
const taxSubmit = new MockElement({ disabled: true });
const taxForm = formWith([
  ["[data-tax-bulk-confirm]", taxConfirmation],
  ["[data-tax-bulk-submit]", taxSubmit],
]);

const intalev = new MockElement({ value: "code:INT-CFO-1" });
const target = new MockElement({ value: "target-node" });
const cfoIndividualConfirmation = new MockElement({ disabled: true });
const cfoIndividualSubmit = new MockElement({ disabled: true });
const cfoIndividualForm = formWith([
  ["[data-cfo-intalev]", intalev],
  ["[data-cfo-target]", target],
  ["[data-cfo-confirm]", cfoIndividualConfirmation],
  ["[data-cfo-submit]", cfoIndividualSubmit],
]);
const cfoEntry = new MockElement({
  dataset: {
    confirmed: "false",
    entryKey: "entry-1",
    sourceReportingUnit: "АЮ",
    sourceCfo: "АЮ Административный Отдел",
  },
});
cfoEntry.selectors = new Map([
  ["[data-cfo-form]", cfoIndividualForm],
  ["[data-cfo-intalev]", intalev],
  ["[data-cfo-target]", target],
]);

const cfoBulkSelections = new MockElement();
const cfoBulkConfirmation = new MockElement({ disabled: true });
const cfoBulkCount = new MockElement();
const cfoBulkEmpty = new MockElement();
const cfoBulkSubmit = new MockElement({ disabled: true });
const cfoBulkForm = formWith([
  ["[data-cfo-bulk-selections]", cfoBulkSelections],
  ["[data-cfo-bulk-confirm]", cfoBulkConfirmation],
  ["[data-cfo-bulk-count]", cfoBulkCount],
  ["[data-cfo-bulk-empty]", cfoBulkEmpty],
  ["[data-cfo-bulk-submit]", cfoBulkSubmit],
]);

global.document = {
  getElementById(id) {
    return id === "erp-catalog-data"
      ? { textContent: JSON.stringify(catalog) }
      : null;
  },
  querySelector(selector) {
    return new Map([
      ["[data-bulk-confirm-form]", bulkForm],
      ["[data-tax-bulk-form]", taxForm],
      ["[data-cfo-bulk-form]", cfoBulkForm],
    ]).get(selector) || null;
  },
  querySelectorAll(selector) {
    if (selector === '[data-testid="attention-editor"]') return [editor];
    if (selector === "[data-cfo-entry]") return [cfoEntry];
    return [];
  },
};

vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"), {
  filename: process.argv[2],
});

bulkConfirmation.checked = true;
bulkConfirmation.dispatch("change");
taxConfirmation.checked = true;
taxConfirmation.dispatch("change");
cfoBulkConfirmation.checked = true;
cfoBulkConfirmation.dispatch("change");

const result = {
  erp: !bulkSubmit.disabled,
  tax: !taxSubmit.disabled,
  cfo: !cfoBulkSubmit.disabled,
};
if (!result.erp || !result.tax || !result.cfo) {
  throw new Error(`Bulk checkbox state failed: ${JSON.stringify(result)}`);
}
process.stdout.write(JSON.stringify(result));
