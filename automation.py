"""
SnapSort — Smart Image Organizer: Core Automation Module

This module provides the file-system automation logic for SnapSort.
It is decoupled from any UI framework and can be tested, scripted,
or imported independently.

Features:
- Validates source and destination paths with safety boundaries.
- Case-insensitive discovery of .jpg and .jpeg images.
- Safe moves with automatic collision-renaming (e.g., photo_1.jpg).
- Prevents unsafe operations (identical paths, recursive folder loops).
- Full audit trail with structured logs and detailed operation stats.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
from typing import Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Setup module logger
logger = logging.getLogger("snapsort")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Recognized JPEG extensions (case-insensitive)
IMAGE_EXTENSIONS = {".jpg", ".jpeg"}

# Blocked / protected system root directories for safety
BLOCKED_ROOT_NAMES = {"/", "c:\\", "c:/", "d:\\", "d:/", "e:\\", "e:/"}


@dataclass
class MoveResult:
    """Record of an individual file operation."""
    status: str  # 'MOVED', 'SKIPPED', 'ERROR'
    source_path: Path
    destination_path: Optional[Path]
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "Time": self.timestamp.strftime("%H:%M:%S"),
            "Status": self.status,
            "Original File": self.source_path.name,
            "Source Path": str(self.source_path),
            "Destination": str(self.destination_path) if self.destination_path else "-",
            "Details": self.message,
        }


@dataclass
class OrganizationStats:
    """Consolidated summary statistics for an organization run."""
    images_found: int = 0
    images_moved: int = 0
    files_skipped: int = 0
    errors: int = 0
    results: list[MoveResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    activity_log: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return max(0.0, (end - self.start_time).total_seconds())


class ValidationError(Exception):
    """Raised when source or destination path fails validation."""
    pass


def is_system_root(path: Path) -> bool:
    """Check if the path resolves to an OS root drive or filesystem root."""
    try:
        resolved = path.resolve()
        # Direct parent equals self means filesystem root
        if resolved.parent == resolved:
            return True
        norm = str(resolved).lower().rstrip("\\/") + "/"
        for root in BLOCKED_ROOT_NAMES:
            if norm == root.lower().rstrip("\\/") + "/":
                return True
    except Exception:
        pass
    return False


def validate_source_dir(source_path: str | Path) -> tuple[bool, str]:
    """
    Validate that the source directory exists, is a folder, and is readable.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not source_path or not str(source_path).strip():
        return False, "Source folder path cannot be empty."

    src = Path(source_path).expanduser()
    if not src.exists():
        return False, f"Source directory does not exist: '{src}'"

    if not src.is_dir():
        return False, f"Source path is a file, not a directory: '{src}'"

    if is_system_root(src):
        return False, "For safety, scanning entire root drives is not permitted."

    # Verify read permissions
    if not os.access(src, os.R_OK):
        return False, f"Permission denied: cannot read directory '{src}'"

    return True, ""


def validate_destination_path(
    source_path: str | Path,
    dest_path: str | Path,
    recursive: bool = False,
) -> tuple[bool, str]:
    """
    Validate the destination path and safety constraints against source.

    Returns:
        (is_valid: bool, error_message: str)
    """
    if not dest_path or not str(dest_path).strip():
        return False, "Destination folder path cannot be empty."

    src = Path(source_path).expanduser().resolve()
    dest = Path(dest_path).expanduser().resolve()

    if is_system_root(dest):
        return False, "For safety, writing directly to root drives is not permitted."

    # Check 1: Identical paths
    if src == dest:
        return False, "Source and destination folders cannot be the same directory."

    # Check 2: Destination inside source in recursive mode
    if recursive and (src in dest.parents):
        return (
            False,
            "Unsafe operation: Destination is inside the source folder tree while "
            "subfolder scanning is enabled. This would cause an infinite loop.",
        )

    # Check 3: If destination already exists, verify it is a directory and writable
    if dest.exists():
        if not dest.is_dir():
            return False, f"Destination path exists and is a file: '{dest}'"
        if not os.access(dest, os.W_OK):
            return False, f"Permission denied: destination directory is not writable: '{dest}'"
    else:
        # Check closest existing parent for write permission
        curr = dest.parent
        while not curr.exists() and curr != curr.parent:
            curr = curr.parent
        if curr.exists() and not os.access(curr, os.W_OK):
            return False, f"Permission denied: cannot create destination folder under '{curr}'"

    return True, ""


def find_images(source_dir: Path, recursive: bool = False) -> list[Path]:
    """
    Discover all .jpg and .jpeg files in the source directory case-insensitively.

    Args:
        source_dir: Validated directory Path
        recursive: If True, searches subdirectories recursively;
                   otherwise processes only direct children.

    Returns:
        Sorted list of matching Path objects.
    """
    images: list[Path] = []
    if not source_dir.is_dir():
        return images

    try:
        if recursive:
            for item in source_dir.rglob("*"):
                try:
                    if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
                        images.append(item)
                except (PermissionError, OSError):
                    continue
        else:
            for item in source_dir.iterdir():
                try:
                    if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
                        images.append(item)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError) as e:
        logger.error(f"Error reading directory {source_dir}: {e}")

    # Sort deterministically
    return sorted(images, key=lambda p: str(p).lower())


