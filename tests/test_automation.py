"""
Automated Test Suite for SnapSort Automation Module

All tests use pytest and pytest's `tmp_path` fixture to ensure isolated,
reproducible, and safe testing without touching any user directories.
"""

from pathlib import Path
import pytest

from automation import (
    IMAGE_EXTENSIONS,
    OrganizationStats,
    ValidationError,
    find_images,
    get_safe_destination_path,
    organize_images,
    validate_destination_path,
    validate_source_dir,
    generate_sample_images,
)


@pytest.fixture
def mock_directories(tmp_path: Path):
    """Provides isolated source and destination directories for testing."""
    src = tmp_path / "test_source"
    dst = tmp_path / "test_destination"
    src.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=True)
    return src, dst


# 1. Moving JPG files successfully
def test_move_jpg_files_successfully(mock_directories):
    src, dst = mock_directories
    img1 = src / "photo1.jpg"
    img2 = src / "photo2.jpg"
    img1.write_bytes(b"dummy jpg content 1")
    img2.write_bytes(b"dummy jpg content 2")

    stats = organize_images(src, dst)

    assert stats.images_found == 2
    assert stats.images_moved == 2
    assert stats.files_skipped == 0
    assert stats.errors == 0
    assert not img1.exists()
    assert not img2.exists()
    assert (dst / "photo1.jpg").exists()
    assert (dst / "photo2.jpg").exists()


# 2. Moving JPEG files successfully
def test_move_jpeg_files_successfully(mock_directories):
    src, dst = mock_directories
    img1 = src / "vacation.jpeg"
    img1.write_bytes(b"dummy jpeg content")

    stats = organize_images(src, dst)

    assert stats.images_found == 1
    assert stats.images_moved == 1
    assert not img1.exists()
    assert (dst / "vacation.jpeg").exists()
    assert (dst / "vacation.jpeg").read_bytes() == b"dummy jpeg content"


# 3. Ignoring unrelated file types
def test_ignore_unrelated_file_types(mock_directories):
    src, dst = mock_directories
    txt_file = src / "notes.txt"
    png_file = src / "diagram.png"
    pdf_file = src / "document.pdf"
    csv_file = src / "data.csv"
    jpg_file = src / "valid_pic.jpg"

    txt_file.write_text("keep me")
    png_file.write_bytes(b"png data")
    pdf_file.write_bytes(b"pdf data")
    csv_file.write_text("a,b,c")
    jpg_file.write_bytes(b"jpg data")

    stats = organize_images(src, dst)

    assert stats.images_found == 1
    assert stats.images_moved == 1
    # Unrelated files must remain untouched in the source folder
    assert txt_file.exists()
    assert png_file.exists()
    assert pdf_file.exists()
    assert csv_file.exists()
    assert not (dst / "notes.txt").exists()
    assert not (dst / "diagram.png").exists()


# 4. Case-insensitive extension handling
def test_case_insensitive_extensions(mock_directories):
    src, dst = mock_directories
    files = [
        src / "image1.JPG",
        src / "image2.JPEG",
        src / "image3.Jpg",
        src / "image4.Jpeg",
        src / "image5.jpg",
    ]
    for f in files:
        f.write_bytes(b"content")

    stats = organize_images(src, dst)

    assert stats.images_found == 5
    assert stats.images_moved == 5
    for f in files:
        assert not f.exists()
        assert (dst / f.name).exists()


# 5. Handling an empty source folder
def test_empty_source_folder(mock_directories):
    src, dst = mock_directories
    stats = organize_images(src, dst)

    assert stats.images_found == 0
    assert stats.images_moved == 0
    assert stats.files_skipped == 0
    assert stats.errors == 0
    assert len(stats.results) == 0


# 6. Creating a destination directory when missing
def test_create_destination_directory_when_missing(tmp_path: Path):
    src = tmp_path / "source_folder"
    dst = tmp_path / "brand_new_subfolder" / "nested_destination"
    src.mkdir(parents=True)
    img = src / "test.jpg"
    img.write_bytes(b"data")

    assert not dst.exists()
    stats = organize_images(src, dst, create_dest=True)

    assert dst.exists()
    assert dst.is_dir()
    assert stats.images_moved == 1
    assert (dst / "test.jpg").exists()


