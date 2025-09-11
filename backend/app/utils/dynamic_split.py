import re
from typing import List
import pdfplumber
from transformers import AutoTokenizer

# 加载中文分词 tokenizer（可换成 gpt-3.5-turbo / llama 对应的 tokenizer）
tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")

def count_tokens(text: str) -> int:
    """计算文本的 token 数"""
    return len(tokenizer.encode(text, add_special_tokens=False))

def dynamic_split(text: str,max_tokens: int = 500,overlap: int = 50) -> List[str]:
    """
    动态切分：优先按语义边界 → 超限 fallback 定长
    :param text: 原始长文本
    :param max_tokens: 每个 chunk 最大 token 数
    :param overlap: 块之间的 token 重叠数
    """
    # 第一步：初步按句子/段落边界切分
    sentences = re.split(r"([。！？!?；;]\s*|\n+)", text)  # 保留分隔符
    sentences = ["".join(sentences[i:i+2]).strip() for i in range(0, len(sentences), 2)]
    sentences = [s for s in sentences if s]

    chunks = []
    current_chunk = []
    current_len = 0

    for sent in sentences:
        sent_len = count_tokens(sent)

        # 如果当前句子太长，直接 fallback：切成定长块
        if sent_len > max_tokens:
            sub_chunks = []
            tokens = tokenizer.encode(sent, add_special_tokens=False)
            for i in range(0, len(tokens), max_tokens - overlap):
                piece = tokenizer.decode(tokens[i:i+max_tokens], skip_special_tokens=True)
                sub_chunks.append(piece)
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk, current_len = [], 0
            chunks.extend(sub_chunks)
            continue

        # 如果当前块 + 句子不超过限制 → 合并
        if current_len + sent_len <= max_tokens:
            current_chunk.append(sent)
            current_len += sent_len
        else:
            # 当前块收尾
            if current_chunk:
                chunks.append("".join(current_chunk))

            # 新块从 overlap 开始
            overlap_tokens = []
            if overlap > 0 and chunks:
                last_chunk_tokens = tokenizer.encode(chunks[-1], add_special_tokens=False)
                overlap_tokens = last_chunk_tokens[-overlap:]

            current_chunk = [tokenizer.decode(overlap_tokens, skip_special_tokens=True), sent]
            current_len = count_tokens("".join(current_chunk))

    # 收尾
    if current_chunk:
        chunks.append("".join(current_chunk))

    return chunks

# def test_pdf_split(pdf_path, max_tokens=200, overlap=30):
#     with pdfplumber.open(pdf_path) as pdf:
#         full_text = ""
#         for page in pdf.pages:
#             text = page.extract_text()
#             if text:
#                 full_text += text + "\n"
#
#     print("PDF 总字数:", len(full_text))
#
#     chunks = dynamic_split(full_text, max_tokens=max_tokens, overlap=overlap)
#
#     print(f"\n切分得到 {len(chunks)} 个片段：\n")
#     for i, c in enumerate(chunks, 1):
#         print(f"Chunk {i} (tokens={count_tokens(c)}):\n{c[:150]}...\n")
#
#
# if __name__ == "__main__":
#     test_pdf_split("学生手册.pdf", max_tokens=200, overlap=30)
