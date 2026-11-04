import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Check,
  FileText,
  Upload,
  X,
} from 'lucide-react';
import type { JobPreference } from '../../types/preference';
import {
  formatFileSize,
  MAX_RESUME_FILE_SIZE_BYTES,
  type ResumeItem,
} from '../../types/resume';

interface ResumeUploadModalProps {
  isOpen: boolean;
  existingResumes: ResumeItem[];
  preferences: JobPreference[];
  isUploading: boolean;
  uploadProgress: number;
  apiError: string | null;
  onClose: () => void;
  onUpload: (options: {
    file: File;
    resumeName: string;
    preferenceIds: string[];
  }) => Promise<void>;
}

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];

function validateCandidateFile(file: File): string | null {
  const lowerName = file.name.toLowerCase();
  const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
  if (!hasValidExt) {
    return 'Unsupported file format. Please select a PDF (.pdf) or Word (.docx) file.';
  }
  if (file.size === 0) {
    return 'The selected file is empty (0 bytes).';
  }
  if (file.size > MAX_RESUME_FILE_SIZE_BYTES) {
    return `File size (${formatFileSize(file.size)}) exceeds the 10 MB maximum limit.`;
  }
  return null;
}

function defaultNameFromFile(filename: string): string {
  return filename
    .replace(/\.(pdf|docx)$/i, '')
    .replace(/[_-]+/g, ' ')
    .trim();
}

