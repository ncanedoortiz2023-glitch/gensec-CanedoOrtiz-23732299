"""Load, split, embed, and store a Project Gutenberg book."""

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import GutenbergLoader
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


SAMPLE_BOOK_URL = "https://www.gutenberg.org/cache/epub/1661/pg1661.txt"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 1000
CHROMA_DIRECTORY = Path(__file__).resolve().parent / ".chromadb"


def load_gutenberg_book(book_url):
    """Load a Project Gutenberg plain-text ebook as LangChain documents."""
    loader = GutenbergLoader(book_url)
    return loader.load()


def split_documents(documents):
    """Split loaded documents into overlapping character-based chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return text_splitter.split_documents(documents)


def embed_and_store_chunks(chunks):
    """Embed chunks with Vertex AI and add them to a local Chroma store.

    Google Cloud authentication uses Application Default Credentials. Set
    GOOGLE_CLOUD_PROJECT in the environment, and optionally set
    GOOGLE_CLOUD_LOCATION to choose the Vertex AI region.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT before storing embeddings.")

    embeddings = VertexAIEmbeddings(
        model_name="gemini-embedding-001",
        project=project,
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1"),
    )
    vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIRECTORY),
    )
    if chunks:
        vector_store.add_documents(documents=chunks)
    return vector_store


if __name__ == "__main__":
    book_url = input(
        "Project Gutenberg .txt URL "
        f"[Enter for Sherlock Holmes: {SAMPLE_BOOK_URL}]: "
    ).strip()
    if not book_url:
        book_url = SAMPLE_BOOK_URL

    documents = load_gutenberg_book(book_url)
    chunks = split_documents(documents)
    vector_store = embed_and_store_chunks(chunks)
    print(
        f"Loaded {len(documents)} document(s), split them into {len(chunks)} "
        f"chunks, and stored them in {CHROMA_DIRECTORY}."
    )
    if chunks:
        print("First chunk preview:")
        print(chunks[0].page_content[:1000])
