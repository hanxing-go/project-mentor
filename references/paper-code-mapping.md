# Paper-to-Code Mapping Methodology

## When This Applies

The academic/research mode is triggered when the user provides BOTH a GitHub repository URL AND a paper (PDF file or arXiv link). This methodology defines how to connect the paper's claims to the codebase's implementation.

---

## The Mapping Protocol

```
Paper (PDF)                          Codebase (GitHub)
    │                                     │
    ├─ Extract claims ────────────────────┤
    ├─ Extract formulas ──────┐           ├─ Extract module structure (AST skeleton)
    ├─ Extract sections ──────┤           ├─ Search for formula variable names
    ├─ Extract experiments ───┤           ├─ Search for section numbers in comments
    └─ Extract architecture ──┘           └─ Search for algorithm/method names
                                          │
                                          ▼
                                   ┌──────────────────┐
                                   │  Mapping Table     │
                                   │  Paper Section →   │
                                   │  Code Location     │
                                   └──────────────────┘
```

---

## Step 1: Extracting Claims from the Paper

### Core Problem Statement
Look in: Abstract, Introduction (Section 1), Problem Formulation section.
Extract: The one-sentence problem the paper claims to solve.

### Innovation / Contribution List
Look in: End of Introduction (usually the paragraph starting "Our contributions are:" or "In this paper, we:").
Extract: Each contribution as a bullet point. These become the top-level rows of the mapping table.

### Formula Extraction
Look for: Equation environments, displayed math (`$$...$$`, `\begin{equation}`), inline math with numbers.
Extract: Formula number, LaTeX source, what it computes, which section it belongs to.

### Architecture Diagram Extraction
Look for: Figures showing model architecture, system design, or data flow.
Extract: Figure caption, components shown, data flow direction.

### Experiment Configuration
Look for: "Experimental Setup", "Implementation Details", "Training Details" sections.
Extract: Dataset names, hyperparameter values, hardware used, baseline methods compared.

---

## Step 2: Searching the Codebase

### Search Strategy 1: Formula Variable Names

Take variable names from extracted formulas and search the codebase:
```bash
grep -r "self_attention" --include="*.py" .
grep -r "cross_attn" --include="*.py" .
grep -r "gating_mechanism" --include="*.py" .
```

### Search Strategy 2: Section Numbers in Comments

Many papers' reference implementations include section numbers:
```bash
grep -r "Section 3\\.2" --include="*.py" .
grep -r "Eq\\. \\(5\\)" --include="*.py" .
grep -r "Algorithm 1" --include="*.py" .
```

### Search Strategy 3: Algorithm / Method Names

Search for the paper's named methods:
```bash
grep -r "def cross_attention" --include="*.py" .
grep -r "class GatedAttention" --include="*.py" .
grep -r "CurriculumLearning" --include="*.py" .
```

### Search Strategy 4: Architecture Component Names

Map figure components to code:
```bash
# If the architecture diagram shows "Encoder → Cross-Attention → Decoder":
grep -r "class Encoder" --include="*.py" .
grep -r "class Decoder" --include="*.py" .
```

### Search Strategy 5: Hyperparameter Values

Search for exact values from the paper:
```bash
grep -r "learning_rate.*0\\.001" --include="*.py" --include="*.yaml" --include="*.json" .
grep -r "batch_size.*32" --include="*.py" .
grep -r "num_layers.*6" --include="*.py" .
```

---

## Step 3: Building the Mapping Table

### Table Format

```
| Paper Reference | What It Claims | Code Location | Confidence | Notes |
|-----------------|---------------|---------------|------------|-------|
| Section 3.2     | Cross-Attention with Gate | layers/gated_attn.py:45-120 | Exact | Class name matches section title |
| Equation (5)    | Gate parameter calculation | layers/gated_attn.py:78 | Exact | Variable names match formula |
| Table 1          | Experiment results | benchmark.yaml | Probable | Config values match but no direct reference |
| Section 4.1     | Curriculum learning | ??? | Missing | Could not find corresponding code |
```

### Confidence Levels

| Level | Icon | Meaning |
|-------|------|---------|
| **Exact** | ✅ | File path is directly referenced in comments, or variable names exactly match formulas |
| **Probable** | 🔶 | Strong circumstantial match (structure, naming convention) but no explicit reference |
| **Speculative** | ❓ | Weak match based on functionality; may be implemented differently or elsewhere |
| **Missing** | ❌ | Paper claims this but no corresponding code found — potential gap between paper and implementation |

