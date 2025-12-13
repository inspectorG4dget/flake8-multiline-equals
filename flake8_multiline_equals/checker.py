"""
Flake8 plugin to enforce spacing around `=` in multiline function calls.

Rules:
- MNA001: Missing spaces around `=` in multiline function call
- MNA002: Unexpected spaces around `=` in single-line function call (replaces E251)

This plugin reimplements E251 to allow spaces around `=` in multiline calls
while still catching them in single-line calls. Configure flake8 to ignore E251
when using this plugin.
"""
import ast
import tokenize
from typing import Generator, Tuple, Any


class MultilineNamedArgsChecker:
    name = 'flake8-multiline-named-args'
    version = '1.0.0'

    def __init__(self, tree: ast.AST, lines: list[str], file_tokens: list[tokenize.TokenInfo]):
        self.tree = tree
        self.lines = lines
        self.file_tokens = file_tokens

    def run(self) -> Generator[Tuple[int, int, str, type], None, None]:
        """Run the checker and yield violations."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                yield from self._check_call(node)

    def _check_call(self, node: ast.Call) -> Generator[Tuple[int, int, str, type], None, None]:
        """Check a function call for spacing violations."""
        # Get all keyword arguments
        if not node.keywords:
            return

        # Determine if the call is multiline
        call_start_line = node.lineno
        call_end_line = node.end_lineno

        is_multiline = call_start_line != call_end_line

        # Check each keyword argument individually
        for keyword in node.keywords:
            if keyword.arg is None:  # Skip **kwargs
                continue

            # Look for the equals sign in the tokens
            equals_info = self._find_equals_for_keyword(keyword)
            if not equals_info:
                continue

            equals_line, equals_col, has_space_before, has_space_after = equals_info

            # For each keyword, check if it spans multiple lines
            # A keyword is multiline if the argument name and value are on different lines
            # OR if the overall call is multiline
            keyword_start_line = equals_line
            keyword_end_line = keyword.value.end_lineno
            keyword_is_multiline = is_multiline and (keyword_start_line != keyword_end_line or 
                                                     self._keyword_spans_lines(keyword))

            # DEBUG: Uncomment to see what's happening
            import sys
            print(f"DEBUG: keyword={keyword.arg} line={equals_line} col={equals_col} multiline={is_multiline} keyword_multiline={keyword_is_multiline} space_before={has_space_before} space_after={has_space_after}", file=sys.stderr)

            if keyword_is_multiline:
                # Rule: Multiline calls MUST have spaces around `=`
                if not has_space_before or not has_space_after:
                    print(f"DEBUG: YIELDING MNA001 for {keyword.arg} at line {equals_line} col {equals_col}", file=sys.stderr)
                    yield (
                        equals_line,
                        equals_col,
                        "MNA001 missing spaces around '=' in multiline function call",
                        type(self),
                    )
            else:
                # Rule: Single-line calls MUST NOT have spaces around `=`
                if has_space_before or has_space_after:
                    print(f"DEBUG: YIELDING MNA002 for {keyword.arg} at line {equals_line} col {equals_col}", file=sys.stderr)
                    yield (
                        equals_line,
                        equals_col,
                        "MNA002 unexpected spaces around '=' in single-line function call",
                        type(self),
                    )
    
    def _keyword_spans_lines(self, keyword: ast.keyword) -> bool:
        """Check if a keyword argument spans multiple lines."""
        # A keyword spans lines if any part of it is on a different line
        # This includes the case where the opening paren of the call is on one line
        # and the keyword is on the next line
        return True  # In a multiline call, treat each keyword as multiline

    def _find_equals_for_keyword(self, keyword: ast.keyword) -> Tuple[int, int, bool, bool] | None:
        """
        Find the `=` token for a keyword argument and check spacing.
        
        Returns: (line, col, has_space_before, has_space_after) or None
        """
        # The keyword argument name is keyword.arg
        keyword_name = keyword.arg
        if not keyword_name:
            return None
        
        # The equals sign should be on the same line as the keyword value starts,
        # or possibly the line before
        target_line = keyword.value.lineno
        
        # Look through tokens to find keyword_name followed by '='
        # We need to make sure we're finding the keyword arg, not other uses of the name
        for i, token in enumerate(self.file_tokens):
            # Look for NAME token matching our keyword on or near the target line
            if (token.type == tokenize.NAME and 
                token.string == keyword_name and
                abs(token.start[0] - target_line) <= 1):
                
                # Check if this NAME token is followed by '=' (making it a keyword arg)
                # Skip any whitespace tokens
                for j in range(i + 1, min(i + 3, len(self.file_tokens))):
                    next_tok = self.file_tokens[j]
                    
                    # Skip whitespace-like tokens
                    if next_tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, 
                                        tokenize.DEDENT, tokenize.COMMENT):
                        continue
                    
                    # Found the equals - this must be our keyword argument
                    if next_tok.type == tokenize.OP and next_tok.string == '=':
                        # Make sure this isn't a comparison operator
                        # Check the token after '=' isn't another '=' (for ==)
                        if j + 1 < len(self.file_tokens):
                            after_eq = self.file_tokens[j + 1]
                            if after_eq.type == tokenize.OP and after_eq.string == '=':
                                break  # This is '==', not keyword arg
                        
                        # Check spacing before '='
                        has_space_before = token.end != next_tok.start
                        
                        # Check space after '='
                        has_space_after = False
                        if j + 1 < len(self.file_tokens):
                            after_tok = self.file_tokens[j + 1]
                            if after_tok.type not in (tokenize.NEWLINE, tokenize.NL):
                                has_space_after = next_tok.end != after_tok.start
                        
                        return (next_tok.start[0], next_tok.start[1], has_space_before, has_space_after)
                    
                    # If we hit any other token, this NAME isn't a keyword arg
                    break
        
        return None


def _load_file_tokens(physical_line, line_number, lines):
    """Helper to get file tokens for the checker."""
    # This is a bit of a hack, but flake8 doesn't pass tokens directly
    # We'll tokenize the entire file when needed
    return []


# Flake8 entry point using the older API that's more compatible
class MultilineNamedArgsCheckerPlugin:
    name = 'flake8-multiline-named-args'
    version = '1.0.0'

    def __init__(self, tree, filename, lines):
        self.tree = tree
        self.filename = filename
        self.lines = lines
        
        # Tokenize the file
        try:
            import io
            file_content = ''.join(lines)
            self.file_tokens = list(tokenize.generate_tokens(io.StringIO(file_content).readline))
        except:
            self.file_tokens = []

    def run(self):
        checker = MultilineNamedArgsChecker(self.tree, self.lines, self.file_tokens)
        yield from checker.run()