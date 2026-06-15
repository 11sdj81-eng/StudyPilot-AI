from core.config import CHUNK_OVERLAP, CHUNK_SIZE


def split_text_pages(
    pages: list[dict],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    chunks: list[dict] = []
    step = max(1, chunk_size - chunk_overlap)
    for page in pages:
        text = page["text"]
        if len(text) <= chunk_size:
            chunks.append({**page, "chunk_id": f"{page['filename']}_p{page['page']}_0"})
            continue
        for offset in range(0, len(text), step):
            piece = text[offset : offset + chunk_size].strip()
            if not piece:
                continue
            chunks.append(
                {
                    **page,
                    "text": piece,
                    "chunk_id": f"{page['filename']}_p{page['page']}_{offset}",
                }
            )
    return chunks
