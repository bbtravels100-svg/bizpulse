import React, { useState, useRef } from 'react';
import { Badge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { apiPost } from '../../api/client';
import {
  DatasetSummary,
  DatasetValidationResponse,
  DatasetUploadResponse,
} from '../../types/dataSources';

interface Props {
  isOpen: boolean;
  dataset: DatasetSummary | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const CsvUploadModal: React.FC<Props> = ({ isOpen, dataset, onClose, onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<DatasetValidationResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen || !dataset) return null;

  const resetState = () => {
    setSelectedFile(null);
    setFileContent(null);
    setValidationResult(null);
    setValidationError(null);
    setUploadSuccess(null);
    setUploadError(null);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const processFile = (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setValidationError('Please select a valid .csv file.');
      return;
    }
    setSelectedFile(file);
    setValidationError(null);
    setValidationResult(null);
    setUploadSuccess(null);
    setUploadError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setFileContent(text);
      // Auto-validate immediately upon file read
      runValidation(text, file.name);
    };
    reader.onerror = () => {
      setValidationError('Failed to read the selected file.');
    };
    reader.readAsText(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const runValidation = async (content: string, filename: string) => {
    if (!dataset) return;
    setIsValidating(true);
    setValidationError(null);
    try {
      const res = await apiPost<DatasetValidationResponse>(`/api/datasets/${dataset.id}/validate`, {
        content,
        filename,
      });
      setValidationResult(res);
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : 'Validation request failed.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleUpload = async () => {
    if (!dataset || !selectedFile || !fileContent || !validationResult?.is_valid) return;
    setIsUploading(true);
    setUploadError(null);
    try {
      const res = await apiPost<DatasetUploadResponse>(`/api/datasets/${dataset.id}/upload`, {
        filename: selectedFile.name,
        content: fileContent,
        overwrite: true,
      });
      setUploadSuccess(res.message);
      onSuccess();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Dataset upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const requiredColNames = dataset.columns.filter((c) => c.required).map((c) => c.name);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(8, 15, 32, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !isUploading) handleClose();
      }}
    >
      <div
        style={{
          background: 'var(--bp-card-bg)',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '820px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1)',
          border: '1px solid var(--bp-border)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--bp-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAF9FF',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--bp-navy)', margin: 0 }}>
                Upload & Validate Dataset
              </h2>
              <Badge variant="info">{dataset.name}</Badge>
            </div>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.825rem', color: 'var(--bp-text-muted)' }}>
              Replace <code>{dataset.filename}</code> with validated CSV telemetry.
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={isUploading}
            style={{
              background: 'transparent',
              border: 'none',
              fontSize: '1.25rem',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              color: 'var(--bp-text-muted)',
              padding: '0.25rem 0.5rem',
              borderRadius: '6px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {/* Required Schema Box */}
          <div
            style={{
              padding: '0.85rem 1rem',
              background: '#F8F8FC',
              border: '1px solid var(--bp-border)',
              borderRadius: '8px',
              marginBottom: '1.25rem',
            }}
          >
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.35rem' }}>
              Required Schema Specification:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
              {requiredColNames.map((col) => (
                <span
                  key={col}
                  style={{
                    fontSize: '0.75rem',
                    padding: '0.15rem 0.45rem',
                    background: '#FFFFFF',
                    border: '1px solid var(--bp-border)',
                    borderRadius: '4px',
                    color: 'var(--bp-navy)',
                    fontWeight: 600,
                  }}
                >
                  {col} *
                </span>
              ))}
            </div>
          </div>

          {/* Upload Success Banner */}
          {uploadSuccess && (
            <div
              style={{
                padding: '1.25rem',
                background: '#F0FDF4',
                border: '1px solid #86EFAC',
                borderRadius: '8px',
                marginBottom: '1.25rem',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✅</div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#166534', margin: '0 0 0.5rem 0' }}>
                Upload Complete!
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#15803D', margin: '0 0 1rem 0' }}>
                {uploadSuccess} An immutable backup was created automatically.
              </p>
              <Button size="sm" variant="primary" onClick={handleClose}>
                Return to Data Sources
              </Button>
            </div>
          )}

          {/* Upload Error Banner */}
          {uploadError && (
            <div
              style={{
                padding: '1rem',
                background: '#FEF2F2',
                border: '1px solid #FCA5A5',
                borderRadius: '8px',
                color: '#991B1B',
                fontSize: '0.875rem',
                marginBottom: '1.25rem',
              }}
            >
              <strong>Upload Error:</strong> {uploadError}
            </div>
          )}

          {!uploadSuccess && (
            <>
              {/* Dropzone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: isDragging ? '2px dashed var(--bp-purple)' : '2px dashed var(--bp-border)',
                  background: isDragging ? 'var(--bp-light-purple)' : '#FAFAFE',
                  borderRadius: '10px',
                  padding: '2.5rem 1.5rem',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  marginBottom: '1.25rem',
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📄</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.25rem' }}>
                  {selectedFile ? selectedFile.name : 'Choose a CSV file or drag & drop here'}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
                  {selectedFile
                    ? `${(selectedFile.size / 1024).toFixed(1)} KB — click to choose another file`
                    : 'Standard comma-delimited .csv files up to 25 MB'}
                </div>
              </div>

              {/* Validation Progress */}
              {isValidating && (
                <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--bp-text-muted)' }}>
                  <div
                    style={{
                      display: 'inline-block',
                      width: '24px',
                      height: '24px',
                      border: '3px solid var(--bp-light-purple)',
                      borderTopColor: 'var(--bp-purple)',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite',
                      marginBottom: '0.5rem',
                    }}
                  />
                  <div style={{ fontSize: '0.85rem' }}>Validating schema and mathematical integrity...</div>
                </div>
              )}

              {/* Client error */}
              {validationError && (
                <div
                  style={{
                    padding: '0.85rem 1rem',
                    background: '#FEF2F2',
                    border: '1px solid #FCA5A5',
                    borderRadius: '8px',
                    color: '#991B1B',
                    fontSize: '0.85rem',
                    marginBottom: '1rem',
                  }}
                >
                  <strong>Validation Error:</strong> {validationError}
                </div>
              )}

              {/* Validation Feedback Report */}
              {validationResult && (
                <div style={{ marginTop: '1rem' }}>
                  {/* Status Banner */}
                  <div
                    style={{
                      padding: '1rem 1.25rem',
                      borderRadius: '8px',
                      background: validationResult.is_valid ? '#F0FDF4' : '#FEF2F2',
                      border: `1px solid ${validationResult.is_valid ? '#86EFAC' : '#FCA5A5'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '1rem',
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: '0.95rem',
                          color: validationResult.is_valid ? '#166534' : '#991B1B',
                          marginBottom: '0.2rem',
                        }}
                      >
                        {validationResult.is_valid
                          ? '✓ Schema Verification Passed'
                          : '✕ Validation Failed — Action Required'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: validationResult.is_valid ? '#15803D' : '#B91C1C' }}>
                        {validationResult.is_valid
                          ? `All ${requiredColNames.length} required columns verified. ${validationResult.total_rows} rows ready for ingest.`
                          : `Detected ${validationResult.errors.length} blocking error(s). Please review and correct below.`}
                      </div>
                    </div>
                    <Badge variant={validationResult.is_valid ? 'success' : 'danger'}>
                      {validationResult.is_valid ? 'Valid CSV' : 'Invalid CSV'}
                    </Badge>
                  </div>

                  {/* Errors List */}
                  {validationResult.errors.length > 0 && (
                    <div
                      style={{
                        padding: '1rem',
                        background: '#FFF5F5',
                        border: '1px solid #FED7D7',
                        borderRadius: '8px',
                        marginBottom: '1rem',
                      }}
                    >
                      <div style={{ fontWeight: 700, color: '#C53030', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                        Blocking Errors ({validationResult.errors.length}):
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.825rem', color: '#9B2C2C' }}>
                        {validationResult.errors.map((err, idx) => (
                          <li key={idx} style={{ marginBottom: '0.35rem' }}>
                            {err.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Warnings List */}
                  {validationResult.warnings.length > 0 && (
                    <div
                      style={{
                        padding: '0.85rem 1rem',
                        background: '#FFFBEB',
                        border: '1px solid #FDE68A',
                        borderRadius: '8px',
                        marginBottom: '1rem',
                      }}
                    >
                      <div style={{ fontWeight: 700, color: '#B45309', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                        Warnings ({validationResult.warnings.length}):
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#92400E' }}>
                        {validationResult.warnings.map((warn, idx) => (
                          <li key={idx} style={{ marginBottom: '0.25rem' }}>
                            {warn.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Sample preview of uploaded data */}
                  {validationResult.preview_rows.length > 0 && (
                    <div style={{ marginTop: '1rem' }}>
                      <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--bp-navy)', marginBottom: '0.4rem' }}>
                        Parsed File Preview (First {validationResult.preview_rows.length} rows):
                      </div>
                      <div style={{ overflowX: 'auto', border: '1px solid var(--bp-border)', borderRadius: '6px' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                          <thead>
                            <tr style={{ background: '#F8F8FC', borderBottom: '1px solid var(--bp-border)' }}>
                              {validationResult.detected_columns.map((c) => (
                                <th key={c} style={{ padding: '0.5rem 0.75rem', textAlign: 'left', color: 'var(--bp-navy)' }}>
                                  {c}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {validationResult.preview_rows.map((row, rIdx) => (
                              <tr key={rIdx} style={{ borderBottom: '1px solid var(--bp-border)' }}>
                                {validationResult.detected_columns.map((c) => (
                                  <td key={c} style={{ padding: '0.5rem 0.75rem', color: 'var(--bp-navy)', whiteSpace: 'nowrap' }}>
                                    {String(row[c] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--bp-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#FAF9FF',
          }}
        >
          <div style={{ fontSize: '0.8rem', color: 'var(--bp-text-muted)' }}>
            Safety protocol: automatic <code>.bak</code> snapshot created prior to write.
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button size="sm" variant="secondary" onClick={handleClose} disabled={isUploading}>
              Cancel
            </Button>
            {validationResult?.is_valid && !uploadSuccess && (
              <Button
                size="sm"
                variant="primary"
                onClick={handleUpload}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading & Replacing...' : 'Apply & Ingest Dataset'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
