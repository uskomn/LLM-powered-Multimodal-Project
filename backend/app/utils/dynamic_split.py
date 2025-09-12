import re
from typing import List,Optional
import pdfplumber
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 加载中文分词 tokenizer（可换成 gpt-3.5-turbo / llama 对应的 tokenizer）
tokenizer = AutoTokenizer.from_pretrained("bert-base-chinese")

def count_tokens(text: str) -> int:
    """计算文本的 token 数"""
    return len(tokenizer.encode(text, add_special_tokens=False))

# 动态分块
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

# 递归分块
def recursive_split(text: str,max_tokens: int = 500,overlap: int = 50,level: int = 0) -> List[str]:
    """
    递归分块函数
    :param text: 待切分文本
    :param max_tokens: 每个块的最大 token 数
    :param overlap: 定长切分时的 token 重叠
    :param level: 当前递归层级（0=章节，1=段落，2=句子）
    """
    # 定义多级分隔符（从粗到细）
    separators = [
        r"\n{2,}",  # 章节/小节（两个以上换行）
        r"\n",  # 段落（单换行）
        r"([。！？!?；;]\s*)"  # 句子（保留标点）
    ]

    # 如果文本太短，直接返回
    if count_tokens(text) <= max_tokens:
        return [text.strip()]

    # 如果还有分隔符可用 → 尝试切分
    if level < len(separators):
        sep = separators[level]
        parts = re.split(sep, text)

        # 句子切分时，保留分隔符拼回去
        if level == 2:
            parts = ["".join(parts[i:i + 2]).strip() for i in range(0, len(parts), 2)]

        # 递归处理子块
        chunks = []
        buf = []
        buf_len = 0
        for part in parts:
            if not part.strip():
                continue
            part_len = count_tokens(part)

            if buf_len + part_len <= max_tokens:
                buf.append(part)
                buf_len += part_len
            else:
                if buf:
                    chunks.append("".join(buf).strip())
                # 递归分割超大部分
                if part_len > max_tokens:
                    chunks.extend(recursive_split(part, max_tokens, overlap, level + 1))
                else:
                    buf = [part]
                    buf_len = part_len
                buf = []
                buf_len = 0
        if buf:
            chunks.append("".join(buf).strip())
        return chunks

    # === Fallback：定长切分 + overlap ===
    tokens = list(text)  # 这里简单按字符代替 token
    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap):
        piece = "".join(tokens[i:i + max_tokens])
        chunks.append(piece.strip())
    return chunks

def semantic_chunking(
    text: str,
    max_tokens: int = 300,
    similarity_threshold: float = 0.7,
    window_size: int = 3,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 64,
    debug: bool = False
) -> List[str]:
    """
    基于滑动窗口的语义分块（稳健版）
    - 只计算相邻语义单元之间的相似度，避免构造全量相似度矩阵 (O(u^2))
    - 明确把句子边界映射到相邻单元索引，避免越界
    """

    # 1) 句子切分（保留常见中英文句号/问叹/换行）
    parts = re.split(r'([。！？!?；;]\s*|\n+)', text)
    sentences = ["".join(parts[i:i+2]).strip() for i in range(0, len(parts), 2)]
    sentences = [s for s in sentences if s]

    if not sentences:
        return []

    # 如果 window_size >= len(sentences)，把整个文档视为一个单元
    if window_size < 1:
        window_size = 1
    if window_size >= len(sentences):
        units = ["".join(sentences)]
    else:
        units = ["".join(sentences[i:i+window_size]) for i in range(len(sentences) - window_size + 1)]

    u = len(units)  # 单元数量

    if debug:
        print(f"num_sentences={len(sentences)}, window_size={window_size}, num_units={u}")

    # 2) 计算 unit embeddings（如果只有一个 unit，直接跳过相似度计算）
    model = SentenceTransformer(model_name)
    # NOTE: SentenceTransformer.encode 支持 convert_to_numpy=True
    unit_embeddings = model.encode(units, convert_to_numpy=True, batch_size=batch_size, show_progress_bar=False)

    # 3) L2 归一化 embeddings（便于用点积作 cosine）
    norms = np.linalg.norm(unit_embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)
    unit_embeddings = unit_embeddings / norms

    # 4) 计算相邻单元相似度数组 sim_adj: len = max(u-1, 0)
    if u > 1:
        sim_adj = np.sum(unit_embeddings[:-1] * unit_embeddings[1:], axis=1)  # shape (u-1,)
    else:
        sim_adj = np.array([])

    if debug:
        print(f"sim_adj.shape = {sim_adj.shape}")

    # 5) 分块（遍历句子边界 i 表示边界在 sentences[i-1] 和 sentences[i] 之间）
    chunks = []
    current_chunk = sentences[0]
    current_len = count_tokens(current_chunk)

    # 映射规则（关键）：
    # 边界 i 对应的相邻单元索引 s = i - window_size
    # 因为 unit s covers sentences [s ... s+window_size-1]
    # 相邻单元 s 和 s+1 的“断点”在 sentence index = s + window_size
    # 若 s 不在 [0, u-2]，则使用最近的可用相邻单元（近似 fallback）
    for i in range(1, len(sentences)):
        s_idx = i - window_size  # 想要的相邻单元索引 (unit s and s+1)
        if len(sim_adj) == 0:
            sim = 1.0  # 只有 1 个 unit 时, 视为高相似（不会被语义切分）
        else:
            if 0 <= s_idx < len(sim_adj):
                sim = float(sim_adj[s_idx])
            else:
                # fallback：取最近的相邻单元相似度（避免越界）
                j = min(max(s_idx, 0), len(sim_adj) - 1)
                sim = float(sim_adj[j])

        # 决策：相似且不超 max_tokens → 合并，否则断开
        next_sent = sentences[i]
        next_len = count_tokens(next_sent)
        if sim > similarity_threshold and (current_len + next_len) <= max_tokens:
            current_chunk += next_sent
            current_len += next_len
        else:
            chunks.append(current_chunk)
            current_chunk = next_sent
            current_len = next_len

        if debug and i % 1000 == 0:
            print(f"i={i}, s_idx={s_idx}, sim={sim:.4f}, current_len={current_len}")

    if current_chunk:
        chunks.append(current_chunk)

    if debug:
        print(f"final_chunks={len(chunks)}")

    return chunks


def test_pdf_split(pdf_path, max_tokens=300, overlap=30):
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    print("PDF 总字数:", len(full_text))

    chunks = recursive_split(full_text, max_tokens=max_tokens)

    print(f"\n切分得到 {len(chunks)} 个片段：\n")
    for i, c in enumerate(chunks, 1):
        print(f"Chunk {i} (tokens={count_tokens(c)}):\n{c[:150]}...\n")


if __name__ == "__main__":
    test_pdf_split("学生手册.pdf", max_tokens=200, overlap=30)