export function ResumeUploadModal({
  isOpen,
  existingResumes,
  preferences,
  isUploading,
  uploadProgress,
  apiError,
  onClose,
  onUpload,
}: ResumeUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeName, setResumeName] = useState('');
  const [selectedPreferenceIds, setSelectedPreferenceIds] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isUploading) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isUploading, onClose]);

  if (!isOpen) return null;

  const handleCandidateFile = (file: File) => {
    const error = validateCandidateFile(file);
    if (error) {
      setSelectedFile(null);
      setValidationError(error);
      return;
    }
    setValidationError(null);
    setSelectedFile(file);
    if (!resumeName.trim()) {
      setResumeName(defaultNameFromFile(file.name));
    }
  };

  const handleFileInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleCandidateFile(file);
    }
    event.target.value = '';
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!isUploading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    if (isUploading) return;

    const file = event.dataTransfer.files?.[0];
    if (file) {
      handleCandidateFile(file);
    }
  };

  const togglePreferenceId = (prefId: string) => {
    setSelectedPreferenceIds((prev) =>
      prev.includes(prefId)
        ? prev.filter((id) => id !== prefId)
        : [...prev, prefId],
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedFile) {
      setValidationError('Please select a PDF or DOCX resume file to upload.');
      return;
    }
    const finalName = resumeName.trim() || defaultNameFromFile(selectedFile.name);
    await onUpload({
      file: selectedFile,
      resumeName: finalName,
      preferenceIds: selectedPreferenceIds,
    });
  };

  const displayError = validationError || apiError;

  const duplicateFilenameMatch = selectedFile
    ? existingResumes.find(
        (item) =>
          item.original_filename.toLowerCase() ===
            selectedFile.name.toLowerCase() ||
          (resumeName.trim() !== '' &&
            item.resume_name.toLowerCase() === resumeName.trim().toLowerCase()),
      )
    : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-resume-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
    >
      <div
        aria-hidden="true"
        onClick={() => {
          if (!isUploading) onClose();
        }}
        className="fixed inset-0 bg-black/50 backdrop-blur-[2px]"
      />

      <div className="relative z-10 flex max-h-[90vh] w-full max-w-xl flex-col rounded-2xl border border-line bg-surface shadow-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-6 py-4">
          <div>
            <h2
              id="upload-resume-modal-title"
              className="text-lg font-semibold text-ink"
            >
              Upload Resume
            </h2>
            <p className="mt-0.5 text-xs text-muted">
              Upload a PDF or DOCX resume (maximum 10 MB) and link it to your job
              preferences.
            </p>
          </div>

          <button
            type="button"
            disabled={isUploading}
            onClick={onClose}
            aria-label="Close upload modal"
            className="rounded-xl p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} noValidate className="overflow-y-auto px-6 py-5">
          {displayError && (
            <div
              role="alert"
              className="mb-4 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{displayError}</span>
            </div>
          )}

          {duplicateFilenameMatch && !displayError && (
            <div
              role="status"
              className="mb-4 flex items-start gap-2.5 rounded-xl border border-amber-500/35 bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Duplicate filename warning: A resume named{' '}
                <strong className="font-semibold">
                  “{duplicateFilenameMatch.resume_name}”
                </strong>{' '}
                ({duplicateFilenameMatch.original_filename}) already exists in your
                library. You can rename it below or continue to upload a new copy.
              </span>
            </div>
          )}

          <div className="space-y-4">
            {/* Drag-and-Drop Zone */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileInputChange}
                className="hidden"
              />

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => {
                  if (!isUploading) fileInputRef.current?.click();
                }}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
                  isDragging
                    ? 'border-accent bg-accent-soft'
                    : selectedFile
                      ? 'border-emerald-500/50 bg-emerald-500/5'
                      : 'border-line bg-surface-2 hover:border-subtle/60'
                }`}
              >
                {selectedFile ? (
                  <div className="flex flex-col items-center">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
                      <FileText className="h-5 w-5" strokeWidth={1.9} />
                    </div>
                    <p className="mt-2.5 text-sm font-semibold text-ink">
                      {selectedFile.name}
                    </p>
                    <p className="mt-0.5 text-xs text-muted">
                      {formatFileSize(selectedFile.size)} · Ready to upload
                    </p>
                    <button
                      type="button"
                      disabled={isUploading}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      className="mt-2.5 rounded-lg border border-line bg-surface px-2.5 py-1 text-[11px] font-medium text-muted hover:text-ink"
                    >
                      Choose a different file
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
                      <Upload className="h-5 w-5" strokeWidth={1.9} />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-ink">
                      Drag & drop your resume here, or{' '}
                      <span className="text-accent underline">browse files</span>
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      Supports PDF (.pdf) and Word (.docx) up to 10 MB
                    </p>
                  </>
                )}
              </div>
            </div>

            {/* Upload Progress Bar */}
            {isUploading && (
              <div className="rounded-xl border border-line bg-surface-2 p-3">
                <div className="flex items-center justify-between text-xs font-medium text-ink">
                  <span>Uploading & extracting resume text…</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface">
                  <div
                    className="h-full rounded-full bg-accent transition-all duration-150"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Resume Name Input */}
            <div>
              <label
                htmlFor="upload-resume-name"
                className="block text-xs font-medium text-ink"
              >
                Resume Name
              </label>
              <input
                id="upload-resume-name"
                type="text"
                disabled={isUploading}
                value={resumeName}
                onChange={(e) => setResumeName(e.target.value)}
                placeholder="e.g., Data Analytics Resume — 2026"
                className="mt-1.5 w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2 text-sm text-ink placeholder:text-subtle focus:border-accent focus:outline-none"
              />
            </div>

            {/* Associate with Existing Job Preferences */}
            <div>
              <div className="flex items-center justify-between">
                <span className="block text-xs font-medium text-ink">
                  Associate with Job Preferences (Optional)
                </span>
                <span className="text-[11px] text-muted">
                  {selectedPreferenceIds.length} selected
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-muted">
                Choose which job preferences should use this resume.
              </p>

              {preferences.length === 0 ? (
                <p className="mt-2 rounded-xl border border-line bg-surface-2 p-3 text-xs text-muted">
                  No job preferences created yet. You can link preferences later.
                </p>
              ) : (
                <div className="mt-2 max-h-40 space-y-1.5 overflow-y-auto rounded-xl border border-line bg-surface-2 p-2">
                  {preferences.map((pref) => {
                    const isChecked = selectedPreferenceIds.includes(pref.id);
                    return (
                      <button
                        key={pref.id}
                        type="button"
                        disabled={isUploading}
                        onClick={() => togglePreferenceId(pref.id)}
                        className={`flex w-full items-center justify-between gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                          isChecked
                            ? 'bg-accent-soft font-semibold text-accent-ink'
                            : 'text-ink hover:bg-surface'
                        }`}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <span
                            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                              pref.is_active ? 'bg-emerald-500' : 'bg-subtle'
                            }`}
                          />
                          <span className="truncate">{pref.preference_name}</span>
                        </div>

                        <span
                          className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                            isChecked
                              ? 'border-accent bg-accent text-white'
                              : 'border-line bg-surface'
                          }`}
                        >
                          {isChecked && <Check className="h-3 w-3" strokeWidth={2.5} />}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-line pt-4">
            <button
              type="button"
              disabled={isUploading}
              onClick={onClose}
              className="rounded-xl border border-line bg-surface-2 px-4 py-2 text-xs font-medium text-ink transition-colors hover:border-subtle/50 disabled:opacity-60"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isUploading || !selectedFile}
              className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white shadow-card transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isUploading ? `Uploading (${uploadProgress}%)…` : 'Upload Resume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
