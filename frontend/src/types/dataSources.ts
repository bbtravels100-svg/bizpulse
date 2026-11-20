export interface DatasetColumnInfo {
  name: string;
  data_type: 'date' | 'string' | 'integer' | 'float' | 'unknown';
  required: boolean;
  sample_values: (string | number | boolean | null)[];
  missing_count: number;
}

export interface DatasetSummary {
  id: string;
  name: string;
  description: string;
  filename: string;
  file_path: string;
  record_count: number;
  file_size_bytes: number;
  last_modified: string | null;
  status: 'healthy' | 'missing' | 'validation_error' | 'error';
  columns: DatasetColumnInfo[];
  source_type: string;
  version?: number;
  last_reloaded_at?: string | null;
  content_hash?: string | null;
}

export interface DatasetPreviewResponse {
  dataset_id: string;
  name: string;
  record_count: number;
  columns: DatasetColumnInfo[];
  rows: Record<string, any>[];
  total_columns: number;
  duplicate_rows_count: number;
}

export interface ValidationMessage {
  type: 'error' | 'warning';
  field?: string | null;
  message: string;
  row_index?: number | null;
}

export interface DatasetValidationRequest {
  content: string;
  filename?: string;
}

export interface DatasetValidationResponse {
  dataset_id: string;
  is_valid: boolean;
  total_rows: number;
  errors: ValidationMessage[];
  warnings: ValidationMessage[];
  detected_columns: string[];
  missing_columns: string[];
  extra_columns: string[];
  preview_rows: Record<string, any>[];
}

export interface DatasetUploadRequest {
  filename: string;
  content: string;
  overwrite?: boolean;
}

export interface DatasetUploadResponse {
  status: string;
  message: string;
  dataset_id: string;
  record_count: number;
  file_size_bytes: number;
  backup_created: boolean;
  version?: number;
  reloaded_at?: string;
}

export interface IntegrationCard {
  id: string;
  name: string;
  category: string;
  icon: string;
  description: string;
  status: 'active' | 'coming_soon' | 'planned';
  supportedEntities: string[];
}
