"""
Flake8 plugin to enforce spacing around `=` in multiline function calls.

Rules:
- MNA001: Missing spaces around `=` in multiline function call
- MNA002: Unexpected spaces around `=` in single-line function call (replaces E251)
- MNA003: Multiple keyword arguments on same line in multiline function call

This plugin reimplements E251 to allow spaces around `=` in multiline calls
while still catching them in single-line calls. Configure flake8 to ignore E251
when using this plugin.

Rationale:
These rules improve readability in multiline function calls by:
- Enforcing visual consistency with spaces around `=` making keyword args easier to scan
- Ensuring each keyword argument gets its own line for better diff visibility
- Maintaining PEP 8 compliance for single-line calls (no spaces around `=`)

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
    
    Incorrect multiline usage (MNA003):
        result = foo(a = 1, b = 2,
                     c = 3,
                     )
        
        result = foo(1, 2, a = 3,
                     b = 4,
                     )
"""
import ast
import io
import tokenize
from typing import Generator, Tuple, List, Dict, Optional, Set
from dataclasses import dataclass


# Constants
LINE_SEARCH_TOLERANCE = 1  # How many lines away from target to search for tokens
MAX_TOKEN_LOOKAHEAD = 3    # Maximum tokens to look ahead when finding '='

# Error message templates
ERROR_MESSAGES = {
    'MNA001': "MNA001 missing spaces around '=' in multiline function call",
    'MNA002': "MNA002 unexpected spaces around '=' in single-line function call",
    'MNA003_MULTIPLE': "MNA003 multiple keyword arguments on same line in multiline function call (found: {keywords})",
    'MNA003_POSITIONAL': "MNA003 keyword argument '{keyword}' shares line with positional arguments in multiline function call",
}


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

        # Cache equals info to avoid redundant token lookups
        keyword_equals_cache: Dict[ast.keyword, Optional[EqualsTokenInfo]] = {}
        for keyword in node.keywords:
            if keyword.arg is not None:  # Skip **kwargs
                keyword_equals_cache[keyword] = self._find_equals_for_keyword(keyword)

        # For multiline calls, check that each line has at most one keyword argument
        if is_multiline:
            self._check_one_keyword_per_line(node, keyword_equals_cache)

        # Check each keyword argument individually for spacing
        for keyword in node.keywords:
            if keyword.arg is None:  # Skip **kwargs
                continue

            equals_info = keyword_equals_cache.get(keyword)
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
                        ERROR_MESSAGES['MNA001'],
                        type(self),
                    ))
            else:
                # Rule: Single-line calls MUST NOT have spaces around `=`
                if equals_info.has_space_before or equals_info.has_space_after:
                    self.errors.append((
                        equals_info.line,
                        equals_info.col,
                        ERROR_MESSAGES['MNA002'],
                        type(self),
                    ))
    
    def _check_one_keyword_per_line(
        self, 
        node: ast.Call, 
        keyword_equals_cache: Dict[ast.keyword, Optional[EqualsTokenInfo]]
    ) -> None:
        """
        Check that in multiline calls, each keyword argument is on its own line
        with no other arguments (positional or keyword).
        
        This improves readability and makes diffs clearer when arguments change.
        """
        # Track which lines have keyword arguments, storing keyword objects
        lines_with_keywords: Dict[int, List[ast.keyword]] = {}
        # Track which lines have any part of positional arguments
        lines_with_positional: Set[int] = set()
        
        # Check positional arguments - track all lines they span
        for arg in node.args:
            # Add all lines from start to end of the argument
            for line in range(arg.lineno, arg.end_lineno + 1):
                lines_with_positional.add(line)
        
        # Check keyword arguments
        for keyword in node.keywords:
            if keyword.arg is None:  # Skip **kwargs
                continue
            
            equals_info = keyword_equals_cache.get(keyword)
            if not equals_info:
                continue
            
            line = equals_info.line
            if line not in lines_with_keywords:
                lines_with_keywords[line] = []
            lines_with_keywords[line].append(keyword)
        
        # Report errors for lines with multiple keyword arguments
        # Report one error per additional keyword (so 3 keywords = 2 errors)
        for line, keywords in lines_with_keywords.items():
            if len(keywords) > 1:
                keyword_names = [kw.arg for kw in keywords]
                
                # Report error for each keyword after the first
                for keyword in keywords[1:]:
                    equals_info = keyword_equals_cache.get(keyword)
                    # This should always exist since we got it from the cache, but check anyway
                    # to avoid errors if token parsing failed for some reason
                    if equals_info:
                        self.errors.append((
                            equals_info.line,
                            equals_info.col,
                            ERROR_MESSAGES['MNA003_MULTIPLE'].format(keywords=', '.join(keyword_names)),
                            type(self),
                        ))
        
        # Report errors for keyword arguments that share a line with positional arguments
        for line, keywords in lines_with_keywords.items():
            if line in lines_with_positional:
                # Report error for all keywords on this line
                for keyword in keywords:
                    equals_info = keyword_equals_cache.get(keyword)
                    if equals_info:
                        self.errors.append((
                            equals_info.line,
                            equals_info.col,
                            ERROR_MESSAGES['MNA003_POSITIONAL'].format(keyword=keyword.arg),
                            type(self),
                        ))

    def _find_equals_for_keyword(self, keyword: ast.keyword) -> Optional[EqualsTokenInfo]:
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
        
        # Get the column offset of the keyword argument from the AST
        # This helps us narrow down which NAME token is the actual keyword arg
        keyword_col = keyword.col_offset
        
        # Look through tokens to find keyword_name followed by '='
        # We need to make sure we're finding the keyword arg, not other uses of the name
        for i, token in enumerate(self.file_tokens):
            # Look for NAME token matching our keyword on or near the target line
            # Also check that the column is close to what the AST reports
            if (token.type == tokenize.NAME and 
                token.string == keyword_name and
                abs(token.start[0] - target_line) <= LINE_SEARCH_TOLERANCE and
                abs(token.start[1] - keyword_col) <= 5):  # Within 5 columns
                
                # Check if this NAME token is followed by '=' (making it a keyword arg)
                for j in range(i + 1, min(i + MAX_TOKEN_LOOKAHEAD, len(self.file_tokens))):
                    next_tok = self.file_tokens[j]
                    
                    # Skip whitespace-like tokens
                    if next_tok.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, 
                                        tokenize.DEDENT, tokenize.COMMENT):
                        continue
                    
                    # Found the equals - verify it's a keyword argument assignment
                    if next_tok.type == tokenize.OP and next_tok.string == '=':
                        # Make sure this isn't part of a comparison operator
                        # Check token BEFORE for !, <, > (for !=, <=, >=)
                        if j > 0:
                            prev_tok = self.file_tokens[j - 1]
                            if prev_tok.type == tokenize.OP and prev_tok.string in ('!', '<', '>'):
                                break  # This is part of !=, <=, or >=
                        
                        # Check token AFTER for = (for ==)
                        if j + 1 < len(self.file_tokens):
                            after_eq = self.file_tokens[j + 1]
                            if after_eq.type == tokenize.OP and after_eq.string == '=':
                                break  # This is ==
                        
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
        except tokenize.TokenError:
            # If tokenization fails, we can't check spacing
            # This might happen with syntax errors, which flake8 will catch separately
            self.file_tokens = []
        except Exception:
            # Catch other unexpected errors to avoid breaking flake8
            # This is a safety net for unexpected tokenization issues
            self.file_tokens = []

    def run(self) -> Generator[Tuple[int, int, str, type], None, None]:
        """Run the checker and yield violations."""
        if not self.file_tokens:
            # Can't check without tokens
            return
            
        checker = MultilineNamedArgsChecker(self.tree, self.lines, self.file_tokens)
        yield from checker.run()