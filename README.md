# flake8-multilne-equals

A Flake8 plugin that enforces consistent spacing around `=` in function call keyword arguments, with different rules for single-line vs. multiline calls.

## Installation

```bash
pip install flake8-multilne-equals
```

## Motivation

This plugin improves code readability in multiline function calls by:

- **Visual consistency**: Spaces around `=` in multiline calls make keyword arguments easier to scan
- **Better diffs**: One argument per line produces cleaner git diffs when arguments change
- **PEP 8 compliance**: Maintains standard Python style (no spaces around `=`) for single-line calls

This style deliberately contradicts PEP 8's E251 rule for multiline calls, trading strict adherence for improved readability in long function signatures.

## Rules

### MNA001: Missing spaces around `=` in multiline function call

**Bad:**
```python
result = foo(
    a=1,
    b=2,
)
```

**Good:**
```python
result = foo(
    a = 1,
    b = 2,
)
```

### MNA002: Unexpected spaces around `=` in single-line function call

This rule replaces E251 for single-line calls.

**Bad:**
```python
result = foo(a = 1, b = 2)
```

**Good:**
```python
result = foo(a=1, b=2)
```

### MNA003: Multiple arguments on same line in multiline function call

**Bad - Multiple keyword arguments:**
```python
result = foo(
    a = 1, b = 2,
    c = 3,
)
```

**Bad - Keyword mixed with positional:**
```python
result = foo(
    1, 2, a = 3,
    b = 4,
)
```

**Good:**
```python
result = foo(
    a = 1,
    b = 2,
    c = 3,
)
```

## Configuration

Since this plugin contradicts PEP 8's E251, you need to configure Flake8 to ignore E251 and enable MNA checks.

### Option 1: Command line

```bash
flake8 --extend-ignore=E251 your_file.py
```

### Option 2: Configuration file

Create or edit `.flake8` in your project root:

```ini
[flake8]
extend-ignore = E251
extend-select = MNA
```

Or in `setup.cfg`:

```ini
[flake8]
extend-ignore = E251
extend-select = MNA
```

Or in `tox.ini`:

```ini
[flake8]
extend-ignore = E251
extend-select = MNA
```

### Option 3: pyproject.toml (requires flake8 >= 5.0)

```toml
[tool.flake8]
extend-ignore = ["E251"]
extend-select = ["MNA"]
```

## Examples

### Correct usage

```python
# Single-line calls: no spaces around =
result1 = foo(a=1, b=2)
obj = MyClass(x=10, y=20, z=30)

# Multiline calls: spaces around =, one argument per line
result2 = foo(
    a = 1,
    b = 2,
    c = 3,
)

result3 = MyClass(
    x = 10,
    y = 20,
    z = 30,
)

# Positional args separate from keyword args
result4 = foo(
    1,
    2,
    a = 3,
    b = 4,
)
```

### Common violations

```python
# MNA002: Spaces in single-line call
result = foo(a = 1, b = 2)

# MNA001: No spaces in multiline call
result = foo(
    a=1,
    b=2,
)

# MNA003: Multiple keywords on same line
result = foo(a = 1, b = 2,
             c = 3)

# MNA003: Keyword mixed with positional on same line
result = foo(1, 2, a = 3,
             b = 4)
```

## Editor Integration

### VS Code

Install the Python extension and configure Flake8 in your `settings.json`:

```json
{
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": ["--extend-ignore=E251"]
}
```

### PyCharm

1. Go to **Settings → Tools → External Tools**
2. Add Flake8 with arguments: `--extend-ignore=E251 $FilePath$`
3. Or configure in **Settings → Editor → Inspections → Python → Flake8**

### Vim/Neovim

With ALE:

```vim
let g:ale_python_flake8_options = '--extend-ignore=E251'
```

### Emacs

With Flycheck:

```elisp
(setq flycheck-flake8rc ".flake8")
```

Then use a `.flake8` config file.

## Pre-commit Hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--extend-ignore=E251']
        additional_dependencies: ['/path/to/flake8-multiline-equals']
```

## Development

### Running tests

Create test files in `test/` directory and run:

```bash
flake8 --extend-ignore=E251 [FILES]
```

## Limitations

- The plugin only checks keyword arguments, not positional arguments
- Nested function calls are handled correctly, but deeply nested calls with complex line spans may have edge cases
- Multiline keyword argument values (e.g., lambda expressions, list comprehensions) only track the `=` line, not the full value span

## FAQ

**Q: Why deviate from PEP 8?**

A: While PEP 8 (E251) prohibits spaces around `=` in keyword arguments, this plugin prioritizes readability for multiline calls. The spaces create visual separation that makes complex function signatures easier to read and modify.

**Q: Can I use this with other formatters like Black?**

A: Black does not add spaces around `=` in keyword arguments, so it conflicts with this plugin's MNA001 rule. You would need to manually format multiline calls or configure Black to skip those sections.

**Q: What if I only want to enforce the "one argument per line" rule (MNA003)?**

A: You can selectively ignore rules in your Flake8 config:
```ini
[flake8]
extend-ignore = E251, MNA001, MNA002
extend-select = MNA
```

**Q: Does this work with Python 2?**

A: No, this plugin requires Python 3.9+ for type hints and AST features.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all checks pass
5. Submit a pull request

## Changelog

### 1.0.0 (2024-12-13)
- Initial release
- MNA001: Enforce spaces around `=` in multiline calls
- MNA002: Prohibit spaces around `=` in single-line calls
- MNA003: One argument per line in multiline calls
