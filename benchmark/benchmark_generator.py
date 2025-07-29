# %%
def get_prompt(domain: str, question: str):
    return f"""You are preparing an experiment to compare two types of data systems:
1. Interactive Data Assistant System - understands user intent, can reason, refine, and generate SQL to answer questions.
2. Static Table Discovery System - can only return one or more relevant tables based on a query; it cannot perform transformations, aggregations, or calculations.

Both systems will be tested on the same underlying goal (hidden from the user in the simulation): {question}

Your task is to generate two separate starting prompts for a {domain} domain expert:
- Interactive System Prompt - phrased naturally for a smart assistant that can compute and manipulate data.
- Static System Prompt - phrased for a limited table retrieval tool, avoiding requests for calculations or transformations; instead, it should ask for relevant tables or columns.

Requirements for the prompts:
- Phrase them as if the expert is beginning a real exploratory workflow — sounding natural and grounded in the domain, not like they are intentionally avoiding the target.
- The first turn should express a broad curiosity, often framed as "Could we start with…" or "Can you give me an overview of…".
- Do NOT directly mention or strongly hint at the hidden goal, or pre-select a specific entity/metric that is part of the answer.
- Keep them at least 5 reasoning steps away from the hidden goal so they require multiple turns to reach it.
- Make the prompts plausible even if the hidden goal didn't exist.
- Keep the core curiosity the same so the conversations are comparable, while matching each system's capabilities.

```
Interactive System First Turn:
[write here]

Static System First Turn:
[write here]
```"""

# %%
import json

def read_jsonl(file_path):
    """Reads a JSONL file and returns a list of JSON objects (dicts)."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # skip empty lines
                data.append(json.loads(line))
    return data

def write_jsonl(data, file_path):
    """Writes a list of JSON objects (dicts) to a JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

# %%
SOURCE_DIR = "sources (kramabench)"
KRAMABENCH_SRCS = [
    "archeology.json"
]

final_bench: list[dict[str, str]] = []
for kramabench_src in KRAMABENCH_SRCS:
    domain = kramabench_src[:-5]
    print(f"Handling this domain: {domain}\n\n", flush=True)
    with open(f"{SOURCE_DIR}/{kramabench_src}") as f:
        benchmark_data = json.load(f)
        for datum in benchmark_data:
            query = datum['query']
            answer = datum['answer']
            # print(f"Original query: {query}\n => answer: {answer}")
            prompt = get_prompt(domain, query)
            print(prompt, flush=True)
            interactive = input("Interactive question:\n")
            static = input("Static question:\n")
            final_bench.append({
                "domain": domain,
                "original_direct_question": query,
                "answer": answer,
                "interactive_initial_prompt": interactive,
                "static_initial_prompt": static,
            })
            write_jsonl(final_bench, f"benchmark_{domain}.jsonl")
            print("=" * 50)
    print("=" * 50)


