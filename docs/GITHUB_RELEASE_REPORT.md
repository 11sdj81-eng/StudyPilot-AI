# StudyPilot AI v1.3 Beta GitHub Release Report

Date: 2026-06-15

## Project

- Name: StudyPilot-AI
- Version: StudyPilot AI v1.3 Beta
- Description: AI-powered personalized learning coach with OCR, RAG, Knowledge Graph, Exam Pattern Engine and Typst PDF generation.
- License: MIT

## Release Scope

This release preparation focused on repository hygiene and GitHub readiness only.

No new product features were added. Upload, RAG, DeepSeek configuration, task management, PDF generation logic, document intelligence worker logic, and Streamlit navigation were not changed.

## Repository Hygiene

- `.gitignore` updated for Python caches, environments, local materials, uploaded data, generated outputs, vector stores, OCR assets, model weights, and large PDFs.
- `sample_outputs/` prepared with lightweight demo artifacts.
- `docs/screenshots/` placeholder created for future public screenshots.
- Large uploaded source PDFs moved to `local_only/`.
- Virtual environments left in place locally but excluded from Git.

## Security Check

- A real DeepSeek key was found in local `.env`.
- `.env` was replaced with `DEEPSEEK_API_KEY=YOUR_API_KEY_HERE`.
- `.env.example` contains placeholder values.
- `.env`, `.env.*`, and `*.env` are ignored, with `.env.example` explicitly allowed.
- Recommendation: rotate the previously exposed DeepSeek key before any public release.

## Large File Check

Large files were found in local virtual environments and uploaded source PDFs.

Actions:

- Uploaded source PDFs were moved to `local_only/data/uploads/course_bb15e787/`.
- Virtual environments were not moved to avoid breaking local setup.
- All detected categories are excluded from Git by `.gitignore`.

## Documentation

Included release documentation:

- `README.md`
- `LICENSE`
- `docs/PROJECT_SHOWCASE.md`
- `docs/RESUME_BULLETS.md`
- `docs/FINAL_ACCEPTANCE_CHECKLIST.md`
- `docs/ARCHITECTURE_V5.md`
- `docs/ACKNOWLEDGEMENTS.md`
- `docs/THIRD_PARTY_NOTICES.md`
- `docs/DI_WORKER_SETUP.md`
- `docs/SECURITY_CHECK.md`
- `docs/LARGE_FILE_CHECK.md`
- `docs/GITHUB_RELEASE_REPORT.md`

## Checks Run

- Python syntax check: passed with `python3 -m compileall app.py core`
- App import check: passed with `python3 -c "import app"`
- Note: importing Streamlit in bare mode prints expected Streamlit runtime warnings; it did not fail.

## GitHub Status

- Local Git repository initialized on branch `main`.
- GitHub CLI was not installed on this machine, so remote repository creation and push could not be completed automatically in this environment.

## Manual Follow-Up

To publish after installing GitHub CLI:

```bash
brew install gh
gh auth login
gh repo create StudyPilot-AI --public --description "AI-powered personalized learning coach with OCR, RAG, Knowledge Graph, Exam Pattern Engine and Typst PDF generation." --source=. --remote=origin --push
```

Or create an empty GitHub repository in the browser, then run:

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## Release Recommendation

The repository is ready for local Git commit and manual GitHub publishing after the API key is rotated. Product development should stop here for v1.3 Beta; future work should move to a new branch or milestone.
