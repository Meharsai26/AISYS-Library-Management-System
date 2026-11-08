const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export type Book = {
  id: string;
  title: string;
  author: string | null;
  isbn: string | null;
};

export type Item = {
  id: string;
  bib_id: string;
  accession_number: string;
  status: string;
  is_reference: boolean;
};

export type Member = {
  id: string;
  card_number: string;
  display_name: string;
  status: string;
};

export async function api<T>(
  path: string,
  token?: string,
  method = "GET",
  body?: unknown
): Promise<T> {
  const response = await fetch(`${BASE}/api/v1${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`
    );
  }

  return data as T;
}
