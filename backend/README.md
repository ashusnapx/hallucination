# HalluciWatch

Real-time hallucination risk detection for Large Language Models via internal neural signal fingerprinting.

## Installation

```bash
pip install halluciwatch

# With PyTorch support
pip install halluciwatch[torch]

# With LangChain integration
pip install halluciwatch[langchain]

# With training dependencies
pip install halluciwatch[train]

# Everything
pip install halluciwatch[all]
```

## Quick Start

```python
from halluciwatch import HalluciWatch

hw = HalluciWatch.from_pretrained("meta-llama/Llama-3.1-8B")
response, risk_score = hw.score("What year was the Eiffel Tower completed?")
print(f"Risk: {risk_score:.1%}")
```

## License

Apache 2.0
