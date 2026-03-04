from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import transitions

COMMENT_CHARS = ("!", "#")


class TokenizerError(Exception):
    """Base tokenizer error with context."""
    
    def __init__(self, message, context=None):
        super().__init__(message)
        self.message = message
        self.context = context


class UnterminatedStringError(TokenizerError):
    """Error for unterminated strings."""
    pass


class InvalidTokenCharError(TokenizerError):
    """Error for invalid characters in tokens."""
    pass


@dataclass
class Context:
    colnr: Optional[int] = None
    colnrs: List[int] = field(default_factory=list)
    ref_colnr: Optional[int] = None
    line: Optional[str] = None
    ref_line: Optional[str] = None
    filename: Optional[str] = None
    section: Any = None
    section_stack: List[str] = field(default_factory=list)


@dataclass
class Token:
    string: str
    ctx: Context


class CP2KInputTokenizer(transitions.Machine):
    def begin_basic_token(self, _, colnr):
        self._current_token_start = colnr

    def end_basic_token(self, _, colnr: int):
        # the end idx follows the python-default of specifying ranges,
        # since this is triggered on the character after, using idx is correct
        self._tokens += [(self._current_token_start, colnr)]

    def begin_string_token(self, content, colnr):
        self._current_token_start = colnr
        self._tracking_quote_char = content[colnr]

    def end_string_token(self, content, colnr):
        # this is trigger ON the encounter of the string token, while the
        # end of the basic token is determined by the character that follows
        self._tokens += [(self._current_token_start, colnr + 1)]

    def unterminated_string(self, content, colnr):
        ctx = Context(
            colnr=colnr,
            ref_colnr=self._current_token_start,
            line=content
        )
        raise UnterminatedStringError("unterminated string detected", ctx)

    def invalid_token_char(self, content, colnr):
        ctx = Context(
            colnr=colnr,
            ref_colnr=self._current_token_start,
            line=content
        )
        raise InvalidTokenCharError("invalid keyword character found", ctx)

    def is_not_escaped(self, content, colnr):
        if colnr > 0:
            # possible to do: account for multiple escapes
            return content[colnr - 1] != "\\"

        return True

    @property
    def tokens(self):
        return self._tokens

    def is_matching_quote(self, content, colnr):
        return self._tracking_quote_char == content[colnr]

    def __init__(self):
        super().__init__(
            self,
            initial="lookout",
            states=[
                transitions.State(name="lookout"),
                transitions.State(name="basic_token", on_enter=["begin_basic_token"], on_exit=["end_basic_token"]),
                transitions.State(name="string_token", on_enter=["begin_string_token"], on_exit=["end_string_token"]),
                transitions.State(name="comment", on_enter=["begin_basic_token"], on_exit=["end_basic_token"]),
            ],
            transitions=[
                # start parsing a token:
                {"trigger": "token_char", "source": "lookout", "dest": "basic_token"},
                # ... unless we're already parsing a token or inside a string or comment
                {"trigger": "token_char", "source": ["basic_token", "string_token", "comment"], "dest": None},
                # '/" initiate strings
                {"trigger": "quote_char", "source": "lookout", "dest": "string_token"},
                {
                    "trigger": "quote_char",
                    "source": "string_token",
                    "dest": "lookout",
                    "conditions": ["is_not_escaped", "is_matching_quote"],
                },
                # a '!' or '#' initiates a comment (and terminates a token if necessary)
                {"trigger": "comment_char", "source": ["lookout", "basic_token"], "dest": "comment"},
                # ... unless inside a single or double quoted string, where it is consumed:
                {"trigger": "comment_char", "source": "string_token", "dest": None},
                # whitespace terminates a basic token
                {"trigger": "ws_char", "source": "basic_token", "dest": "lookout"},
                # ... and is consumed in all other cases
                {"trigger": "ws_char", "source": ["lookout", "string_token", "comment"], "dest": None},
                # single/double quotes are not allowed in a basic token:
                {"trigger": "quote_char", "source": "basic_token", "before": "invalid_token_char", "dest": None},
                # inside comments, quotes are regular characters
                {"trigger": "quote_char", "source": "comment", "dest": None},
                {"trigger": "nl_char", "source": ["basic_token", "comment"], "dest": "lookout"},
                {"trigger": "nl_char", "source": "lookout", "dest": None},
                {"trigger": "nl_char", "source": "string_token", "before": "unterminated_string", "dest": None},
            ],
        )

        self._tracking_quote_char = None
        self._current_token_start = 0
        self._tokens = []


def tokenize(string: str) -> Tuple[str, ...]:
    """Tokenize a CP2K input line.
    
    Args:
        string: The input line to tokenize
        
    Returns:
        Tuple of token strings
        
    Raises:
        UnterminatedStringError: If a string is not properly terminated
        InvalidTokenCharError: If an invalid character is found in a token
    """
    tokenizer = CP2KInputTokenizer()

    char_map = {" ": tokenizer.ws_char, "\t": tokenizer.ws_char, "'": tokenizer.quote_char, '"': tokenizer.quote_char}

    for cchar in COMMENT_CHARS:
        char_map[cchar] = tokenizer.comment_char

    for colnr, char in enumerate(string):
        char_map.get(char, tokenizer.token_char)(string, colnr)

    tokenizer.nl_char(string, len(string))

    return tuple(string[s:e] for s, e in tokenizer.tokens)


def tokenize_with_context(string: str, filename: Optional[str] = None, line_number: Optional[int] = None) -> List[Token]:
    """Tokenize a CP2K input line with context information.
    
    Args:
        string: The input line to tokenize
        filename: Optional filename for context
        line_number: Optional line number for context
        
    Returns:
        List of Token objects with context information
    """
    tokenizer = CP2KInputTokenizer()

    char_map = {" ": tokenizer.ws_char, "\t": tokenizer.ws_char, "'": tokenizer.quote_char, '"': tokenizer.quote_char}

    for cchar in COMMENT_CHARS:
        char_map[cchar] = tokenizer.comment_char

    for colnr, char in enumerate(string):
        char_map.get(char, tokenizer.token_char)(string, colnr)

    tokenizer.nl_char(string, len(string))

    tokens = []
    for s, e in tokenizer.tokens:
        ctx = Context(
            colnr=s,
            ref_colnr=e,
            line=string,
            filename=filename
        )
        tokens.append(Token(string[s:e], ctx))

    return tokens
