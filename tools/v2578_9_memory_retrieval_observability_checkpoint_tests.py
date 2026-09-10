from pathlib import Path

def main():
 s=Path('conscious_agent/conversation_runtime.py').read_text(); dash=Path('conscious_agent/dashboard.py').read_text(); obs=Path('conscious_agent/cognitive_observability_v2533.py').read_text()
 checks=[s.count('record_memory_retrieval_observability(memory_retrieval_projection, operation_id=operation_id)')==2,'load_memory_retrieval_observability(root)' in obs,'Memory retrieval' in dash,'mind-memory-state' in dash,'raw_memory_text_stored' not in dash]
 print({'suite':'v2578.9-memory-retrieval-observability-checkpoint','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
