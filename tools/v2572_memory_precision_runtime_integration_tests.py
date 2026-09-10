from pathlib import Path

def main():
 s=Path('conscious_agent/conversation_runtime.py').read_text()
 checks=['from memory_retrieval_budget_v2571 import apply_memory_retrieval_budget' in s,s.count('memory_retrieval_projection = refine_memory_retrieval(memory_retrieval_projection)')==2,s.count('memory_retrieval_projection = apply_memory_retrieval_budget(memory_retrieval_projection)')==2]
 print({'suite':'v2572-memory-precision-runtime-integration','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
