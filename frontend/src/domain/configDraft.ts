import type { ActiveConfigPayload, BusinessRuleTemplate } from "../app/types";

export interface ConfigFieldDraft {
  taxProfile: {
    enterpriseName: string;
    taxpayerId: string;
    addressPhone: string;
    bankAccount: string;
  };
  businessRules: {
    templateName: string;
  };
  namingRule: {
    pattern: string;
  };
}

function readString(content: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = content[key];
    if (typeof value === "string") {
      return value;
    }
  }
  return "";
}

export function buildConfigFieldDraft(
  config: ActiveConfigPayload | null,
  templates: BusinessRuleTemplate[],
): ConfigFieldDraft {
  const taxProfileContent = config?.active_snapshot.tax_profile?.content ?? {};
  const businessRuleContent = config?.active_snapshot.business_rules?.content ?? {};
  const namingRuleContent = config?.active_snapshot.naming_rules?.content ?? {};
  return {
    taxProfile: {
      enterpriseName: readString(taxProfileContent, "company_name", "buyer_name"),
      taxpayerId: readString(taxProfileContent, "taxpayer_id", "buyer_tax_no"),
      addressPhone: readString(taxProfileContent, "address_phone", "buyer_address"),
      bankAccount: readString(taxProfileContent, "bank_account", "buyer_bank"),
    },
    businessRules: {
      templateName: readString(businessRuleContent, "template_name") || templates[0]?.template_name || "",
    },
    namingRule: {
      pattern: readString(namingRuleContent, "pattern") || "{{date}}-{{buyer}}-{{amount}}",
    },
  };
}
