# 🧠 Vizro-AI Project Context

## 🎯 Project Objective

This project aims to explore and evaluate the capabilities of **Vizro-AI**, an LLM-powered Python framework that transforms natural language prompts into interactive data visualizations and dashboards using **Plotly** and **Vizro**.

Our testing focuses on:
- Generating charts from complex, domain-specific data (e.g., real estate sales).
- Building multi-component, filterable dashboards.
- Evaluating multilingual, multi-model, and advanced customization support.
- Integrating Vizro-AI with LangChain for LLM-driven workflows.

---

## 📌 Key Goals

- ✅ Use natural language prompts to auto-generate visualizations.
- ✅ Create single-page dashboards with multiple charts and filters.
- ✅ Customize layout, chart types, and style via prompt instructions.
- ✅ Run and host dashboards locally via Vizro.
- ✅ Reuse AI-generated code and plug it into applications.

---

## 📘 About Vizro-AI

- Built on **LangChain** and **Plotly**
- Converts text instructions into **Python code + Plotly graphs**
- Works with any LLM supported by LangChain (`gpt-4o`, `Claude`, `Mistral`, etc.)
- Outputs can be `fig` (for direct display) or structured objects (for insights/code reuse)
- Supports multilingual prompts and dynamic chart customization

---

## 🧠 What We've Learned

- Clear, structured prompts produce the best visualizations.
- You can generate charts or entire dashboards using `.plot()` and `.dashboard()`.
- Using `return_elements=True` gives access to:
  - Code (`.code`, `.code_vizro`)
  - Insights (`.chart_insights`)
  - Dynamically generated fig object
- Vizro-AI can be used statically (copy code) or dynamically (LLM call per run).
- Vizro dashboard supports filters, cards, graphs, and layout grids.

---

## ⚠️ Important Notes

- API key (e.g., OpenAI) is required; store securely in `.env`
- Avoid repeated `.plot()` or `.dashboard()` calls with large data — LLM usage may incur cost
- Custom layouts must be clearly described using grid-like instructions for best results
- When using `.dashboard()`, prompts must describe each page clearly if multi-page output is desired

---

## 💻 Helpful Commands

### ▶️ Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate

# Vizro Setup Guide

## 📦 Install Required Packages

```bash
pip install --upgrade pip
pip install vizro_ai plotly
```

## 🔑 Setup .env File

```ini
OPENAI_API_KEY=your_api_key_here
```

## 🧪 Run a Chart Script

```bash
python first_chart.py
```

## 📊 Run a Vizro Dashboard

```bash
python property_dashboard.py
```

## 🌐 Open Vizro Dashboard on a Port

```bash
Vizro().build(dashboard).run(port=8090)
```

## 🚀 Future Enhancements

- Add real CSV support for production testing
- Try Anthropic/Mistral models using:
  ```bash
  pip install vizro_ai[anthropic,mistral]
  ```
- Integrate Vizro-AI tools into LangChain agent chains