import numpy as np
import torch
import torch.nn as nn
from typing import List, Tuple

class EntropySelector:
    """Entropi tabanlı kritik osiloskop izi seçici."""
    def __init__(self, model: nn.Module):
        self.model = model

    def calculate_entropy(self, traces: torch.Tensor) -> torch.Tensor:
        """İzlerin entropisini hesapla (logits dağılımından)."""
        with torch.no_grad():
            logits = self.model(traces)
            probs = torch.softmax(logits, dim=-1)
            entropy = -torch.sum(probs * torch.log(probs + 1e-9), dim=-1)
        return entropy

    def select_critical_traces(self, traces: torch.Tensor, top_k: int = 10) -> Tuple[torch.Tensor, torch.Tensor]:
        """En yüksek entropili (belirsizliği en yüksek) izleri seç."""
        entropy = self.calculate_entropy(traces)
        k = min(top_k, traces.shape[0])
        top_k_indices = torch.topk(entropy, k).indices
        return traces[top_k_indices], top_k_indices

class FineTuneEngine:
    """Hatalı tahmin edilen izler üzerinde fine-tune yapan motor."""
    def __init__(self, model: nn.Module, lr: float = 1e-4):
        self.model = model
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.criterion = nn.CrossEntropyLoss()

    def train_step(self, traces: torch.Tensor, labels: torch.Tensor):
        self.optimizer.zero_grad()
        outputs = self.model(traces)
        loss = self.criterion(outputs, labels)
        loss.backward()
        self.optimizer.step()
        return loss.item()
