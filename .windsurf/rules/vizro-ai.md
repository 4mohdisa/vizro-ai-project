---
trigger: always_on
---

Code Style
1. Write concise, technical Python code with accurate examples.
2. Use functional and declarative programming patterns; avoid unnecessary classes.
3. Prefer iteration and modularization over code duplication.
4. Use descriptive variable names with auxiliary verbs (e.g., is_loading, has_error).
5. Use consistent naming conventions for variables, functions, and classes.
6. Use consistent spacing and indentation.

Python Usage
1. Use Python type hints for all function parameters and return types.
2. Avoid using bare except: clauses; catch specific exceptions.
3. Use with statements for resource management (e.g., file operations).
4. Avoid using mutable default arguments in function definitions.
5. Use list comprehensions and generator expressions where appropriate for readability and performance.

Naming Conventions
1. Use snake_case for variables and function names (e.g., process_data).
2. Use PascalCase for class names (e.g., DataProcessor).
3. Use UPPER_CASE for constants (e.g., MAX_RETRIES).
4. Prefix private variables and functions with an underscore (e.g., _helper_function).
5. Be consistent with naming across the codebase to enhance readability.

Syntax and Formatting
1. Use the def keyword for function definitions; avoid lambda functions for complex operations.
2. Avoid unnecessary parentheses and brackets in expressions.
3. Use f-strings for string formatting (e.g., f"Value: {value}").
4. Keep lines within a reasonable length (e.g., 79 characters) for readability.
5. Use a linter (e.g., flake8) and formatter (e.g., black) to maintain code quality.

FastAPI and Pydantic
1. Use Pydantic models for request and response validation.
2. Define API endpoints with appropriate HTTP methods (GET, POST, etc.).
3. Use dependency injection for shared resources (e.g., database connections).
4. Document API endpoints using FastAPI's automatic documentation features.
5. Handle asynchronous operations appropriately; use async and await where necessary.

Error Handling
1. Implement global exception handlers to catch and log unexpected errors.
2. Provide meaningful error messages to the client without exposing internal details.
3. Use custom exception classes for application-specific errors.
4. Log exceptions with stack traces for debugging purposes.
5. Avoid using exceptions for control flow; use them only for exceptional cases.

Security
1. Validate and sanitize all user inputs to prevent injection attacks.
2. Implement proper CORS policies to control cross-origin requests.
3. Use HTTPS for all communications to secure data in transit.
4. Store sensitive information (e.g., API keys) securely; avoid hardcoding them.
5. Regularly update dependencies to patch known vulnerabilities.
