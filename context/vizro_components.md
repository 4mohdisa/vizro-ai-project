# Available Components:

## Graph

Displays interactive Plotly figures (scatter, bar, pie, etc.).

```python
vm.Graph(
    figure=px.scatter(df, x="sepal_length", y="petal_length", color="species")
)
```

## Button

Triggers an action like exporting data or applying filters.

    ```python
vm.Button(
    text="Download",
    actions=[vm.Action(function=export_data())]
)
```

## AgGrid

Interactive table with sorting, filtering, and selection.

```python
from vizro.tables import dash_ag_grid

vm.AgGrid(
    figure=dash_ag_grid(data_frame=df)
)
```

## Table

Simplified table for displaying static tabular data.

```python
vm.Table(data_frame=df.head())
```

## Card

Displays a summary KPI metric with optional delta and icon.

```python
vm.Card(
    title="Total Sales",
    value="$50K",
    delta="↑ 8%"
)
```

## Filter

Adds filter control based on a column.

```python
vm.Filter(column="species")
```

## Parameter

Used to create custom user inputs and dynamic expressions.

```python
vm.Parameter(id="year_selector", options=[2000, 2007, 2014])
```

## Example:
```python
vm.Button(
    text="Export Data",
    actions=[vm.Action(function=export_data())]
)
```