import json
import os
import time
from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from docx import Document
from mcp.server.fastmcp import FastMCP
import pymupdf
import pytesseract
from PIL import Image
from io import BytesIO

# -----------------------------------
# Configuration
# -----------------------------------


mcp = FastMCP("Filsystem MCP Server")

RESUME_DIR = Path(os.getenv("RESUME_DIR", "resumes")).resolve()


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


RESUME_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------
# Internal helper functions
# ------------------------------------


def get_safe_path(filepath: str) -> Path:
    """
    Resolve a path and ensure it stays inside RESUME_DIR.
    Prevents access to files outside the configured directory.
    """

    path = Path(filepath)

    if not path.is_absolute():
        path = RESUME_DIR / path

    path = path.resolve()
    root = RESUME_DIR.resolve()

    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Access outside the resume directory is not allowed.")

    return path


def build_metadata(filepath: Path) -> dict:
    return {
        "name": filepath.name,
        "size": filepath.stat().st_size,
        "modified_date": filepath.stat().st_mtime,
        "extension": filepath.suffix.lower(),
    }


def get_file_snapshot(directory: Path) -> dict:
    snapshot = {}

    for path in directory.iterdir():
        if path.is_file():
            snapshot[str(path)] = (path.stat().st_mtime, path.stat().st_size)

    return snapshot


def read_file(filepath: str) -> dict:
    try:
        path = get_safe_path(filepath)

        if not path.exists():
            return {"success": False, "error": "File does not exist."}

        if not path.is_file():
            return {"success": False, "error": "Path is not a file."}

        extension = path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Unsupported file extension: {extension}",
            }

        content = ""

        if extension == ".txt":
            content = path.read_text(encoding="utf-8", errors="replace")

        elif extension == ".pdf":
            # First attempt: normal PDF text extraction
            pdf = pymupdf.open(str(path))

            for page in pdf:
                content += page.get_text()

            # Fallback: OCR if normal extraction returns no text
            if not content.strip():
                ocr_text = []

                for page in pdf:
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)

                    image = Image.open(BytesIO(pix.tobytes("png")))

                    page_text = pytesseract.image_to_string(image, lang="eng")

                    ocr_text.append(page_text)

                content = "\n".join(ocr_text)

            pdf.close()

        elif extension == ".docx":
            document = Document(str(path))
            content = "\n".join(paragraph.text for paragraph in document.paragraphs)

        return {"success": True, "content": content, "metadata": build_metadata(path)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(directory: str = "", extension: Optional[str] = None) -> list:
    try:
        path = get_safe_path(directory) if directory else RESUME_DIR

        if not path.exists():
            return []

        if not path.is_dir():
            raise ValueError("Provided path is not a directory.")

        if extension:
            extension = extension.lower()
            if not extension.startswith("."):
                extension = "." + extension

        result = []

        for file_path in path.iterdir():
            if not file_path.is_file():
                continue

            if extension is None or file_path.suffix.lower() == extension:
                result.append(build_metadata(file_path))

        return result

    except Exception as e:
        raise ValueError(str(e))


def write_file(filepath: str, content: str) -> dict:
    try:
        path = get_safe_path(filepath)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return {"success": True, "filepath": str(path)}

    except Exception as e:
        return {"success": False, "error": str(e)}


def search_in_file(filepath: str, keyword: str) -> dict:
    try:
        result = read_file(filepath)

        if not result["success"]:
            return result

        content = result["content"]
        position = content.lower().find(keyword.lower())

        if position == -1:
            return {"success": True, "found": False, "context": None}

        start = max(0, position - 50)
        end = position + len(keyword) + 50

        return {"success": True, "found": True, "context": content[start:end]}

    except Exception as e:
        return {"success": False, "error": str(e)}


# --------------------------------------
# MCP tools
# --------------------------------------


@mcp.tool()
def read_resume(filepath: str) -> dict:
    """Read the contents and metadata of a TXT, PDF, or DOCX resume."""
    return read_file(filepath)


@mcp.tool()
def list_resumes(extension: Optional[str] = None) -> list:
    """List resume files, optionally filtering by extension such as pdf or docx."""
    return list_files(extension=extension)


@mcp.tool()
def write_resume(filepath: str, content: str) -> dict:
    """Write text content to a file inside the configured resume directory."""
    return write_file(filepath, content)


@mcp.tool()
def search_resume(filepath: str, keyword: str) -> dict:
    """Search for a keyword in a resume and return its surrounding context."""
    return search_in_file(filepath, keyword)


@mcp.tool()
def batch_process(filepaths: Optional[list[str]] = None) -> dict:
    """
    Process multiple resumes in one request.

    If filepaths is omitted, all supported files in the resume directory
    are processed.
    """
    try:
        if filepaths is None:
            files = [
                item["name"]
                for item in list_files()
                if item["extension"] in SUPPORTED_EXTENSIONS
            ]
        else:
            files = filepaths

        results = []

        for filepath in files:
            results.append({"filepath": filepath, "result": read_file(filepath)})

        successful = sum(1 for item in results if item["result"]["success"])

        return {
            "success": True,
            "total_files": len(results),
            "processed": successful,
            "failed": len(results) - successful,
            "results": results,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def watch_directory(duration_seconds: int = 30, poll_interval: int = 2) -> dict:
    """
    Monitor the resume directory for newly added or modified files.

    The tool checks periodically and returns detected changes when
    the monitoring period ends.
    """
    if not 1 <= duration_seconds <= 300:
        return {
            "success": False,
            "error": "duration_seconds must be between 1 and 300.",
        }

    if not 1 <= poll_interval <= 30:
        return {"success": False, "error": "poll_interval must be between 1 and 30."}

    try:
        previous = get_file_snapshot(RESUME_DIR)
        detected = []
        end_time = time.monotonic() + duration_seconds

        while time.monotonic() < end_time:
            time.sleep(min(poll_interval, max(0, end_time - time.monotonic())))

            current = get_file_snapshot(RESUME_DIR)

            for filepath, details in current.items():
                if filepath not in previous:
                    detected.append({"event": "created", "filepath": filepath})
                elif previous[filepath] != details:
                    detected.append({"event": "modified", "filepath": filepath})

            previous = current

        return {
            "success": True,
            "directory": str(RESUME_DIR),
            "duration_seconds": duration_seconds,
            "changes_detected": len(detected),
            "changes": detected,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# --------------------------------------------
# MCP Resources
# --------------------------------------------


@mcp.resource("resumes://files")
def resume_files_resource() -> str:
    """Resource containing metadata for all files in the resume directory."""
    files = list_files()
    return json.dumps(files, indent=2)


@mcp.resource("resumes://directory")
def resume_directory_resource() -> str:
    """Resource containing information about the configured resume directory."""
    return json.dumps(
        {
            "directory": str(RESUME_DIR),
            "exists": RESUME_DIR.exists(),
            "file_count": len(list_files()),
        },
        indent=2,
    )


# ------------------------------------------
# Start MCP server
# ------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
