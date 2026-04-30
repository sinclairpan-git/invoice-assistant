const TOKEN_LABELS: Record<string, string> = {
  date: "日期",
  buyer: "购方",
  seller: "销售方",
  amount: "金额",
  invoice_no: "发票号码",
  invoice_number: "发票号码",
};

export const NAMING_PATTERN_PRESETS = [
  {
    value: "{{date}}-{{buyer}}-{{amount}}",
    label: "日期-购方-金额",
    description: "适合按报销时间和购方快速检索",
  },
  {
    value: "{{date}}-{{seller}}-{{amount}}",
    label: "日期-销售方-金额",
    description: "适合按供应商归档和对账",
  },
  {
    value: "{{date}}-{{invoice_no}}-{{amount}}",
    label: "日期-发票号码-金额",
    description: "适合按发票号码追溯原票",
  },
  {
    value: "{{buyer}}-{{date}}-{{amount}}",
    label: "购方-日期-金额",
    description: "适合多主体并行处理时区分购方",
  },
] as const;

function normalizeText(value: string | null | undefined): string {
  return value?.trim() ?? "";
}

export function describeBusinessTemplate(
  templateName: string | null | undefined,
  displayName: string | null | undefined,
): string {
  return normalizeText(displayName) || normalizeText(templateName) || "--";
}

export function describeBusinessTemplateTone(
  templateName: string | null | undefined,
  displayName: string | null | undefined,
): string {
  const normalized = `${normalizeText(templateName)} ${normalizeText(displayName)}`.toLowerCase();
  if (
    normalized.includes("保守") ||
    normalized.includes("strict") ||
    normalized.includes("conservative")
  ) {
    return "更严格，优先拦住可疑票据";
  }
  if (
    normalized.includes("平衡") ||
    normalized.includes("常规") ||
    normalized.includes("balanced")
  ) {
    return "更均衡，适合日常批量处理";
  }
  return "按模板自动平衡系统建议与人工确认量";
}

export function describeNamingPattern(pattern: string | null | undefined): string {
  const normalized = normalizeText(pattern);
  if (!normalized) {
    return "待填写";
  }

  const preset = NAMING_PATTERN_PRESETS.find((item) => item.value === normalized);
  if (preset) {
    return preset.label;
  }

  const tokens = Array.from(normalized.matchAll(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g))
    .map((match) => TOKEN_LABELS[match[1]])
    .filter((value): value is string => Boolean(value));

  if (tokens.length > 0) {
    return `${tokens.join("-")}（保留当前顺序）`;
  }

  return "保留当前命名方式";
}

export function getNamingPatternOptions(pattern: string | null | undefined) {
  const normalized = normalizeText(pattern);
  const options: Array<{ value: string; label: string }> = NAMING_PATTERN_PRESETS.map((item) => ({
    value: item.value,
    label: item.label,
  }));

  if (normalized && !options.some((item) => item.value === normalized)) {
    options.unshift({
      value: normalized,
      label: describeNamingPattern(normalized),
    });
  }

  return options;
}

export function getNamingPatternDescription(pattern: string | null | undefined): string {
  const normalized = normalizeText(pattern);
  const preset = NAMING_PATTERN_PRESETS.find((item) => item.value === normalized);
  if (preset) {
    return preset.description;
  }
  return "系统会按当前命名方式自动生成建议文件名。";
}
