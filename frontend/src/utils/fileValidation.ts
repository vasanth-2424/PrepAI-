const MAX_FILE_SIZE_MB = 5;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export function validatePdfFile(file: File): string | null {
  if (!file) {
    return 'No file selected.';
  }

  if (file.size === 0) {
    return 'The selected file is empty.';
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return `File size must be under ${MAX_FILE_SIZE_MB} MB.`;
  }

  const isPdf =
    file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');

  if (!isPdf) {
    return 'Only PDF files are accepted.';
  }

  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
