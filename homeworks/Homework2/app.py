"""Load and split a Project Gutenberg book into text chunks."""

from langchain_community.document_loaders import GutenbergLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


SAMPLE_BOOK_URL = "https://www.gutenberg.org/cache/epub/1661/pg1661.txt"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 1000


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


if __name__ == "__main__":
    book_url = input(
        "Project Gutenberg .txt URL "
        f"[Enter for Sherlock Holmes: {SAMPLE_BOOK_URL}]: "
    ).strip()
    if not book_url:
        book_url = SAMPLE_BOOK_URL

    documents = load_gutenberg_book(book_url)
    chunks = split_documents(documents)
    print(f"Loaded {len(documents)} document(s) and split them into {len(chunks)} chunks.")
    if chunks:
        print("First chunk preview:")
        print(chunks[0].page_content[:1000])
