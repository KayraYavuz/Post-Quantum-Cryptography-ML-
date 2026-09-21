import numpy as np

class EntropySelector:
    """Entropi tabanlı aktif öğrenme için osiloskop izi seçici."""
    def __init__(self, model):
        self.model = model

    def calculate_entropy(self, trace):
        """İzin entropisini hesaplar."""
        # İz değerlerinin olasılık dağılımını normalize et
        trace = np.abs(trace)
        total = np.sum(trace)
        if total == 0: return 0
        probs = trace / total
        return -np.sum(probs * np.log2(probs + 1e-9))

    def select_informative_traces(self, traces, n_samples=10):
        """En yüksek entropili izleri seçer."""
        entropies = [self.calculate_entropy(t) for t in traces]
        indices = np.argsort(entropies)[-n_samples:]
        return [traces[i] for i in indices]
