# Flask Testing Instructions

## 1. **Create a New File**
Create a test suite file in the project root named:

```
test_app.py
```

## 2. **Use `unittest` Framework**
Use Python's built-in `unittest` module for writing the tests. Import the necessary modules:

```python
import unittest
from app import app, analyze_csv_data
import json
```

## 3. **Set Up a Test Client**
Inside your test class, use Flask's test client setup:

```python
class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
```

## 4. **Write Unit Tests for Routes**

### ✅ **Test the `/` index route**

```python
def test_home_route(self):
    response = self.app.get('/')
    self.assertIn(response.status_code, [200, 404])
```

### ✅ **Test missing file in `/upload`**

```python
def test_upload_no_file(self):
    response = self.app.post('/upload', content_type='multipart/form-data')
    self.assertEqual(response.status_code, 400)
```

### ✅ **Test `/dashboard-info` with no ID**

```python
def test_dashboard_info_no_id(self):
    response = self.app.get('/dashboard-info')
    self.assertEqual(response.status_code, 400)
```

### ✅ **Test `/generate` with no data**

```python
def test_generate_no_data(self):
    response = self.app.post('/generate', 
                           data=json.dumps({}), 
                           content_type='application/json')
    self.assertEqual(response.status_code, 400)
```