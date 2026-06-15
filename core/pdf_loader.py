from pathlib import Path

import fitz


def load_pdf_pages(file_path: str | Path, resource: dict | None = None) -> list[dict]:
    path = Path(file_path)
    pages: list[dict] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            pages.append(
                {
                    "text": text,
                    "page": index,
                    "filename": path.name,
                    "resource_type": (resource or {}).get("resource_type", ""),
                    "resource_id": (resource or {}).get("resource_id", ""),
                    "course_id": (resource or {}).get("course_id", ""),
                }
            )
    return pages
