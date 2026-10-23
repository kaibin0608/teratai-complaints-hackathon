/** CSV text → rows (RFC 4180: quoted cells may hold commas, doubled quotes and line breaks). Blank lines are skipped. */
export function parseCsv(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let cell = ''
  let quoted = false

  const endCell = () => {
    row.push(cell)
    cell = ''
  }
  const endRow = () => {
    endCell()
    if (row.some((value) => value.trim() !== '')) rows.push(row)
    row = []
  }

  for (let i = 0; i < text.length; i++) {
    const char = text[i]
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') {
        cell += '"'
        i++
      } else if (char === '"') quoted = false
      else cell += char
    } else if (char === '"') quoted = true
    else if (char === ',') endCell()
    else if (char === '\n') endRow()
    else if (char !== '\r') cell += char
  }
  endRow()
  return rows
}

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
