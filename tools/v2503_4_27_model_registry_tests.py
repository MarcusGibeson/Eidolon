import tempfile
from pathlib import Path
from conscious_agent.model_training.model_registry import register_model_candidate
from conscious_agent.model_training.training_eval import freeze_evaluation_corpus,score_evaluation_results
checks=[]
with tempfile.TemporaryDirectory() as td:
    corpus=freeze_evaluation_corpus([{'case_id':'e1','capability':'coding','prompt':'p','checks':[]}],corpus_version='e1')
    evaluation=score_evaluation_results(corpus,[{'case_id':'e1','passed':True}],model_id='eidolon-v1')
    denied=register_model_candidate(runtime_root=td,model_id='eidolon-v1',parent_model='base',dataset_manifest_digest='a'*64,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=evaluation,operator_authorized=False)
    ok=register_model_candidate(runtime_root=td,model_id='eidolon-v1',parent_model='base',dataset_manifest_digest='a'*64,training_config_digest='b'*64,artifact_digest='c'*64,evaluation=evaluation,operator_authorized=True)
    checks=[denied['ok'] is False,ok['ok'] is True,Path(ok['runtime_path']).exists(),ok['record']['status']=='candidate',ok['record']['provider_selected'] is False,ok['model_promotion_authorized'] is False,len(ok['record']['registry_digest'])==64]
print({'ok':all(checks),'passed':sum(checks),'total':len(checks),'contract':'v2503.4.27'})
assert all(checks)
