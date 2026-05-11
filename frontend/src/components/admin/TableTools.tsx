import type { ReactElement } from "react";

export type SortDirection = "asc" | "desc";
export type SortState<Key extends string> = {
  key: Key;
  direction: SortDirection;
} | null;

export type SortableValue = string | number | boolean | null | undefined;

export type CsvColumn<Row> = {
  header: string;
  value: (row: Row) => SortableValue;
};

type SortHeaderProps<Key extends string> = {
  label: string;
  sortKey: Key;
  sort: SortState<Key>;
  onSort: (key: Key) => void;
  className?: string;
};

function normalizeSortValue(value: SortableValue): string | number {
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (value == null) return "";

  const text = String(value).trim();
  const timestamp = Date.parse(text);
  if (text && !Number.isNaN(timestamp) && /[-/:T]/.test(text)) {
    return timestamp;
  }

  return text.toLocaleLowerCase();
}

export function nextSortState<Key extends string>(
  current: SortState<Key>,
  key: Key
): SortState<Key> {
  if (!current || current.key !== key) {
    return { key, direction: "asc" };
  }

  if (current.direction === "asc") {
    return { key, direction: "desc" };
  }

  return null;
}

export function sortRows<Row, Key extends string>(
  rows: Row[],
  sort: SortState<Key>,
  accessors: Record<Key, (row: Row) => SortableValue>
): Row[] {
  if (!sort) return rows;

  const accessor = accessors[sort.key];
  if (!accessor) return rows;

  const direction = sort.direction === "asc" ? 1 : -1;

  return [...rows].sort((a, b) => {
    const aValue = normalizeSortValue(accessor(a));
    const bValue = normalizeSortValue(accessor(b));

    if (typeof aValue === "number" && typeof bValue === "number") {
      return (aValue - bValue) * direction;
    }

    return String(aValue).localeCompare(String(bValue), undefined, {
      numeric: true,
      sensitivity: "base",
    }) * direction;
  });
}

export function SortHeader<Key extends string>({
  label,
  sortKey,
  sort,
  onSort,
  className = "",
}: SortHeaderProps<Key>): ReactElement {
  const active = sort?.key === sortKey;
  const indicator = active ? (sort.direction === "asc" ? "A-Z" : "Z-A") : "--";

  return (
    <button
      type="button"
      onClick={() => onSort(sortKey)}
      className={[
        "inline-flex items-center gap-1 rounded-lg px-1 py-1 text-left font-bold text-black/70 transition hover:text-[var(--navy)] focus:outline-none focus:ring-2 focus:ring-[var(--gold)]/40",
        active ? "text-[var(--navy)]" : "",
        className,
      ].join(" ")}
      aria-label={`Sort by ${label}`}
    >
      <span>{label}</span>
      <span className="text-[10px] text-[var(--gold)]">{indicator}</span>
    </button>
  );
}

function csvCell(value: SortableValue): string {
  const text = value == null ? "" : String(value).replace(/\r?\n/g, " ");
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function buildCsv<Row>(rows: Row[], columns: CsvColumn<Row>[]): string {
  const header = columns.map((column) => csvCell(column.header)).join(",");
  const body = rows.map((row) =>
    columns.map((column) => csvCell(column.value(row))).join(",")
  );

  return [header, ...body].join("\r\n");
}

export function downloadCsv<Row>(
  rows: Row[],
  columns: CsvColumn<Row>[],
  filename: string
) {
  const content = `\ufeff${buildCsv(rows, columns)}`;
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function reportFilename(prefix: string): string {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `${prefix}-${stamp}.csv`;
}

export const adminInputClass =
  "rounded-xl border border-black/10 bg-white px-4 py-3 outline-none focus:border-[var(--gold)]";

export const adminPrimaryButtonClass =
  "rounded-xl bg-[var(--navy)] px-5 py-3 font-extrabold text-white shadow-[0_6px_0_rgba(0,0,0,0.22)] transition hover:-translate-y-0.5 hover:shadow-[0_8px_0_rgba(0,0,0,0.18)] active:translate-y-0.5 active:shadow-[0_3px_0_rgba(0,0,0,0.24)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0";

export const adminGoldButtonClass =
  "rounded-xl bg-[var(--gold)] px-5 py-3 font-extrabold text-black shadow-[0_6px_0_rgba(0,0,0,0.22)] transition hover:-translate-y-0.5 hover:shadow-[0_8px_0_rgba(0,0,0,0.18)] active:translate-y-0.5 active:shadow-[0_3px_0_rgba(0,0,0,0.24)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0";

export const adminSecondaryButtonClass =
  "rounded-xl border border-black/10 bg-white px-4 py-3 font-semibold text-black/75 shadow-[0_4px_0_rgba(0,0,0,0.08)] transition hover:-translate-y-0.5 hover:border-[var(--gold)] active:translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0";
