import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "../src/app/providers";
import type { ActiveConfigPayload, BusinessRuleTemplate } from "../src/app/types";
import {
  ConfigFieldEditor,
  buildConfigFieldDraft,
  type ConfigFieldDraft,
} from "../src/components/settings/ConfigFieldEditor";

const templates: BusinessRuleTemplate[] = [
  {
    template_name: "strict_v1",
    display_name: "严格校验",
    minimum_confidence: 0.92,
  },
  {
    template_name: "balanced_v1",
    display_name: "平衡模式",
    minimum_confidence: 0.85,
  },
];

const activeConfig: ActiveConfigPayload = {
  active_snapshot: {
    tax_profile: {
      id: "tax-v1",
      version_no: "tax-v1",
      content: {
        company_name: "示例科技有限公司",
        taxpayer_id: "91310000123456789X",
        address_phone: "上海市徐汇区示例路 1 号 021-12345678",
        bank_account: "招商银行上海示例支行 1234567890",
      },
      changed_by: "后端可信身份",
      change_summary: "初始化税务档案",
      change_reason: "首次配置",
    },
    business_rules: {
      id: "rules-v1",
      version_no: "rules-v1",
      content: {
        template_name: "strict_v1",
        display_name: "严格校验",
        minimum_confidence: 0.92,
      },
      changed_by: "后端可信身份",
      change_summary: "初始化业务规则",
      change_reason: "首次配置",
    },
    naming_rules: {
      id: "naming-v1",
      version_no: "naming-v1",
      content: {
        pattern: "{{date}}-{{seller}}-{{amount}}",
      },
      changed_by: "后端可信身份",
      change_summary: "初始化命名规则",
      change_reason: "首次配置",
    },
  },
  active_versions: {},
  setup_status: {
    complete: true,
    default_business_rule_templates: {
      strict_v1: templates[0],
      balanced_v1: templates[1],
    },
    missing_required_fields: {
      tax_profile: [],
      business_rules: [],
      naming_rules: [],
    },
  },
};

function renderEditor(initialDraft: ConfigFieldDraft, onSubmit = vi.fn()) {
  render(
    <AppProviders>
      <ConfigFieldEditor
        mode="settings_edit"
        initialDraft={initialDraft}
        templates={templates}
        saving={false}
        onSubmit={onSubmit}
      />
    </AppProviders>,
  );
  return onSubmit;
}

describe("ConfigFieldEditor", () => {
  it("builds one field draft from active config for first-run and settings edit reuse", () => {
    expect(buildConfigFieldDraft(activeConfig, templates)).toEqual({
      taxProfile: {
        enterpriseName: "示例科技有限公司",
        taxpayerId: "91310000123456789X",
        addressPhone: "上海市徐汇区示例路 1 号 021-12345678",
        bankAccount: "招商银行上海示例支行 1234567890",
      },
      businessRules: {
        templateName: "strict_v1",
      },
      namingRule: {
        pattern: "{{date}}-{{seller}}-{{amount}}",
      },
    });
  });

  it("edits tax profile, review policy, and naming fields through the shared editor", async () => {
    const onSubmit = renderEditor(buildConfigFieldDraft(activeConfig, templates));

    expect(await screen.findByText("税务档案")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("企业名称"), { target: { value: "上海示例科技有限公司" } });
    fireEvent.change(screen.getByLabelText("纳税人识别号（税号）"), { target: { value: "91310000999999999X" } });
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("业务规则模板")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText("模板方案"));
    fireEvent.click(await screen.findByText("平衡模式"));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("命名规则")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText("归档命名方式"));
    fireEvent.click(await screen.findByText("日期-购方-金额"));
    fireEvent.click(screen.getByRole("button", { name: "下一步" }));

    expect(await screen.findByText("摘要确认")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "保存配置" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({
        taxProfile: {
          enterpriseName: "上海示例科技有限公司",
          taxpayerId: "91310000999999999X",
          addressPhone: "上海市徐汇区示例路 1 号 021-12345678",
          bankAccount: "招商银行上海示例支行 1234567890",
        },
        businessRules: {
          templateName: "balanced_v1",
        },
        namingRule: {
          pattern: "{{date}}-{{buyer}}-{{amount}}",
        },
      });
    });
  });
});
