from conscious_agent.project_value_calibration_v2601 import build_project_value_calibration

def main():
 rows=[{'strategy_code':'a','predicted_value':10,'realized_value':4,'effort_units':2} for _ in range(3)]+[{'strategy_code':'b','predicted_value':10,'realized_value':10,'effort_units':1} for _ in range(3)];x=build_project_value_calibration(rows);m={r['strategy_code']:r for r in x['profiles']};checks=[m['a']['calibration']=='systematic_overprediction',m['b']['calibration']=='roughly_calibrated',m['a']['median_realized_to_predicted_ratio']==.4,not x['value_model_mutated'],not x['automatic_priority_change_permitted'],len(x['calibration_digest'])==64]
 print({'suite':'v2601-project-value-calibration','passed':sum(map(bool,checks)),'total':len(checks),'ok':all(checks)});raise SystemExit(0 if all(checks) else 1)
if __name__=='__main__':main()
