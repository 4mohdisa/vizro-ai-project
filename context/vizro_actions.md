# Actions = Callbacks

Vizro uses Action models to attach behavior (like callbacks in Dash).

## Built-in Actions:

- export_data()
- filter_interaction(targets=["chart_id"])

## Example:
```python
vm.Graph(
    figure=px.scatter(df, x="x", y="y", custom_data=["category"]),
    actions=[vm.Action(function=filter_interaction(targets=["other_chart"]))]
)
```