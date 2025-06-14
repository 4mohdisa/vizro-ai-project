# What is Vizro?

Vizro is a declarative Python dashboarding library built on top of Dash and Plotly. It allows you to generate fully interactive dashboards using simple configuration (in Python, YAML, or JSON).

## Minimal Dashboard Example:
```python
import vizro.models as vm
from vizro import Vizro
import vizro.plotly.express as px

iris = px.data.iris()

page = vm.Page(
    title="Sample Page",
    components=[
        vm.Graph(figure=px.scatter(iris, x="sepal_length", y="petal_length"))
    ]
)

dashboard = vm.Dashboard(title="My Dashboard", pages=[page])
Vizro().build(dashboard).run()
```
