from agents.manager import run


def main():
    print("Spoonful Enterprise RAG System (Gemini)")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            query = input("Ask a question: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue
        try:
            run(query)
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()

