---
description: This workflow is designed to streamline the development and maintenance of the Vizro AI Dashboard project. It ensures consistency in code style, error handling, and project setup, reducing repetitive tasks and common mistakes.
---

Initialize Project Environment
- Set up the Python virtual environment.
- Install required dependencies listed in requirements.txt.
- Ensure environment variables are correctly configured.monday.com+1orq.ai+1

Code Style and Formatting
- Adhere to PEP 8 standards for Python code.
- Use descriptive variable names with auxiliary verbs (e.g., is_loading, has_error).
- Maintain consistent naming conventions for variables, functions, and classes.
- Use consistent spacing and indentation throughout the codebase.

Error Handling
- Implement try-except blocks where exceptions are expected.
- Log errors appropriately for debugging purposes.
- Provide user-friendly error messages.
- Handle network failures and data loading issues

Dashboard Generation
- Ensure that the generate() function is correctly importing necessary modules.
- Validate that DataFrames are passed as a list (e.g., [df]) to avoid format issues.
- Implement proper error handling with detailed error messages during dashboard creation.
- Add fallback mechanisms for manual dashboard creation when AI generation fails.

Testing and Debugging
- Write unit tests for critical functions.
- Use logging to trace the flow of data and identify issues.
- Test the application thoroughly after changes to ensure

Documentation
- Maintain clear and concise documentation for all modules and functions.
- Update README files with setup instructions and usage guidelines.
- Document any known issues and their resolutions.

Deployment
- Ensure that the Flask backend is running correctly.
- Verify that the web interface is accessible at http://127.0.0.1:8080.
- Confirm that dashboards are generated and opened in a new tab upon CSV upload.

Security
- Implement Content Security Policy headers.
- Sanitize user inputs to prevent injection attacks.
- Handle sensitive data properly, ensuring it is not exposed.
- Implement proper Cross-Origin Resource Sharing (CORS) handling.