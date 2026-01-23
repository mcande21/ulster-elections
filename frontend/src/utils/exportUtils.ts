import html2canvas from 'html2canvas';

/**
 * Escapes CSV field values to handle special characters
 */
function escapeCSVValue(value: any): string {
  if (value === null || value === undefined) {
    return '';
  }

  const stringValue = String(value);

  // If value contains comma, quote, or newline, wrap in quotes and escape existing quotes
  if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
}

/**
 * Converts array of objects to CSV string and triggers download
 */
export function exportToCSV<T extends Record<string, any>>(
  data: T[],
  filename: string,
  columns?: { key: keyof T; header: string }[]
): void {
  if (!data || data.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Determine columns to export
  const columnsToExport = columns || Object.keys(data[0]).map(key => ({
    key: key as keyof T,
    header: key
  }));

  // Build CSV header row
  const headerRow = columnsToExport.map(col => escapeCSVValue(col.header)).join(',');

  // Build CSV data rows
  const dataRows = data.map(row =>
    columnsToExport.map(col => escapeCSVValue(row[col.key])).join(',')
  );

  // Combine header and data
  const csvContent = [headerRow, ...dataRows].join('\n');

  // Create blob and trigger download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  triggerDownload(blob, filename.endsWith('.csv') ? filename : `${filename}.csv`);
}

/**
 * Captures HTML element as PNG and triggers download
 */
export async function exportToPNG(
  element: HTMLElement,
  filename: string
): Promise<void> {
  try {
    const canvas = await html2canvas(element, {
      scale: 2, // Higher quality
      useCORS: true,
      logging: false
    });

    // Convert canvas to blob
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Failed to convert canvas to blob'));
        }
      }, 'image/png');
    });

    triggerDownload(blob, filename.endsWith('.png') ? filename : `${filename}.png`);
  } catch (error) {
    console.error('Failed to export PNG:', error);
    throw error;
  }
}

/**
 * Triggers browser download for a blob
 */
function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
