import { describe, expect, it } from "vitest";

import {
  getResultBucket,
  getReviewLabel,
  isInvoiceProcessing,
  toDisplayStatusFilter,
} from "../src/domain/presentation";
import type { InvoiceSummary } from "../src/app/types";

function invoice(overrides: Partial<InvoiceSummary>): InvoiceSummary {
  return {
    id: "invoice-1",
    batch_id: "batch-1",
    original_filename: "a.pdf",
    renamed_filename: null,
    storage_path_original: null,
    storage_path_renamed: null,
    invoice_code: null,
    invoice_number: null,
    seller_name: null,
    buyer_name: null,
    buyer_tax_no: null,
    invoice_date: null,
    invoice_amount: null,
    processing_status: "completed",
    system_decision: "suggested_pass",
    review_status: null,
    artifact_status: null,
    archive_status: null,
    stable_status: {
      processing_status: "completed",
      review_status: "pending",
      archive_status: "pending",
    },
    duplicate_flag: false,
    duplicate_group_key: null,
    risk_flags: [],
    display_status: "suggested_pass",
    business_bucket: "suggested_pass",
    business_bucket_label: "建议通过",
    basic_compliance_status: "pass",
    business_compliance_status: "pass",
    final_decision: "suggested_pass",
    decision_reasons: [],
    suggested_actions: [],
    problem_count: 0,
    failure_reason: null,
    preview_path: null,
    attachments: [],
    ...overrides,
  };
}

describe("Vue result presentation", () => {
  it("uses canonical bucket values for filters", () => {
    expect(toDisplayStatusFilter("review_required")).toBe("review_required");
    expect(toDisplayStatusFilter("all")).toBeUndefined();
  });

  it("does not treat processing invoices as final missing data", () => {
    expect(isInvoiceProcessing("ocr_processing")).toBe(true);
    expect(getReviewLabel(invoice({ processing_status: "ocr_processing" }))).toBe("等待识别");
  });

  it("maps duplicate invoices to the current-batch duplicate bucket", () => {
    expect(getResultBucket(invoice({ duplicate_flag: true }))).toBe("duplicate_in_batch");
  });
});
