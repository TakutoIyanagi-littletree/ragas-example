<h1 align="center">
  <img style="vertical-align:middle" height="200"
  src="./docs/assets/logo.png">
</h1>
<p align="center">
  <i>SOTA metrics for evaluating Retrieval Augmented Generation (RAG)</i>
</p>

<p align="center">
    <a href="https://github.com/beir-cellar/beir/releases">
        <img alt="GitHub release" src="https://img.shields.io/github/release/beir-cellar/beir.svg">
    </a>
    <a href="https://www.python.org/">
            <img alt="Build" src="https://img.shields.io/badge/Made%20with-Python-1f425f.svg?color=purple">
    </a>
    <a href="https://github.com/beir-cellar/beir/blob/master/LICENSE">
        <img alt="License" src="https://img.shields.io/github/license/beir-cellar/beir.svg?color=green">
    </a>
    <a href="https://colab.research.google.com/drive/1HfutiEhHMJLXiWGT8pcipxT5L2TpYEdt?usp=sharing">
        <img alt="Open In Colab" src="https://colab.research.google.com/assets/colab-badge.svg">
    </a>
    <a href="https://github.com/beir-cellar/beir/">
        <img alt="Downloads" src="https://badges.frapsoft.com/os/v1/open-source.svg?v=103">
    </a>
</p>

<h4 align="center">
    <p>
        <a href="#beers-installation">Installation</a> |
        <a href="#beers-quick-example">Quick Example</a> |
        <a href="https://huggingface.co/BeIR">Hugging Face</a>
    <p>
</h4>


## Quickstart 

This is a small example program you can run to see ragas in action!
```python
from datasets import load_dataset
from ragas.metrics import (
    Evaluation,
    rouge1,
    bert_score,
    entailment_score,
) # import the metrics you want to use

# load the dataset
ds = load_dataset("explodinggradients/eli5-test", split="test_eli5")

# init the evaluator, this takes in the metrics you want to use
# and performs the evaluation
e = Evaluation(
    metrics=[rouge1, bert_score, entailment_score,],
    batched=False,
    batch_size=30,
)

# run the evaluation
results = e.eval(ds["ground_truth"], ds["generated_text"])
print(results)
```
If you want a more in-depth explanation of core components, check out our quick-start notebook
## Metrics

### Character based

- **Levenshtein distance** the number of single character edits (additional, insertion, deletion) required to change your generated text to ground truth text.
- **Levenshtein** **ratio** is obtained by dividing the Levenshtein distance by sum of number of characters in generated text and ground truth. This type of metrics is suitable where one works with short and precise texts.

### N-Gram based

N-gram based metrics as name indicates uses n-grams for comparing generated answer with ground truth. It is suitable to extractive and abstractive tasks but has its limitations in long free form answers due to the word based comparison.

- **ROGUE** (Recall-Oriented Understudy for Gisting Evaluation):
    - **ROUGE-N** measures the number of matching ‘n-grams’ between generated text and ground truth. These matches do not consider the ordering of words.
    - **ROUGE-L** measures the longest common subsequence (LCS) between generated text and ground truth. This means is that we count the longest sequence of tokens that is shared between both

- **BLEU** (BiLingual Evaluation Understudy)

It measures precision by comparing  clipped n-grams in generated text to ground truth text. These matches do not consider the ordering of words.

### Model Based

Model based methods uses language models combined with NLP techniques to compare generated text with ground truth.  It is well suited for free form long or short answer types. 

- **BertScore**
    
    Bert Score measures the similarity between ground truth text answers and generated text using SBERT vector embeddings. The common choice of similarity measure is cosine similarity for which values range between 0 to 1. It shows good correlation with human judgement.
    

- **EntailmentScore**
    
    Textual entailment to measure factual consistency in generated text given ground truth. Score can range from 0 to 1 with latter indicating perfect factual entailment for all samples. Entailment score is highly correlated with human judgement.
    

- **$Q^2$**
    
    Best used to measure factual consistencies between ground truth and generated text. Scores can range from 0 to 1. Higher score indicates better factual consistency between ground truth and generated answer. Employs QA-QG paradigm followed by NLI to compare ground truth and generated answer. Q2Score score is highly correlated with human judgement.