def get_safe_destination_path(dest_dir: Path, original_filename: str) -> Path:
    """
    Generate a non-colliding destination path.
    If 'photo.jpg' exists in dest_dir, generates 'photo_1.jpg', 'photo_2.jpg', etc.

    Never overwrites an existing file.
    """
    original_path = Path(original_filename)
    stem = original_path.stem
    suffix = original_path.suffix

    target = dest_dir / original_filename
    if not target.exists():
        return target

    counter = 1
    while True:
        candidate_name = f"{stem}_{counter}{suffix}"
        target = dest_dir / candidate_name
        if not target.exists():
            return target
        counter += 1


def organize_images(
    source_path: str | Path,
    dest_path: str | Path,
    recursive: bool = False,
    create_dest: bool = True,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> OrganizationStats:
    """
    Organize all .jpg and .jpeg images from source to destination.

    Args:
        source_path: Path to source folder.
        dest_path: Path to destination folder.
        recursive: Whether to scan subdirectories.
        create_dest: If True, creates destination directory when missing.
        progress_callback: Optional callable receiving (current_index, total_count, current_filename).

    Returns:
        OrganizationStats detailing all actions taken.
    """
    stats = OrganizationStats(start_time=datetime.now())

    def log_entry(msg: str, level: str = "INFO"):
        stats.activity_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")
        if level == "ERROR":
            logger.error(msg)
        elif level == "WARNING":
            logger.warning(msg)
        else:
            logger.info(msg)

    log_entry(f"Initiating SnapSort task: Source='{source_path}', Destination='{dest_path}', Recursive={recursive}")

    # 1. Validate Source
    src_valid, src_err = validate_source_dir(source_path)
    if not src_valid:
        log_entry(f"Validation failed for source: {src_err}", level="ERROR")
        stats.errors += 1
        stats.end_time = datetime.now()
        raise ValidationError(src_err)

    # 2. Validate Destination
    dest_valid, dest_err = validate_destination_path(source_path, dest_path, recursive=recursive)
    if not dest_valid:
        log_entry(f"Validation failed for destination: {dest_err}", level="ERROR")
        stats.errors += 1
        stats.end_time = datetime.now()
        raise ValidationError(dest_err)

    src = Path(source_path).expanduser().resolve()
    dest = Path(dest_path).expanduser().resolve()

    # 3. Create destination if required
    if not dest.exists():
        if create_dest:
            try:
                dest.mkdir(parents=True, exist_ok=True)
                log_entry(f"Created destination directory: '{dest}'")
            except OSError as e:
                err_msg = f"Failed to create destination folder: {e}"
                log_entry(err_msg, level="ERROR")
                stats.errors += 1
                stats.end_time = datetime.now()
                raise ValidationError(err_msg)
        else:
            err_msg = f"Destination folder does not exist and create_dest is False: '{dest}'"
            log_entry(err_msg, level="ERROR")
            stats.errors += 1
            stats.end_time = datetime.now()
            raise ValidationError(err_msg)

    # 4. Discover images
    images = find_images(src, recursive=recursive)
    stats.images_found = len(images)
    log_entry(f"Discovery complete. Found {len(images)} image(s) matching .jpg/.jpeg in '{src}'")

    if not images:
        log_entry("No images to move. Task finished.")
        stats.end_time = datetime.now()
        return stats

    # 5. Process each image
    total = len(images)
    for idx, img_path in enumerate(images, start=1):
        filename = img_path.name
        if progress_callback:
            try:
                progress_callback(idx, total, filename)
            except Exception:
                pass

        # Check: Self-move prevention
        try:
            target_dest_path = get_safe_destination_path(dest, filename)
            if img_path.resolve() == target_dest_path.resolve():
                msg = f"Skipped '{filename}': Source and destination target are identical file."
                log_entry(msg, level="WARNING")
                stats.files_skipped += 1
                stats.results.append(
                    MoveResult(
                        status="SKIPPED",
                        source_path=img_path,
                        destination_path=target_dest_path,
                        message=msg,
                    )
                )
                continue

            # Check if source file is still readable / exists
            if not img_path.exists():
                msg = f"Skipped '{filename}': File was deleted or moved before processing."
                log_entry(msg, level="WARNING")
                stats.files_skipped += 1
                stats.results.append(
                    MoveResult(
                        status="SKIPPED",
                        source_path=img_path,
                        destination_path=None,
                        message=msg,
                    )
                )
                continue

            # Execute safe move
            renamed = (target_dest_path.name != filename)
            shutil.move(str(img_path), str(target_dest_path))

            if renamed:
                detail = f"Moved and renamed to avoid collision -> '{target_dest_path.name}'"
            else:
                detail = f"Moved successfully to '{target_dest_path}'"

            log_entry(f"[{idx}/{total}] {img_path.name} -> {target_dest_path.name}")
            stats.images_moved += 1
            stats.results.append(
                MoveResult(
                    status="MOVED",
                    source_path=img_path,
                    destination_path=target_dest_path,
                    message=detail,
                )
            )

        except PermissionError as pe:
            msg = f"Permission denied moving '{filename}': {pe}"
            log_entry(msg, level="ERROR")
            stats.errors += 1
            stats.results.append(
                MoveResult(
                    status="ERROR",
                    source_path=img_path,
                    destination_path=None,
                    message=msg,
                )
            )
        except OSError as oe:
            msg = f"OS error moving '{filename}': {oe}"
            log_entry(msg, level="ERROR")
            stats.errors += 1
            stats.results.append(
                MoveResult(
                    status="ERROR",
                    source_path=img_path,
                    destination_path=None,
                    message=msg,
                )
            )
        except Exception as e:
            msg = f"Unexpected failure moving '{filename}': {e}"
            log_entry(msg, level="ERROR")
            stats.errors += 1
            stats.results.append(
                MoveResult(
                    status="ERROR",
                    source_path=img_path,
                    destination_path=None,
                    message=msg,
                )
            )

    stats.end_time = datetime.now()
    log_entry(
        f"Task summary: {stats.images_moved} moved, {stats.files_skipped} skipped, "
        f"{stats.errors} error(s) in {stats.duration_seconds:.2f}s."
    )
    return stats


def generate_sample_images(base_dir: str | Path, count: int = 5) -> tuple[Path, Path, list[Path]]:
    """
    Generate test/demo directory structure with sample images and non-image files.

    Creates:
    - {base_dir}/source_demo/ with .jpg, .jpeg, .JPG, and non-image files (.txt, .csv)
    - {base_dir}/dest_demo/ (clean destination folder)

    Returns:
        (source_demo_path, dest_demo_path, list_of_created_files)
    """
    base = Path(base_dir).resolve()
    source_demo = base / "source_demo"
    dest_demo = base / "dest_demo"

    # Reset/clean folders
    if source_demo.exists():
        shutil.rmtree(source_demo, ignore_errors=True)
    if dest_demo.exists():
        shutil.rmtree(dest_demo, ignore_errors=True)

    source_demo.mkdir(parents=True, exist_ok=True)
    dest_demo.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []

    # Try using PIL to generate real valid colorful test images
    sample_definitions = [
        ("summer_vacation.jpg", (52, 152, 219), "Summer Beach 2026"),
        ("family_dinner.jpeg", (46, 204, 113), "Family Dinner"),
        ("PORTRAIT_SCAN.JPG", (155, 89, 182), "Studio Portrait"),
        ("nature_sunset.jpg", (230, 126, 34), "Golden Sunset"),
        ("receipt_archive.JPEG", (52, 73, 94), "Office Receipt #402"),
    ]

    try:
        from PIL import Image, ImageDraw

        for name, color, label in sample_definitions[:count]:
            img = Image.new("RGB", (320, 240), color=color)
            draw = ImageDraw.Draw(img)
            # Draw decorative shapes
            draw.rectangle([10, 10, 310, 230], outline=(255, 255, 255), width=3)
            draw.rectangle([20, 20, 300, 60], fill=(0, 0, 0, 128))
            draw.text((30, 30), f"SnapSort Sample: {label}", fill=(255, 255, 255))
            draw.text((30, 180), f"File: {name}", fill=(240, 240, 240))

            file_path = source_demo / name
            img.save(file_path, "JPEG", quality=85)
            created_files.append(file_path)

        # Also create a subfolder with an image to showcase recursive feature
        sub_folder = source_demo / "subfolder_trips"
        sub_folder.mkdir(parents=True, exist_ok=True)
        sub_img = Image.new("RGB", (320, 240), color=(26, 188, 156))
        sub_draw = ImageDraw.Draw(sub_img)
        sub_draw.text((30, 30), "Subfolder Trip Photo", fill=(255, 255, 255))
        sub_file = sub_folder / "mountain_climb.jpg"
        sub_img.save(sub_file, "JPEG", quality=85)
        created_files.append(sub_file)

    except ImportError:
        # Fallback to binary minimal JPEG markers if PIL is missing
        minimal_jpeg = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
            0x01, 0x01, 0x00, 0x60, 0x00, 0x60, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
            0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
            0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
            0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
            0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
            0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0x7F, 0x00, 0xFF, 0xD9
        ])
        for name, _, _ in sample_definitions[:count]:
            file_path = source_demo / name
            file_path.write_bytes(minimal_jpeg)
            created_files.append(file_path)

    # Crucial real-world test: Create unrelated files that should NEVER be moved or deleted!
    notes_file = source_demo / "meeting_notes.txt"
    notes_file.write_text("Important meeting notes - must NOT be organized or deleted.", encoding="utf-8")
    created_files.append(notes_file)

    csv_file = source_demo / "expenses_2026.csv"
    csv_file.write_text("Date,Category,Amount\n2026-01-01,Supplies,42.50\n", encoding="utf-8")
    created_files.append(csv_file)

    logger.info(f"Sample data initialized at {source_demo} with {len(created_files)} files.")
    return source_demo, dest_demo, created_files
