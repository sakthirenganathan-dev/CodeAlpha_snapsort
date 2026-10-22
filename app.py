"""
SnapSort — Smart Image Organizer
Streamlit Web Application

Automates organizing .jpg and .jpeg images from source to destination folders
with collision safety, detailed audit logs, and live progress tracking.
"""

from __future__ import annotations

import os
from pathlib import Path
import time
import pandas as pd
import streamlit as st

from automation import (
    IMAGE_EXTENSIONS,
    OrganizationStats,
    ValidationError,
    find_images,
    generate_sample_images,
    organize_images,
    validate_destination_path,
    validate_source_dir,
)

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="SnapSort — Smart Image Organizer",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Custom Styling: Minimal, Professional Navy & Light Blue
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Global font & background aesthetics */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }
    
    .main {
        background-color: #F8FAFC;
    }
    
    /* Top Header Styling */
    .app-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 20px 24px;
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
        margin-bottom: 24px;
    }
    
    .app-icon {
        width: 52px;
        height: 52px;
        background: linear-gradient(135deg, #2563EB, #0284C7);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        color: white;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.25);
    }
    
    .app-title-group h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.5px;
    }
    
    .app-title-group p {
        margin: 2px 0 0 0;
        font-size: 14px;
        color: #64748B;
        font-weight: 500;
    }

    /* Stat Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 2px 4px rgba(15, 23, 42, 0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(15, 23, 42, 0.06);
    }
    
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    
    .metric-value {
        font-size: 32px;
        font-weight: 800;
        line-height: 1.1;
    }

    .val-found { color: #0284C7; }
    .val-moved { color: #16A34A; }
    .val-skipped { color: #D97706; }
    .val-error { color: #DC2626; }

    /* Badge & Info Containers */
    .mode-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }
    
    .mode-badge-demo {
        background-color: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
    }
    
    .mode-badge-local {
        background-color: #F0FDF4;
        color: #15803D;
        border: 1px solid #BBF7D0;
    }

    .custom-alert {
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        font-size: 14px;
        line-height: 1.5;
    }
    .alert-info {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        color: #0369A1;
    }
    .alert-warn {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        color: #92400E;
    }

    /* Buttons */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        padding: 8px 18px;
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        transform: translateY(-1px);
    }
    
    /* Hide default streamlit hamburger and footer for clean app feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "last_stats" not in st.session_state:
    st.session_state.last_stats = None
if "scan_preview_files" not in st.session_state:
    st.session_state.scan_preview_files = None
if "demo_initialized" not in st.session_state:
    st.session_state.demo_initialized = False

# Path helper for workspace demo
WORKSPACE_ROOT = Path(__file__).parent.resolve()
DEMO_BASE_DIR = WORKSPACE_ROOT / "sample_data"

# ---------------------------------------------------------
# Sidebar Navigation & Execution Mode Selection
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Operating Mode")
    mode_selection = st.radio(
        "Select Environment Mode:",
        ["🧪 Interactive Demo Mode", "🖥️ Local Folder Mode"],
        index=0,
        help="Use Demo Mode for safe sandboxed testing or cloud deployments. Use Local Folder Mode to organize real files on your local machine.",
    )

    is_demo = "Demo" in mode_selection

    st.markdown("---")
    st.markdown("### ℹ️ About SnapSort")
    st.markdown(
        """
        **SnapSort** is an automated image organization system designed to safely move 
        `.jpg` and `.jpeg` images into a designated destination folder.

        **Safety Guarantees:**
        - 🛡️ **Zero Overwrite**: Auto-renames duplicates (`photo_1.jpg`)
        - 🚫 **Self-Move Protection**: Skips identical source & target
        - 🔒 **Loop Prevention**: Rejects destination nested in recursive source
        - 📑 **Audit Trail**: Every action logged with timestamps
        """
    )
    st.markdown("---")
    st.markdown(
        f"<div style='font-size:12px; color:#64748B;'>"
        f"SnapSort v1.0 • Python Task Automation<br>"
        f"Running on Python {os.sys.version.split()[0]}</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Header Section
# ---------------------------------------------------------
badge_html = (
    '<span class="mode-badge mode-badge-demo">🧪 Interactive Demo Sandbox</span>'
    if is_demo
    else '<span class="mode-badge mode-badge-local">🖥️ Local Machine Mode</span>'
)

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-icon">📁</div>
        <div class="app-title-group">
            <h1>SnapSort</h1>
            <p>Smart Image Organizer — Automate Your Photo Ingestion Pipeline</p>
        </div>
        <div style="margin-left: auto;">
            {badge_html}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Mode Notice and Demo Data Controls
# ---------------------------------------------------------
if is_demo:
    st.markdown(
        """
        <div class="custom-alert alert-info">
            <strong>🧪 Demo Mode Active:</strong> This sandbox operates inside <code>sample_data/</code>.
            Click <strong>Generate Sample Test Files</strong> below to synthesize test images (.jpg, .jpeg)
            and dummy documents (.txt, .csv) to test the filtering, renaming, and organization safely.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        if st.button("✨ Generate Sample Test Files", use_container_width=True, type="primary"):
            src_demo, dst_demo, files = generate_sample_images(DEMO_BASE_DIR, count=5)
            st.session_state.demo_initialized = True
            st.session_state.scan_preview_files = None
            st.session_state.last_stats = None
            st.success(f"Generated {len(files)} sample files in '{src_demo.name}'!")
            st.rerun()

    demo_src_path = str(DEMO_BASE_DIR / "source_demo")
    demo_dst_path = str(DEMO_BASE_DIR / "dest_demo")
else:
    st.markdown(
        """
        <div class="custom-alert alert-warn">
            <strong>🖥️ Local Folder Mode:</strong> Provide real folder paths accessible to this machine.
            SnapSort will move actual <code>.jpg</code> and <code>.jpeg</code> files into your destination folder.
            Always review the scan preview before initiating organization.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Folder Configuration Inputs
# ---------------------------------------------------------
st.markdown("### 📂 Folder Configuration")

col_src, col_dst = st.columns(2)

with col_src:
    default_src = demo_src_path if is_demo else ""
    source_folder_input = st.text_input(
        "Source Folder Path:",
        value=default_src,
        placeholder=r"e.g. C:\Users\Username\Pictures\Unsorted" if os.name == "nt" else "/home/user/Pictures/Unsorted",
        help="The directory containing the .jpg and .jpeg images you want to organize.",
    )

with col_dst:
    default_dst = demo_dst_path if is_demo else ""
    dest_folder_input = st.text_input(
        "Destination Folder Path:",
        value=default_dst,
        placeholder=r"e.g. C:\Users\Username\Pictures\Organized" if os.name == "nt" else "/home/user/Pictures/Organized",
        help="The target folder where all images will be moved. Will be created if it does not exist.",
    )

col_opt1, col_opt2 = st.columns([1, 1])
with col_opt1:
    include_subfolders = st.checkbox(
        "Include images from subfolders (Recursive scan)",
        value=False,
        help="When checked, SnapSort scans all nested subdirectories inside the source directory.",
    )

with col_opt2:
    create_dest_checkbox = st.checkbox(
        "Automatically create destination folder if it does not exist",
        value=True,
        help="If enabled, the destination directory will be created once you click Organize.",
    )

# ---------------------------------------------------------
# Pre-Flight Scan & Preview
# ---------------------------------------------------------
col_actions1, col_actions2 = st.columns([1, 2])

with col_actions1:
    scan_clicked = st.button("🔍 Scan & Preview Source", use_container_width=True)

if scan_clicked:
    src_valid, src_msg = validate_source_dir(source_folder_input)
    if not src_valid:
        st.error(f"❌ {src_msg}")
        st.session_state.scan_preview_files = None
    else:
        src_path = Path(source_folder_input).expanduser().resolve()
        found = find_images(src_path, recursive=include_subfolders)
        st.session_state.scan_preview_files = found
        if found:
            st.success(f"Found **{len(found)}** eligible image(s) (.jpg, .jpeg) in source.")
        else:
            st.info("No matching .jpg or .jpeg images found in this folder.")

# Show Scan Preview if available
if st.session_state.scan_preview_files is not None:
    preview_list = st.session_state.scan_preview_files
    with st.expander(f"📋 Scan Preview ({len(preview_list)} image(s) ready to organize)", expanded=True):
        if preview_list:
            df_preview = pd.DataFrame(
                [
                    {
                        "File Name": p.name,
                        "Extension": p.suffix,
                        "Size (KB)": f"{p.stat().st_size / 1024:.1f}" if p.exists() else "0",
                        "Relative Source Path": str(p.relative_to(Path(source_folder_input).expanduser().resolve())),
                    }
                    for p in preview_list[:100]
                ]
            )
            st.dataframe(df_preview, use_container_width=True, hide_index=True)
            if len(preview_list) > 100:
                st.caption(f"Showing first 100 of {len(preview_list)} files.")
        else:
            st.write("No images found.")

# ---------------------------------------------------------
# Confirmation and Organization Execution
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 🚀 Execute Task Automation")

confirm_container = st.container()
with confirm_container:
    # Explicit user confirmation safety check
    confirm_action = st.checkbox(
        f"I confirm that I want to move all `.jpg` and `.jpeg` images from the source to the destination.",
        value=False,
        help="Explicit confirmation is required before any file operations are executed.",
    )

    organize_btn = st.button(
        "⚡ Organize Images",
        type="primary",
        disabled=not confirm_action,
        use_container_width=True,
    )

if organize_btn:
    if not confirm_action:
        st.warning("⚠️ Please check the confirmation checkbox above before proceeding.")
    else:
        # Pre-validate before starting
        src_ok, src_err = validate_source_dir(source_folder_input)
        if not src_ok:
            st.error(f"❌ Source Error: {src_err}")
        else:
            dest_ok, dest_err = validate_destination_path(
                source_folder_input, dest_folder_input, recursive=include_subfolders
            )
            if not dest_ok:
                st.error(f"❌ Destination Error: {dest_err}")
            else:
                # Progress elements
                progress_bar = st.progress(0.0)
                status_text = st.empty()

                def update_progress(current: int, total: int, filename: str):
                    fraction = current / total if total > 0 else 1.0
                    progress_bar.progress(fraction)
                    status_text.text(f"Moving file [{current}/{total}]: {filename}")
                    time.sleep(0.02)  # Smooth UI update

                try:
                    stats = organize_images(
                        source_path=source_folder_input,
                        dest_path=dest_folder_input,
                        recursive=include_subfolders,
                        create_dest=create_dest_checkbox,
                        progress_callback=update_progress,
                    )
                    progress_bar.progress(1.0)
                    status_text.text("✅ Organization process complete!")
                    st.session_state.last_stats = stats
                    st.session_state.scan_preview_files = None
                    st.success(
                        f"Task Completed Successfully! Moved **{stats.images_moved}** images "
                        f"in {stats.duration_seconds:.2f} seconds."
                    )
                except ValidationError as ve:
                    st.error(f"❌ Organization halted: {ve}")
                except Exception as e:
                    st.error(f"❌ Unexpected error occurred during execution: {e}")

# ---------------------------------------------------------
# Dashboard Statistic Cards
# ---------------------------------------------------------
st.markdown("### 📊 Task Statistics")

stats: OrganizationStats = st.session_state.last_stats

found_count = stats.images_found if stats else 0
moved_count = stats.images_moved if stats else 0
skipped_count = stats.files_skipped if stats else 0
error_count = stats.errors if stats else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Images Found</div>
            <div class="metric-value val-found">{found_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Images Moved</div>
            <div class="metric-value val-moved">{moved_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Files Skipped</div>
            <div class="metric-value val-skipped">{skipped_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Errors</div>
            <div class="metric-value val-error">{error_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# Results Section & Activity Logs
# ---------------------------------------------------------
st.markdown("---")
tab_results, tab_logs, tab_preview = st.tabs(["📑 File Operations Result", "🕒 Activity Audit Log", "🖼️ Destination Preview"])

with tab_results:
    if stats and stats.results:
        results_data = [r.to_dict() for r in stats.results]
        df_results = pd.DataFrame(results_data)
        st.dataframe(df_results, use_container_width=True, hide_index=True)
    else:
        st.info("No operations executed yet. Specify your directories and click 'Organize Images' above.")

with tab_logs:
    if stats and stats.activity_log:
        st.code("\n".join(stats.activity_log), language="text")
    else:
        st.caption("Logs will appear here once an operation is executed.")

with tab_preview:
    dest_path_to_check = Path(dest_folder_input).expanduser().resolve() if dest_folder_input else None
    if dest_path_to_check and dest_path_to_check.exists() and dest_path_to_check.is_dir():
        organized_images = [
            f for f in dest_path_to_check.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        ]
        if organized_images:
            st.markdown(f"**Found {len(organized_images)} image(s) inside destination folder:**")
            grid_cols = st.columns(4)
            for i, img_file in enumerate(organized_images[:8]):
                with grid_cols[i % 4]:
                    try:
                        st.image(str(img_file), caption=img_file.name, use_container_width=True)
                    except Exception:
                        st.text(f"📁 {img_file.name}")
            if len(organized_images) > 8:
                st.caption(f"Showing first 8 of {len(organized_images)} images.")
        else:
            st.info("Destination folder is currently empty.")
    else:
        st.info("Destination folder has not been created or specified yet.")
