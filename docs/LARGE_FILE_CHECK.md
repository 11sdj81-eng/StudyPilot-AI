# Large File Check

Date: 2026-06-15

## Result

Files larger than 20 MB were found in three categories:

- Python virtual environments under `.venv/` and `tools/document_intelligence_worker/.venv-di/`
- User-uploaded source PDFs under `data/uploads/`
- Local model/weight style artifacts such as `*.pt`

## Action Taken

- Two large uploaded source PDFs were moved to `local_only/data/uploads/course_bb15e787/`.
- Virtual environment files were left in place to avoid breaking the local development environment, but they are excluded by `.gitignore`.
- Model weights and generated data are excluded by `.gitignore`.

## Release Policy

The GitHub repository should only include source code, lightweight documentation, and curated sample outputs. Original textbooks, scanned PDFs, generated datasets, vector stores, local caches, virtual environments, and model weights must stay local-only.
