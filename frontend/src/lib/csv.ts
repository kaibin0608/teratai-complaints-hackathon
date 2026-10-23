/** Rows → CSV text (every cell quoted, so commas and line breaks in replies are safe). */
export function toCsv(rows: readonly (readonly (string | number | null)[])[]): string {
  return rows.map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n')
}

/** Save rows as a CSV file from the browser (a leading BOM keeps Excel from mangling Malay text). */
export function downloadCsv(filename: string, rows: readonly (readonly (string | number | null)[])[]): void {
  const url = URL.createObjectURL(new Blob(['﻿', toCsv(rows)], { type: 'text/csv;charset=utf-8' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  link.click()
  URL.revokeObjectURL(url)
}
