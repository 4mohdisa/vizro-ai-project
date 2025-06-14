# YAML Setup:
pages:
  - title: Sample
    layout:
      type: Flex
    components:
      - type: Graph
        figure:
          type: scatter
          x: sepal_length
          y: petal_length
          data: iris

app.py:
```python
import yaml
from pathlib import Path
from vizro.models import Dashboard
from vizro.managers import data_manager

from vizro import Vizro
import vizro.plotly.express as px

data_manager["iris"] = px.data.iris()
config = yaml.safe_load(Path("dashboard.yaml").read_text())
dashboard = Dashboard(**config)
Vizro().build(dashboard).run()
```