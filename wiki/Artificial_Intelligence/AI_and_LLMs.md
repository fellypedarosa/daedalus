---
tags: [artificial_intelligence, software_engineering, ethics, economy]
date_created: 2026-04-12
sources:
  - "[[Akitando 135 - ChatGPT Consegue te Substituir]] (Clipper)"
---
# AI and Large Language Models (LLMs)

The emergence of Large Language Models (LLMs) like ChatGPT marks a significant shift in how technical information is accessed and generated, but they remain tools that require expert oversight.

## LLMs in Software Development

### The "Junior Assistant" Paradigm
LLMs are exceptionally good at "mundane" tasks but lack architectural intuition.
- **Capabilities**: Writing boilerplate code, generating unit tests, or explaining basic syntax.
- **Limitations**: They often provide the simplest, least scalable solution (e.g., direct file uploads instead of pre-signed S3 URLs) unless explicitly instructed otherwise.
- **Assertive Errors**: LLMs can verbalize incorrect or hallucinated information with high confidence. Without expert knowledge, a developer cannot distinguish a correct answer from a dangerously confident error.

## Technical and Economic Reality

### 1. Training Costs
Developing high-tier models (GPT-4, etc.) is a multi-million dollar endeavor requiring:
- Thousands of high-end GPUs (NVIDIA centers).
- Petabytes of curated training data.
- Massive electricity and infrastructure budgets.
*Conclusion*: Individual developers or small startups cannot "build" these models from scratch; they will primarily function as consumers of established APIs.

### 2. Scalability of Search vs. AI
- **Economic Viability**: An AI-generated response is 10 to 100 times more expensive than a traditional Google search query.
- **Infrastructure Barrier**: Current models struggle to scale to the billions of daily users that search engines handle, leading to frequent timeouts and outages during peak demand.

## Professional Impact
- **Replacement Risk**: "Ruined," "lazy," or purely manual-repetitive programming roles are the most vulnerable. 
- **The Senior Multiplier**: For expert developers, LLMs act as a multiplier, handling boilerplate faster than searching StackOverflow, provided the senior can validate the architectural integrity of the output.
