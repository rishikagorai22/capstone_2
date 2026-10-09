import config


def chunk_document(text, chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def ingest():
    import chromadb
    from sentence_transformers import SentenceTransformer

    client = chromadb.PersistentClient(path=str(config.CHROMA_PATH))
    collection = client.get_or_create_collection(config.COLLECTION_NAME)
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    for path in sorted(config.DOCS_PATH.glob("*.txt")):
        chunks = chunk_document(path.read_text(encoding="utf-8"))
        if not chunks:
            continue
        embeddings = model.encode(chunks).tolist()
        ids = [f"{path.name}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": path.name, "chunk": i} for i in range(len(chunks))]
        collection.upsert(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        print(f"Ingested {len(chunks)} chunks from {path.name}")


if __name__ == "__main__":
    ingest()

    