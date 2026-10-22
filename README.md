# CodeAlpha_snapsort — SnapSort Smart Image Organizer 📁✨

**SnapSort** is a modern, reliable Python automation application built with **Streamlit**. It solves the repetitive daily chore of discovering and organizing scattered `.jpg` and `.jpeg` images across folders and safely moving them into a designated destination directory.

Designed as an end-to-end task automation project, SnapSort features real file-handling operations, automatic collision prevention, audit trails, and dual execution modes (Local Machine & Sandboxed Cloud Demo).

---

## 🌟 Key Features

- **Automated Image Ingestion**: Detects `.jpg` and `.jpeg` images case-insensitively (`.jpg`, `.JPG`, `.jpeg`, `.JPEG`).
- **Zero-Overwrite Collision Protection**: If a file with the same name already exists in the destination, SnapSort automatically renames the incoming file (e.g., `photo.jpg` → `photo_1.jpg`, `photo_2.jpg`).
- **Preserves Unrelated Files**: Files of any other extension (`.png`, `.pdf`, `.txt`, `.csv`, `.docx`) remain completely untouched in the source directory.
- **Recursive Directory Scan (Optional)**: Can scan deeply nested subfolders when explicitly enabled, or stick strictly to the top-level directory.
- **Strict Safety Boundaries**:
  - Rejects identical source and destination directories.
  - Rejects circular loops (destination located inside source during recursive scanning).
  - Never touches root directories (`C:\`, `/`).
  - Requires explicit user checkbox confirmation before performing any write operations.
  - Never executes shell commands from user input.
- **Dual Operating Modes**:
  - **🖥️ Local Folder Mode**: Operates on real directories on your computer.
  - **🧪 Interactive Demo Sandbox**: Built-in test sandbox that synthesizes sample photos using Pillow so visitors can test the app safely in the cloud or in classroom demos without exposing personal files.
- **Live Visual Progress & Metrics**: Real-time progress bar, individual file status badges (`MOVED`, `SKIPPED`, `ERROR`), and an activity audit log with exact timestamps.
- **Image Gallery Preview**: Preview organized photos directly in the dashboard.

---

## 📸 Screenshots

*(To add real screenshots to your GitHub repository, take screenshots while running the app, save them in an `assets/` folder, and reference them below.)*

```
+---------------------------------------------------------------------------------+
|  [📁] SnapSort — Smart Image Organizer            [ 🧪 Interactive Demo Sandbox ] |
+---------------------------------------------------------------------------------+
|  📂 Folder Configuration                                                        |
|  Source:      [ sample_data/source_demo                                     ]   |
|  Destination: [ sample_data/dest_demo                                       ]   |
|  [ ] Include images from subfolders      [x] Auto-create destination folder     |
|                                                                                 |
|  [🔍 Scan & Preview Source]                                                     |
|                                                                                 |
|  [x] I confirm that I want to move all .jpg and .jpeg images...                 |
|  [⚡ Organize Images (Primary Button)]                                           |
+---------------------------------------------------------------------------------+
|  📊 Task Statistics                                                             |
|  [ Images Found: 5 ]  [ Images Moved: 5 ]  [ Skipped: 0 ]  [ Errors: 0 ]         |
+---------------------------------------------------------------------------------+
|  [📑 File Operations Result]   [🕒 Activity Audit Log]   [🖼️ Destination Preview]|
+---------------------------------------------------------------------------------+
```

---

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Web Interface**: [Streamlit](https://streamlit.io/) (1.35+)
- **File & Path Management**: Python Standard Library (`pathlib`, `os`, `shutil`)
- **Image Synthesis (Demo Mode)**: [Pillow (PIL)](https://python-pillow.org/)
- **Activity Logging**: Python Standard Library (`logging`)
- **Automated Testing**: [pytest](https://pytest.org/) (8.0+)

---

## 📂 Project Structure

```text
snapsort/
├── app.py                   # Streamlit web application & user interface
├── automation.py            # Core file-organization & safety logic (UI-independent)
├── requirements.txt         # Production & development dependencies
├── README.md                # Comprehensive project documentation & guide
├── .gitignore               # Standard ignores for Python, pytest, & virtualenvs
├── tests/
│   └── test_automation.py   # Full pytest test suite (13 test scenarios)
└── sample_data/
    └── .gitkeep             # Directory placeholder for demo mode sandbox
```

---

## 🚀 Quickstart & Installation (Windows)

Follow these steps using **Windows PowerShell**:

### 1. Prerequisites
- Verify that Python 3.11 or newer is installed:
  ```powershell
  python --version
  ```

### 2. Clone or Navigate to the Project
```powershell
cd e:\project\codealpa\SnapSort
```

### 3. Create & Activate a Virtual Environment (Optional but Recommended)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

### 4. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

---

## 💻 Running the Application

Launch the Streamlit web server:

```powershell
python -m streamlit run app.py
```

The app will open automatically in your default browser at:
`http://localhost:8501`

---

## 🧪 Running Automated Tests

Run the test suite with verbose output:

```powershell
python -m pytest tests/ -v
```

Expected output:
```text
tests/test_automation.py::test_move_jpg_files_successfully PASSED
tests/test_automation.py::test_move_jpeg_files_successfully PASSED
tests/test_automation.py::test_ignore_unrelated_file_types PASSED
tests/test_automation.py::test_case_insensitive_extensions PASSED
tests/test_automation.py::test_empty_source_folder PASSED
tests/test_automation.py::test_create_destination_directory_when_missing PASSED
tests/test_automation.py::test_avoid_duplicate_filename_overwrites PASSED
tests/test_automation.py::test_reject_identical_paths PASSED
tests/test_automation.py::test_reject_unsafe_recursive_destination PASSED
tests/test_automation.py::test_handle_missing_source_directory PASSED
tests/test_automation.py::test_recursive_discovery_and_preservation PASSED
tests/test_automation.py::test_stats_and_progress_callback PASSED
tests/test_automation.py::test_generate_sample_images PASSED

============================= 13 passed in 0.78s ==============================
```

---

## 📖 How to Use SnapSort

### Mode 1: Interactive Demo Sandbox (Best for Quick Testing)
1. In the sidebar, select **🧪 Interactive Demo Mode**.
2. Click **✨ Generate Sample Test Files**. This creates 5 distinct `.jpg`/`.jpeg` images and 2 non-image dummy files (`notes.txt`, `expenses.csv`) in `sample_data/source_demo`.
3. Click **🔍 Scan & Preview Source** to see the detected files.
4. Check the **Confirmation Checkbox**.
5. Click **⚡ Organize Images**.
6. Observe the progress bar and review the results table, activity audit log, and image preview.

### Mode 2: Local Folder Mode (Real Organization)
1. In the sidebar, select **🖥️ Local Machine Mode**.
2. Enter your source directory (e.g., `C:\Users\YourName\Downloads\Unsorted`).
3. Enter your destination directory (e.g., `C:\Users\YourName\Pictures\OrganizedImages`).
4. (Optional) Check **Include images from subfolders** if you want to organize nested folders.
5. Click **🔍 Scan & Preview Source** to confirm detected images.
6. Check the confirmation checkbox and click **⚡ Organize Images**.

---

## ☁️ Local vs. Cloud Deployment Explanation

Web applications deployed to cloud hosts (such as Streamlit Community Cloud) run on remote Linux containers. For browser security reasons:
- A web browser cannot grant a cloud-hosted web server raw filesystem access to your personal Windows hard drive (`C:\Users\...`).
- Therefore, when hosting SnapSort in the cloud, visitors interact with **🧪 Interactive Demo Mode**, allowing them to test real Python file moves and collision algorithms within the cloud container's isolated sandbox.
- When run locally on your own PC, **🖥️ Local Machine Mode** has full, safe access to organize your actual personal directories.

---

## 📤 Publishing to GitHub

To push your repository to GitHub:

1. Initialize Git in the project root:
   ```powershell
   git init
   ```
2. Add all files:
   ```powershell
   git add .
   ```
3. Commit the changes:
   ```powershell
   git commit -m "feat: complete SnapSort image organizer with Streamlit UI and tests"
   ```
4. Create a new repository on [GitHub](https://github.com/new).
5. Link the remote and push:
   ```powershell
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

---

## 🌐 Deploying to Streamlit Community Cloud

1. Push your code to GitHub (as shown above).
2. Visit [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.
3. Click **New app**.
4. Select your repository, branch (`main`), and set the main file path to:
   ```text
   app.py
   ```
5. Click **Deploy!** Your app will be live on a public URL in 1–2 minutes.

---

## 🔒 Safety & Boundary Disclaimers

- SnapSort **never** deletes files manually: it uses `shutil.move` exclusively.
- All non-JPEG files are left untouched.
- Duplicate names are automatically assigned an incrementing suffix (`_1`, `_2`), guaranteeing zero accidental data overwrites.
- System root directories (`C:\`, `/`) are blocked from selection to prevent unintended mass moves.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
