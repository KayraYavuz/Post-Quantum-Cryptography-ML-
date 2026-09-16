from fastapi.testclient import TestClient
from pqc_bench.api.main import app

client = TestClient(app)
print('Testing WebSocket connection...')
with client.websocket_connect('/ws/traces') as ws:
    msg = ws.receive_json()
    print('Config type:', msg['type'])
    print('Config n_samples:', msg['n_samples'])
    msg2 = ws.receive_json()
    print('Initial type:', msg2['type'])
    print('Initial trace len:', len(msg2['trace']))
    msg3 = ws.receive_json()
    print('Live type:', msg3['type'])
    print('Live leakage_score:', msg3['leakage_score'])
    print('SUCCESS: WebSocket working!')