---

## Special Handling for ML/AI Papers

### Model Architecture → Code Mapping

| Paper Component | Likely Code Location | Search Pattern |
|-----------------|---------------------|----------------|
| Encoder | `models/encoder.py`, `layers/transformer.py` | `class.*Encoder` |
| Decoder | `models/decoder.py` | `class.*Decoder` |
| Attention Mechanism | `layers/attention.py`, `modules/attn.py` | `def.*attention`, `class.*Attention` |
| Feed-Forward Network | `layers/ffn.py`, `modules/feedforward.py` | `class.*FFN`, `class.*FeedForward` |
| Embedding Layer | `modules/embedding.py` | `class.*Embedding` |
| Positional Encoding | `layers/positional.py` | `def.*positional`, `class.*PositionalEncoding` |

### Loss Function → Code Mapping

| Paper Component | Likely Code Location | Search Pattern |
|-----------------|---------------------|----------------|
| Custom Loss | `losses/custom_loss.py`, `training/loss.py` | `class.*Loss`, `def.*loss` |
| Combined Loss | Same file | Multiple loss functions summed |

### Training Loop → Code Mapping

| Paper Component | Likely Code Location | Search Pattern |
|-----------------|---------------------|----------------|
| Main Training Script | `train.py`, `run.py`, `main.py` | `def train`, `Trainer` class |
| Data Loading | `data/dataset.py`, `dataloader.py` | `class.*Dataset`, `DataLoader` |
| Optimizer Setup | `train.py`, `optimizer.py` | `torch.optim.Adam`, `optimizer` |
| Learning Rate Schedule | `train.py`, `scheduler.py` | `scheduler`, `lr_scheduler` |
| Evaluation Loop | `evaluate.py`, `test.py` | `def evaluate`, `def test` |

### Hyperparameters → Code Mapping

| Paper Component | Likely Code Location | Search Pattern |
|-----------------|---------------------|----------------|
| Model Config | `config.yaml`, `config.py`, `hparams.py` | YAML/JSON files, `argparse` definitions |
| Training Config | `configs/train.yaml` | Batch size, epochs, learning rate |

---

## The Reproduction Verification Check

After building the mapping table, perform a quick verification:

1. **Architecture match:** Does the code's model architecture match the paper's Figure 1?
2. **Formula match:** Does `loss.py` implement what Equation (5) says it should?
3. **Hyperparameter match:** Do the default config values match the paper's Table 2?
4. **Dataset match:** Does the code use the same datasets the paper claims to evaluate on?

Report divergences honestly:

```
⚠️ Implementation Notes:
- The paper claims they use AdamW with lr=1e-4, but the default config has lr=3e-4
- Equation (5) shows a sigmoid gate, but the code uses tanh (layers/gate.py:34)
- The paper's Figure 1 shows 6 encoder layers; code default is 8 (config.yaml)
```

These divergences are common and are valuable teaching moments — they show that papers sometimes describe an idealized version, while the code reflects what actually worked.

---

## Output Format Specification

The `paper_analyze.sh` script extracts paper content. The SKILL.md then orchestrates the code search using the strategies above. The final mapping table follows this structure:

```json
{
  "paper": {
    "title": "...",
    "authors": ["..."],
    "year": 2025,
    "arxiv_id": "2501.xxxxx"
  },
  "claims": [
    {
      "claim": "Cross-attention with learnable gating mechanism",
      "section_ref": "Section 3.2",
      "formula_ref": "Eq(4)",
      "code_location": "layers/gated_attention.py:45-120",
      "confidence": "exact",
      "notes": "Class GatedCrossAttention implements the described mechanism"
    }
  ],
  "formulas": [
    {
      "number": "(5)",
      "latex": "g = \\sigma(W_g \\cdot [h_1; h_2])",
      "description": "Gate parameter from concatenated hidden states",
      "code_location": "layers/gated_attention.py:78",
      "confidence": "exact"
    }
  ],
  "experiments": [
    {
      "name": "ImageNet Classification",
      "dataset": "ImageNet-1K",
      "metrics": ["Top-1 Acc", "Top-5 Acc"],
      "config_location": "configs/imagenet.yaml",
      "confidence": "probable"
    }
  ],
  "gaps": [
    {
      "paper_claim": "Curriculum learning strategy (Section 4.1)",
      "status": "missing",
      "notes": "No scheduler or curriculum-related code found"
    }
  ]
}
```
