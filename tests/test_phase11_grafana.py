import json
import os

def test_grafana_dashboard_structure():
    dashboard_path = "deploy/grafana/dashboard.json"
    assert os.path.exists(dashboard_path), f"Dashboard file not found at {dashboard_path}"
    
    with open(dashboard_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "title" in data
    assert "panels" in data
    assert isinstance(data["panels"], list)
    assert len(data["panels"]) >= 3
    
    # Check expected metrics in panels
    expressions = []
    for panel in data["panels"]:
        for target in panel.get("targets", []):
            if "expr" in target:
                expressions.append(target["expr"])
                
    expected_metrics = ["cpu_usage_percent", "memory_usage_bytes", "http_requests_total", "rate_limit_exceeded_total"]
    for m in expected_metrics:
        assert any(m in expr for expr in expressions), f"Expected metric expression containing '{m}' not found in dashboard targets."

if __name__ == "__main__":
    test_grafana_dashboard_structure()
    print("Grafana dashboard structure tests passed successfully!")
