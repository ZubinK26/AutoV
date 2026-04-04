# P-FOLIO (optional local copy)

The official dataset is **[yale-nlp/P-FOLIO](https://huggingface.co/datasets/yale-nlp/P-FOLIO)** on Hugging Face (**gated**: accept terms and sign in).

After you have access, download the CSV into this folder, for example:

```bash
huggingface-cli download yale-nlp/P-FOLIO P-FOLIO.csv --local-dir .
```

The manual test file [`../wfm_folio_pffolio_examples_en.md`](../wfm_folio_pffolio_examples_en.md) uses **distinct FOLIO premise bundles** as stand-ins for the **natural-language problems** P-FOLIO annotates until `P-FOLIO.csv` is present here.
