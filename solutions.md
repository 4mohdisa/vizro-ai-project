# Flask Application Error Fixes

## ✅ 1. UnboundLocalError: local variable 'os' referenced before assignment

### 🔍 Problem
You re-imported `os` inside the `generate()` function, causing Python to treat `os` as a local variable. But because `os` is already imported at the top, this leads to:

```plaintext
UnboundLocalError: local variable 'os' referenced before assignment
```

### ✅ Solution
**REMOVE** the `import os` line from within the `generate()` function:

```python
# ❌ DELETE this from inside the function
import os
```

You already have:

```python
import os  # ✅ This is already at the top of your script
```

## ✅ 2. ValueError: Input should be a list of DataFrames (VizroAI expects list)

### 🔍 Problem
In `vizro_ai.dashboard(...)` you're passing:

```python
dashboard = vizro_ai.dashboard(df_dict, prompt)
```

But `df_dict` is a dict, not a DataFrame or list of DataFrames.

### ✅ Solution
You should pass either:

```python
vizro_ai.dashboard([df], prompt)  # ✅ Correct: list of DataFrames
```

Or fallback:

```python
vizro_ai.dashboard([df.to_dict(orient='records')], prompt)  # if only dict is accepted
```

So in your function:

```python
dashboard = vizro_ai.dashboard([df], prompt)
```

## ✅ 3. test_generate_with_data fails with status code 500

### 🔍 Problem
Since you're hitting the `UnboundLocalError` and `ValueError`, the `/generate` endpoint crashes, causing the test to return:

```plaintext
500 INTERNAL SERVER ERROR
```

### ✅ Solution
Fixing the above two problems will eliminate this and return a proper `200 OK`.