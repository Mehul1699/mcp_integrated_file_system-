print("STEP 1: Script started", flush=True)

print("Before standard library imports", flush=True)
import os
import re
import hashlib
from pathlib import Path

print("Before ChromaDB import", flush=True)
import chromadb

print("Before dotenv import", flush=True)
from dotenv import load_dotenv

from mcp_client import MCPFilesystemClient

import json
import asyncio
from local_embeddings import generate_embeddings

print("All imports completed", flush=True)

load_dotenv()
RESUME_FOLDER = Path("resumes")
DATABASE_FOLDER = "./chroma_db"

chroma_client = chromadb.PersistentClient(path=DATABASE_FOLDER)

collection = chroma_client.get_or_create_collection(
    name="resume_chunks",
    metadata={"hnsw:space": "cosine"}
)

print("ChromaDB collection ready.")

print("STEP 2: ChromaDB collection created", flush=True)


def chunk_resume(text: str) -> list[dict]:
    section_names = {
        "summary": "Summary",
        "professional summary": "Summary",
        "skills": "Skills",
        "technical skills": "Skills",
        "experience": "Experience",
        "work experience": "Experience",
        "professional experience": "Experience",
        "education": "Education",
        "projects": "Projects",
        "certifications": "Certifications",
    }

    chunks = []
    current_section = "General"
    current_lines = []

    def save_chunk():
        content = "\n".join(current_lines).strip()

        if content:
            words = content.split()
            chunk_size = 180
            overlap = 30

            start = 0
            while start < len(words):
                part = " ".join(words[start : start + chunk_size])

                chunks.append(
                    {
                        "section": current_section,
                        "text": f"Section: {current_section}\n{part}",
                    }
                )

                if start + chunk_size >= len(words):
                    break

                start += chunk_size - overlap

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        heading = re.sub(r"[:\s]+$", "", line).lower()

        if heading in section_names:
            save_chunk()
            current_section = section_names[heading]
            current_lines = []
        else:
            current_lines.append(line)

    save_chunk()
    return chunks


def extract_candidate_name(text: str, filepath: Path) -> str:
    """Try to identify the candidate's name near the start of a resume."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Examine the first few lines, where a resume name usually appears.
    for line in lines[:8]:
        cleaned = line.strip(" |:-\t")

        # Skip contact details, headings, and obvious labels.
        if any(char.isdigit() for char in cleaned):
            continue

        if "@" in cleaned or "http" in cleaned.lower():
            continue

        if len(cleaned.split()) not in (2, 3, 4):
            continue

        if len(cleaned) > 60:
            continue

        if cleaned.lower() in {
            "resume",
            "curriculum vitae",
            "professional summary",
            "technical skills",
            "work experience",
            "education",
        }:
            continue

        # Accept typical names made up of alphabetic words,
        # including common hyphenated or apostrophe names.
        words = cleaned.split()

        if all(re.fullmatch(r"[A-Za-z][A-Za-z'-]*", word) for word in words):
            return cleaned

    # Fall back to the filename if no plausible name is found.
    return filepath.stem


async def index_resumes():
    print("\nConnecting to Filsystem MCP Server...")

    async with MCPFilesystemClient() as mcp_client:

        print("\nRequesting resumes through MCP...")

        batch_result = await mcp_client.batch_process()

        if batch_result.isError:
            print("MCP batch processing failed.")
            return

        batch_data = None

        for item in batch_result.content:
            if hasattr(item, "text"):
                try:
                    batch_data = json.loads(item.text)
                    break
                except json.JSONDecodeError:
                    continue

        if not batch_data:
            print("No resume data received from MCP server.")
            return

        processed_count = 0

        for file_data in batch_data.get("results", []):
            filepath = file_data.get("filepath", "")
            result = file_data.get("result", {})

            if not result.get("success"):
                print(f"Skipping {filepath}: {result.get('error')}")
                continue

            text = result.get("content", "")

            if not text.strip():
                print(f"Skipping {filepath}: No text extracted")
                continue

            chunks = chunk_resume(text)

            if not chunks:
                print(f"Skipping {filepath}: No chunks generated.")
                continue

            candidate_name = extract_candidate_name(text, Path(filepath))

            file_key = hashlib.sha256(filepath.encode("utf-8")).hexdigest()[:16]

            metadatas = [
                {
                    "resume_id": file_key,
                    "resume_path": filepath,
                    "candidate_name": candidate_name,
                    "section": chunk["section"],
                    "chunk_index": index,
                }
                for index, chunk in enumerate(chunks)
            ]

            try:
                collection.delete(where={"resume_id": file_key})
            except Exception:
                pass

            embeddings = generate_embeddings([chunk["text"] for chunk in chunks])

            ids = [f"{file_key}_{index}" for index in range(len(chunks))]

            collection.add(
                ids=ids,
                documents=[chunk["text"] for chunk in chunks],
                embeddings=embeddings,
                metadatas=metadatas,
            )

            processed_count += 1
            print(f"Indexed: {candidate_name} " f"({len(chunks)} chunks)")

        print(f"\nSuccessfully indexed {processed_count} resumes.")


if __name__ == "__main__":
    asyncio.run(index_resumes())
