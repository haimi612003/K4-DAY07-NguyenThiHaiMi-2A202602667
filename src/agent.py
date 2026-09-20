from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        if self.store.get_collection_size() == 0:
            return "Không có tài liệu nào trong kho dữ liệu để trả lời câu hỏi này."

        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy ngữ cảnh liên quan để trả lời câu hỏi này."

        context_blocks = []
        for i, result in enumerate(results, start=1):
            source = result.get("metadata", {}).get("doc_id", result.get("id", "unknown"))
            context_blocks.append(f"[{i}] (nguồn: {source}) {result['content']}")
        context = "\n".join(context_blocks)

        prompt = (
            "Trả lời câu hỏi CHỈ dựa trên ngữ cảnh được cung cấp bên dưới. "
            "Khi dùng thông tin từ một đoạn, trích dẫn số của đoạn đó, ví dụ [1]. "
            "Nếu ngữ cảnh không chứa câu trả lời, hãy nói rõ là không tìm thấy thông tin.\n\n"
            f"Ngữ cảnh:\n{context}\n\n"
            f"Câu hỏi: {question}\n"
            "Trả lời:"
        )
        return self.llm_fn(prompt)
