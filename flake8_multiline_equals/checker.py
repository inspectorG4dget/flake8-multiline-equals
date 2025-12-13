"""
Flake8 plugin to enforce spacing around `=` in multiline function calls.

Rules:
- MNA001: Missing spaces around `=` in multiline function call
- MNA002: Unexpected spaces around `=` in single-line function call (replaces E251)

This plugin reimplements E251 to allow spaces around `=` in multiline calls
while still catching them in single-line calls. Configure flake8 to ignore E251
when using this plugin.

Examples:
    Correct single-line usage:
        result = foo(a=1, b=2)
    
    Incorrect single-line usage (MNA002):
        result = foo(a = 1, b = 2)
    
    Correct multiline usage:
        result = foo(
            a = 1,
            b = 2,
        )
    
    Incorrect multiline usage (MNA001):
        result = foo(
            a=1,
            b=2,
        )
"""
import ast
import io
import tokenize
from typing import Generator, Tuple, List
from dataclasses import dataclass


# Constants
LINE_SEARCH_TOLERANCE = 1  # How many lines away from target to search for tokens
MAX_TOKEN_LOOKAHEAD = 3    # Maximum tokens to look ahead when finding '='


@dataclass
class EqualsTokenInfo:
    """Information about an equals sign token in a keyword argument."""
    line: int
    col: int
    has_space_before: bool
    has_space_after: bool


class MultilineNamedArgsChecker(ast.NodeVisitor):
    """AST visitor that checks keyword argument spacing in function calls."""
    
    name = 'flake8-multiline-named-args'
    version = '1.0.0'

    def __init__(self, tree: ast.AST, lines: List[str], file_tokens: List[tokenize.TokenInfo]):
        self.tree = tree
        self.lines = lines
        self.file_tokens = file_tokens
        self.errors: List[Tuple[int, int, str, type]] = []

    def run(self) -> Generator[Tuple[int, int, str, type], None, None]:
        """Run the checker and yield violations."""
        self.visit(self.tree)
        yield from self.errors

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call node and check keyword arguments."""
        self._check_call(node)
        self.generic_visit(node)

    def _check_call(self, node: ast.Call) -> None:
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

            # For multiline calls, all keywords are treated as multiline
            # For single-line calls, all keywords are treated as single-line
            if is_multiline:
                # Rule: Multiline calls MUST have spaces around `=`
                if not equals_info.has_space_before or not equals_info.has_space_after:
                    self.errors.append((
                        equals_info.line,
                        equals_info.col,
                        "MNA001 missing spaces around '=' in multiline function call",
                        type(self),
                    ))
            else:
                # Rule: Single-line calls MUST NOT have spaces around `=`
                if equals_info.has_space_before or equals_info.has_space_after:
                    self.errors.append((
                        equals_info.line,
                        equals_info.col,
                        "MNA002 unexpected spaces around '=' in single-line function call",
                        type(self),
                    ))

    def _find_equals_for_keyword(self, keyword: ast.keyword) -> EqualsTokenInfo | None:
        """
        Find the `=` token for a keyword argument and check spacing.
        
        Args:
            keyword: The keyword argument AST node
            
        Returns:
            EqualsTokenInfo if found, None otherwise
        """
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
                abs(token.start[0] - target_line) <= LINE_SEARCH_TOLERANCE):
                
                # Check if this NAME token is followed by '=' (making it a keyword arg)
                for j in range(i + 1, min(i + MAX_TOKEN_LOOKAHEAD, len(self.file_tokens))):
                    next_tok = self.file_tokens[j]
                    
                    # Skip whitespace-like tokens
                    if next_tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, 
                                        tokenize.DEDENT, tokenize.COMMENT):
                        continue
                    
                    # Found the equals - this must be our keyword argument
                    if next_tok.type == tokenize.OP and next_tok.string == '=':
                        # Make sure this isn't a comparison operator (==, !=, <=, >=)
                        if j + 1 < len(self.file_tokens):
                            after_eq = self.file_tokens[j + 1]
                            if after_eq.type == tokenize.OP and after_eq.string in ('=', '!', '<', '>'):
                                break  # This is a comparison operator, not keyword arg
                        
                        # Check spacing before '='
                        has_space_before = token.end != next_tok.start
                        
                        # Check space after '='
                        has_space_after = False
                        if j + 1 < len(self.file_tokens):
                            after_tok = self.file_tokens[j + 1]
                            if after_tok.type not in (tokenize.NEWLINE, tokenize.NL):
                                has_space_after = next_tok.end != after_tok.start
                        
                        return EqualsTokenInfo(
                            line=next_tok.start[0],
                            col=next_tok.start[1],
                            has_space_before=has_space_before,
                            has_space_after=has_space_after
                        )
                    
                    # If we hit any other token, this NAME isn't a keyword arg
                    break
        
        return None


class MultilineNamedArgsCheckerPlugin:
    """Flake8 plugin entry point."""
    
    name = 'flake8-multiline-named-args'
    version = '1.0.0'

    def __init__(self, tree: ast.AST, filename: str, lines: List[str]):
        self.tree = tree
        self.filename = filename
        self.lines = lines
        
        # Tokenize the file
        try:
            file_content = ''.join(lines)
            self.file_tokens = list(tokenize.generate_tokens(io.StringIO(file_content).readline))
        except tokenize.TokenError as e:
            # If tokenization fails, we can't check spacing
            # This might happen with syntax errors, which flake8 will catch separately
            self.file_tokens = []
        except Exception as e:
            # Catch other unexpected errors to avoid breaking flake8
            # Log could be added here in future versions
            self.file_tokens = []

    def run(self) -> Generator[Tuple[int, int, str, type], None, None]:
        """Run the checker and yield violations."""
        if not self.file_tokens:
            # Can't check without tokens
            return
            
        checker = MultilineNamedArgsChecker(self.tree, self.lines, self.file_tokens)
        yield from checker.run()