# 7. Avoiding duplicate filename overwrites
def test_avoid_duplicate_filename_overwrites(mock_directories):
    src, dst = mock_directories
    # Pre-populate destination with photo.jpg
    (dst / "photo.jpg").write_text("existing photo in destination")
    (dst / "photo_1.jpg").write_text("existing numbered photo")

    # Source has a photo.jpg with different content
    (src / "photo.jpg").write_text("new incoming photo")

    stats = organize_images(src, dst)

    assert stats.images_found == 1
    assert stats.images_moved == 1
    # Existing files in dest must NOT be overwritten
    assert (dst / "photo.jpg").read_text() == "existing photo in destination"
    assert (dst / "photo_1.jpg").read_text() == "existing numbered photo"
    # New file must be safely renamed to photo_2.jpg
    assert (dst / "photo_2.jpg").exists()
    assert (dst / "photo_2.jpg").read_text() == "new incoming photo"


# 8. Rejecting identical source and destination paths
def test_reject_identical_paths(tmp_path: Path):
    src = tmp_path / "same_dir"
    src.mkdir()
    valid, msg = validate_destination_path(src, src)
    assert not valid
    assert "same directory" in msg.lower()

    with pytest.raises(ValidationError):
        organize_images(src, src)


# 9. Rejecting unsafe recursive destination paths (destination inside source)
def test_reject_unsafe_recursive_destination(tmp_path: Path):
    src = tmp_path / "parent_source"
    dest_inside = src / "nested_dest"
    src.mkdir()
    dest_inside.mkdir()

    # In non-recursive, it's technically separate, but in recursive it's an infinite loop hazard
    valid, msg = validate_destination_path(src, dest_inside, recursive=True)
    assert not valid
    assert "infinite loop" in msg.lower() or "inside the source" in msg.lower()

    with pytest.raises(ValidationError):
        organize_images(src, dest_inside, recursive=True)


# 10. Handling missing source directories
def test_handle_missing_source_directory(tmp_path: Path):
    missing_src = tmp_path / "does_not_exist"
    dst = tmp_path / "dst"
    dst.mkdir()

    valid, msg = validate_source_dir(missing_src)
    assert not valid
    assert "does not exist" in msg.lower()

    with pytest.raises(ValidationError):
        organize_images(missing_src, dst)


# 11. Preserving unrelated files in deep subfolders during recursive scan
def test_recursive_discovery_and_preservation(tmp_path: Path):
    src = tmp_path / "deep_src"
    dst = tmp_path / "deep_dst"
    sub1 = src / "sub1"
    sub2 = sub1 / "nested_sub2"
    sub2.mkdir(parents=True)
    dst.mkdir()

    (src / "top.jpg").write_text("top")
    (sub1 / "level1.jpeg").write_text("level1")
    (sub2 / "level2.JPG").write_text("level2")
    (sub2 / "keep_unrelated.docx").write_text("do not move")

    # Non-recursive should only find top.jpg
    non_rec_stats = find_images(src, recursive=False)
    assert len(non_rec_stats) == 1
    assert non_rec_stats[0].name == "top.jpg"

    # Recursive organizes all 3 images
    stats = organize_images(src, dst, recursive=True)
    assert stats.images_found == 3
    assert stats.images_moved == 3
    assert (dst / "top.jpg").exists()
    assert (dst / "level1.jpeg").exists()
    assert (dst / "level2.JPG").exists()
    # Unrelated document remains untouched in nested folder
    assert (sub2 / "keep_unrelated.docx").exists()


# 12. Correctly reporting stats and progress callback
def test_stats_and_progress_callback(mock_directories):
    src, dst = mock_directories
    (src / "a.jpg").write_text("a")
    (src / "b.jpg").write_text("b")

    progress_calls = []

    def callback(cur, total, name):
        progress_calls.append((cur, total, name))

    stats = organize_images(src, dst, progress_callback=callback)

    assert stats.images_found == 2
    assert stats.images_moved == 2
    assert len(progress_calls) == 2
    assert progress_calls[0] == (1, 2, "a.jpg")
    assert progress_calls[1] == (2, 2, "b.jpg")
    assert stats.duration_seconds >= 0.0


# 13. Demo sample images generation helper
def test_generate_sample_images(tmp_path: Path):
    base = tmp_path / "demo_root"
    src_demo, dst_demo, files = generate_sample_images(base, count=3)

    assert src_demo.exists()
    assert dst_demo.exists()
    assert len(files) >= 3

    # Check that sample JPGs and non-image files are present
    extensions = {f.suffix.lower() for f in files}
    assert ".jpg" in extensions or ".jpeg" in extensions
    assert ".txt" in extensions  # notes.txt for negative testing
