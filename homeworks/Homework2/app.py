"""Load, split, embed, and store a Project Gutenberg book."""

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import GutenbergLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


SAMPLE_BOOK_URL = "https://www.gutenberg.org/cache/epub/1661/pg1661.txt"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 1000
CHROMA_DIRECTORY = Path(__file__).resolve().parent / ".chromadb"

PROMPT = ChatPromptTemplate.from_template(
    """You are an assistant for question-answering tasks.
Use the retrieved book excerpts to answer the question.
If the excerpts do not contain the answer, say you don't know based on the book.
Keep the answer concise and do not invent details.

Question: {question}

Context: {context}

Answer:"""
)


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


def format_documents(documents):
    """Combine retrieved document text into the prompt context."""
    return "\n\n".join(document.page_content for document in documents)


def generate_answer(answer_chain, question, documents):
    """Return a grounded answer, or report a concise Gemini/API error."""
    try:
        return answer_chain.invoke(
            {"question": question, "context": format_documents(documents)}
        )
    except Exception as error:
        print(
            f"Gemini/API request failed ({type(error).__name__}). "
            "Try another question or type 'quit'."
        )
        return None


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

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_MODEL"))
    answer_chain = PROMPT | llm | StrOutputParser()

    print("\nAsk questions about the book. Type 'quit' to exit.")
    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() == "quit":
            break
        if not question:
            continue

        retrieved_chunks = retriever.invoke(question)
        print(f"Top {len(retrieved_chunks)} chunks:")
        for index, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk.metadata.get("source", book_url)
            print(f"\n--- Chunk {index} (source: {source}) ---")
            print(chunk.page_content[:1000])

        answer = generate_answer(answer_chain, question, retrieved_chunks)
        if answer is None:
            continue
        print(f"\nAnswer:\n{answer}")
