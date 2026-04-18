export type RuleKind = "tax_profile" | "business_rules" | "naming_rules";

export interface CurrentActor {
  actor_id: string;
  display_name: string;
  roles: string[];
}

export interface ProviderDiagnostic {
  provider_name?: string | null;
  provider_version?: string | null;
  provider_error_code?: string | null;
  [key: string]: unknown;
}

export interface RecentFailure {
  invoice_id: string;
  original_filename: string;
  failure_reason: string | null;
  failure_stage?: string | null;
  error_code?: string | null;
  retryable?: boolean;
  parse_source?: string | null;
  provider_diagnostic?: ProviderDiagnostic;
}

export interface BatchProgress {
  batch_id: string;
  batch_no: string;
  stage_code: string;
  stage_text: string;
  progress_percent: number;
  total_files: number;
  completed_files: number;
  processing_files: number;
  failed_files: number;
  suggested_pass_count: number;
  suggested_pass_total_amount: string;
  recent_failures: RecentFailure[];
}

export interface ExportJob {
  id?: string;
  job_id?: string;
  export_type: string;
  status: string;
  output_path: string;
  created_by?: string;
  created_at?: string;
  summary: Record<string, unknown>;
}

export interface RuleSnapshotEntry {
  id: string;
  version_no: string;
  content: Record<string, unknown>;
  changed_by: string;
  change_summary: string;
  change_reason: string;
}

export type ActiveSnapshot = Partial<Record<RuleKind, RuleSnapshotEntry | null>>;

export interface Batch {
  id: string;
  batch_no: string;
  created_at: string;
  created_by: string;
  status: string;
  total_files: number;
  completed_files: number;
  processing_files: number;
  failed_files: number;
  suggested_pass_count: number;
  suggested_pass_total_amount: string;
  export_manifest_path: string | null;
  invoice_file_count: number;
  attachment_file_count: number;
  progress?: BatchProgress;
  snapshot?: ActiveSnapshot;
  export_jobs?: ExportJob[];
}

export interface InvoiceSummary {
  id: string;
  batch_id: string;
  original_filename: string;
  renamed_filename: string | null;
  storage_path_original: string | null;
  storage_path_renamed: string | null;
  invoice_code: string | null;
  invoice_number: string | null;
  seller_name: string | null;
  buyer_name: string | null;
  buyer_tax_no: string | null;
  invoice_date: string | null;
  invoice_amount: string | null;
  parse_source?: string | null;
  processing_status: string | null;
  system_decision: string | null;
  review_status: string | null;
  artifact_status: string | null;
  duplicate_flag: boolean;
  duplicate_group_key: string | null;
  risk_flags: string[];
  display_status: string;
  basic_compliance_status: string;
  business_compliance_status: string;
  final_decision: string;
  decision_reasons: string[];
  suggested_actions: string[];
  problem_count: number;
  failure_reason: string | null;
  preview_path: string | null;
}

export interface DocumentEvidence {
  id: string;
  source_type: string;
  raw_text: string;
  pages: Array<Record<string, unknown>>;
  text_blocks: Array<Record<string, unknown>>;
  table_lines: Array<Record<string, unknown>>;
  field_candidates: Array<Record<string, unknown>>;
  confidence_summary: Record<string, unknown>;
  provider_name: string | null;
  provider_version: string | null;
  provider_error_code: string | null;
}

export interface ExtractedField {
  id: string;
  field_name: string;
  extracted_value: string | null;
  normalized_value: string | null;
  confidence: string | null;
  page_no: number | null;
  source_fragment: string | null;
  bbox: Record<string, unknown> | null;
}

export interface FieldCheck {
  id: string;
  field_name: string;
  expected_value: string | null;
  actual_value: string | null;
  match_result: string | null;
  reason: string | null;
}

export interface ReviewAction {
  id: string;
  review_action: string;
  review_note: string | null;
  reviewed_by: string;
  reviewed_at: string;
}

export interface InvoiceDetail extends InvoiceSummary {
  last_error_stage: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  retryable: boolean;
  provider_diagnostic: ProviderDiagnostic;
  evidence_items: DocumentEvidence[];
  extracted_fields: ExtractedField[];
  field_checks: FieldCheck[];
  review_actions: ReviewAction[];
}

export interface BatchRetryResult {
  batch_id: string;
  retried_invoice_ids: string[];
}

export interface InvoiceRetryResult {
  invoice_id: string;
  batch_id: string;
  retried: boolean;
}

export interface BatchInvoiceListing {
  items: InvoiceSummary[];
  status_counts: Record<string, number>;
  batch_summary: {
    count: number;
    total_amount: string;
  };
  filtered_summary: {
    count: number;
    total_amount: string;
  };
}

export interface RuleVersion {
  id: string;
  kind: RuleKind;
  version_no: string;
  content: Record<string, unknown>;
  is_active: boolean;
  change_summary: string;
  changed_by: string;
  changed_at: string;
  change_reason: string;
}

export interface ActiveConfigPayload {
  active_snapshot: ActiveSnapshot;
  active_versions: Partial<Record<RuleKind, RuleVersion>>;
}
