# Layouts:

Flex(): vertical stack

Grid(columns=2): grid layout with columns

Navigation:
```python
navigation = vm.Navigation(
    nav_selector=vm.NavBar(
        items=[vm.NavLink(label="Main", pages=["Page 1"])]
    )
)
```