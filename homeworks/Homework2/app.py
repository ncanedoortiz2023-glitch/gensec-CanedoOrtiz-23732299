from langchain_community.document_loaders import GutenbergLoader


SAMPLE_BOOK_URL = "https://www.gutenberg.org/cache/epub/1661/pg1661.txt"


def load_gutenberg_book(book_url):
    """Load a Project Gutenberg plain-text ebook as LangChain Documents."""
    loader = GutenbergLoader(book_url)
    return loader.load()


if __name__ == "__main__":
    book_url = input(
        "Project Gutenberg .txt URL "
        f"[Enter for Sherlock Holmes: {SAMPLE_BOOK_URL}]: "
    ).strip()
    if not book_url:
        book_url = SAMPLE_BOOK_URL

    documents = load_gutenberg_book(book_url)
    print(f"Loaded {len(documents)} document(s).")
    for document in documents:
        print(f"Source: {document.metadata.get('source', book_url)}")
        print("Preview:")
        print(document.page_content[:1000])
