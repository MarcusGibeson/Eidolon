from pathlib import Path

def main():
 text=Path('conscious_agent/conversation_runtime.py').read_text(encoding='utf-8')
 checks=[
  'from precision_memory_retrieval_v2569 import refine_memory_retrieval' in text,
  text.count('memory_retrieval_projection = refine_memory_retrieval(memory_retrieval_projection)')==2,
  text.count('memories = list(memory_retrieval_projection["selected_memory_records"])')>=2,
 ]
 print({'suite':'v2570-precision-memory-conversation-integration','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
