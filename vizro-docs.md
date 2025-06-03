# 📊 Vizro AI Dashboard Generation Guide

Create interactive, AI-assisted dashboards in minutes using `vizro_ai` and `vizro`.

## ⚙️ 1. Installation

Ensure Python ≥ 3.8 is installed. Then run:

```bash
pip install --upgrade pip
pip install vizro_ai plotly
```

Optional for OpenAI model:

```bash
pip install python-dotenv
```

## 🔐 2. Set up `.env` File

Create a `.env` file in your root directory with your OpenAI API key:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 📁 3. Load Dependencies

```python
from vizro_ai import VizroAI
from vizro import Vizro
import pandas as pd
from dotenv import load_dotenv
import os
```

Load your environment variables:

```python
load_dotenv()
```

## 📄 4. Prepare Your Data

Load your CSV file or generate a DataFrame:

```python
df = pd.read_csv("your_data.csv")
```

AI needs clean, structured tabular data (Pandas DataFrame format).

## 🧠 5. Generate Dashboard with AI

### 🧾 Define Your Prompt

```python
prompt = """
Create a dashboard with:
- Bar chart: Sales by region
- Line chart: Monthly performance
- Filters for region and product category
"""
```

### ⚡ Initialize and Generate

```python
vizro_ai = VizroAI(model="gpt-4o")  # Or gpt-4, gpt-3.5-turbo, etc.
dashboard = vizro_ai.dashboard([df], prompt)
Vizro().build(dashboard).run(port=8090)
```

## 🧪 6. Test a Single Chart

To generate one chart only (e.g., for preview or debugging):

```python
fig = vizro_ai.plot(df, "Bar chart of sales by product")
fig.show()
```

## 🛠 7. Manual Dashboard (Fallback)

If AI generation fails, create your own dashboard:

```python
import vizro.models as vm
import vizro.plotly.express as px

bar_chart = px.bar(df, x="region", y="sales")

dashboard = vm.Dashboard(
    title="Manual Dashboard",
    pages=[
        vm.Page(
            title="Overview",
            components=[vm.Graph(id="sales_chart", figure=bar_chart)]
        )
    ]
)

Vizro().build(dashboard).run(port=8090)
```

## 🔄 Optional: Use Other Models

If you want to try Mistral or Anthropic Claude:

```bash
pip install vizro_ai[anthropic,mistral]
```

## 🧠 Tips for Best Results

- Ensure your DataFrame column names are clean (`snake_case` or `camelCase`)
- Limit to 1,000–2,000 rows for faster responses
- Use clear, structured prompts ("line chart of X over time", "filter by region and product")

## 📌 Common Functions

| Function | Description |
|----------|-------------|
| `VizroAI(model="gpt-4o")` | Initialize Vizro-AI |
| `vizro_ai.plot(df, prompt)` | Generate single chart |
| `vizro_ai.dashboard([df], prompt)` | Generate full dashboard |
| `Vizro().build(dashboard).run(port=8090)` | Launch dashboard server |