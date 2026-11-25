import { useRef, useState } from 'react';

import { formatFileSize, validatePdfFile } from '../../utils/fileValidation';

interface UploadZoneProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export function UploadZone({ file, onFileSelect, disabled = false }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  function handleFile(selected: File | null) {
    if (!selected) return;

    const error = validatePdfFile(selected);
    if (error) {
      setLocalError(error);
      return;
    }

    setLocalError(null);
    onFileSelect(selected);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (disabled) return;

    const dropped = event.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }

  function handleRemove() {
    onFileSelect(null);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = '';
  }

  return (
    <div className="space-y-4">
      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
            dragActive
              ? 'border-indigo-400 bg-indigo-500/10'
              : 'border-slate-700 bg-slate-900/40 hover:border-slate-500'
          } ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          role="button"
          tabIndex={0}
          aria-label="Upload resume PDF"
        >
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-indigo-500/15 text-2xl">
            📄
          </div>
          <p className="mb-1 text-lg font-medium text-white">Drag & drop your resume PDF</p>
          <p className="mb-4 text-sm text-slate-400">or click to browse files</p>
          <button
            type="button"
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              inputRef.current?.click();
            }}
            className="rounded-lg bg-indigo-500 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Browse PDF
          </button>
          <p className="mt-4 text-xs text-slate-500">PDF only · Max 5 MB</p>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate font-medium text-white">{file.name}</p>
              <p className="text-sm text-slate-400">{formatFileSize(file.size)}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={disabled}
                onClick={() => inputRef.current?.click()}
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 transition-colors hover:border-slate-400 hover:text-white disabled:opacity-60"
              >
                Replace
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={handleRemove}
                className="rounded-lg border border-red-500/40 px-4 py-2 text-sm text-red-300 transition-colors hover:border-red-400 hover:text-red-200 disabled:opacity-60"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />

      {localError && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {localError}
        </p>
      )}
    </div>
  );
}
