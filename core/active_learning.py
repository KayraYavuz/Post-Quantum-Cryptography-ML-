import torch
import numpy as np

class EntropySelector:
    """Entropi tabanlı aktif öğrenme için osiloskop izi seçici."""
    def __init__(self, model):
        self.model = model

    def calculate_entropy(self, trace):
        """İzin entropisini hesaplar."""
        # İz değerlerinin olasılık dağılımını normalize et
        trace = np.abs(trace.detach().numpy()) if isinstance(trace, torch.Tensor) else np.abs(trace)
        total = np.sum(trace)
        if total == 0: return 0
        probs = trace / total
        return -np.sum(probs * np.log2(probs + 1e-9))

    def select_critical_traces(self, traces, top_k=5):
        entropies = [self.calculate_entropy(t) for t in traces]
        indices = np.argsort(entropies)[-top_k:]
        return traces[indices], indices

class FineTuneEngine:
    def __init__(self, model):
        self.model = model
        self.optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        self.criterion = torch.nn.CrossEntropyLoss()

    def train_step(self, x, y):
        self.optimizer.zero_grad()
        out = self.model(x)
        loss = self.criterion(out, y)
        loss.backward()
        self.optimizer.step()
        return loss.item()
