"""
Demo LSP Server — a minimal but functional language server.
Provides completions, diagnostics, hover, go-to-definition, and document symbols
for a simple demo language (.demo files).
"""

import re
import logging
from lsprotocol.types import (
    INITIALIZE,
    INITIALIZED,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    Hover,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    Location,
    SymbolKind,
    DocumentSymbol,
    ServerCapabilities,
    TextDocumentSyncKind,
    InitializeParams,
)
from pygls.server import LanguageServer


logging.basicConfig(
    level=logging.DEBUG,
    filename="/tmp/demo-lsp-server.log",
    filemode="w",
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

server = LanguageServer("demo-lsp", "v1.0.0")

# In-memory document store
documents: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@server.feature(INITIALIZE)
def initialize(ls: LanguageServer, params: InitializeParams):
    logger.info("Server initializing...")
    return ServerCapabilities(
        text_document_sync=TextDocumentSyncKind.FULL,
        completion_provider=CompletionOptions(
            trigger_characters=[".", ":", "@", " "],
            resolve_provider=False,
        ),
        hover_provider=True,
        definition_provider=True,
        document_symbol_provider=True,
    )


@server.feature(INITIALIZED)
def initialized(ls: LanguageServer, params):
    logger.info("Server initialized.")
    ls.show_message("Demo LSP Server started — ready for .demo files")


# ---------------------------------------------------------------------------
# Document sync
# ---------------------------------------------------------------------------

def _sync_doc(uri: str, text: str):
    documents[uri] = text
    _publish_diagnostics(uri, text)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params):
    _sync_doc(params.text_document.uri, params.text_document.text)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params):
    uri = params.text_document.uri
    text = params.content_changes[0].text  # Full sync — whole document
    _sync_doc(uri, text)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params):
    uri = params.text_document.uri
    if uri in documents:
        _publish_diagnostics(uri, documents[uri])


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

BUILTIN_WORDS = {
    "fn", "return", "let", "if", "else", "for", "while",
    "struct", "enum", "impl", "pub", "mod", "use", "true", "false", "nil",
    "print", "println", "format",
}

def _publish_diagnostics(uri: str, text: str):
    diags: list[Diagnostic] = []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if len(line) > 100:
            diags.append(Diagnostic(
                range=Range(
                    start=Position(line=i, character=100),
                    end=Position(line=i, character=len(line)),
                ),
                message=f"Line exceeds 100 characters ({len(line)})",
                severity=DiagnosticSeverity.Warning,
                source="demo-lsp",
            ))

        if line.endswith(" ") or line.endswith("\t"):
            diags.append(Diagnostic(
                range=Range(
                    start=Position(line=i, character=len(line.rstrip())),
                    end=Position(line=i, character=len(line)),
                ),
                message="Trailing whitespace",
                severity=DiagnosticSeverity.Information,
                source="demo-lsp",
            ))

        # Warn on unknown top-level keywords
        tokens = line.strip().split()
        if tokens and tokens[0] not in BUILTIN_WORDS and not line.strip().startswith("//"):
            if tokens[0].isalpha() and not tokens[0].startswith(("fn", "let", "struct", "enum", "impl", "pub", "mod", "use")):
                pass  # Could be a function call or assignment — skip

    server.publish_diagnostics(uri, diags)


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

COMPLETIONS = [
    CompletionItem(label="fn",    kind=CompletionItemKind.Keyword,    sort_text="01", detail="Define a function",            documentation="Declares a new function: `fn name(args) { ... }`"),
    CompletionItem(label="return", kind=CompletionItemKind.Keyword, sort_text="01", detail="Return from function",          documentation="Returns a value from the current function."),
    CompletionItem(label="let",   kind=CompletionItemKind.Keyword,    sort_text="01", detail="Variable binding",              documentation="Declares an immutable variable: `let x = 5;`"),
    CompletionItem(label="if",    kind=CompletionItemKind.Keyword,    sort_text="01", detail="Conditional branch",            documentation="Conditional: `if condition { ... } else { ... }`"),
    CompletionItem(label="else",  kind=CompletionItemKind.Keyword,    sort_text="01", detail="Alternative branch",            documentation="Alternative branch for `if`."),
    CompletionItem(label="for",   kind=CompletionItemKind.Keyword,    sort_text="01", detail="Loop over a range",             documentation="Loops over an iterator or range: `for x in 0..10 { ... }`"),
    CompletionItem(label="while", kind=CompletionItemKind.Keyword,    sort_text="01", detail="Conditional loop",              documentation="Loops while a condition is true."),
    CompletionItem(label="struct", kind=CompletionItemKind.Keyword,   sort_text="01", detail="Define a struct",               documentation="Defines a data structure: `struct Point { x: i32, y: i32 }`"),
    CompletionItem(label="enum",  kind=CompletionItemKind.Keyword,    sort_text="01", detail="Define an enum",                documentation="Defines an enumerated type."),
    CompletionItem(label="impl",  kind=CompletionItemKind.Keyword,    sort_text="01", detail="Implementation block",          documentation="Implements methods on a type."),
    CompletionItem(label="pub",   kind=CompletionItemKind.Keyword,    sort_text="01", detail="Public visibility modifier",    documentation="Makes the following item public."),
    CompletionItem(label="mod",   kind=CompletionItemKind.Keyword,    sort_text="01", detail="Module declaration",            documentation="Declares a module."),
    CompletionItem(label="use",   kind=CompletionItemKind.Keyword,    sort_text="01", detail="Import declaration",            documentation="Imports items from another module."),
    CompletionItem(label="true",  kind=CompletionItemKind.Value,      sort_text="01", detail="Boolean true",                  documentation="The boolean literal `true`."),
    CompletionItem(label="false", kind=CompletionItemKind.Value,      sort_text="01", detail="Boolean false",                 documentation="The boolean literal `false`."),
    CompletionItem(label="nil",   kind=CompletionItemKind.Value,      sort_text="01", detail="Null value",                    documentation="Represents the absence of a value."),
    CompletionItem(label="print", kind=CompletionItemKind.Function,   sort_text="02", detail="fn print(msg: str)",            documentation="Prints to stdout."),
    CompletionItem(label="println", kind=CompletionItemKind.Function, sort_text="02", detail="fn println(msg: str)",         documentation="Prints to stdout with a newline."),
    CompletionItem(label="format", kind=CompletionItemKind.Function,  sort_text="02", detail="fn format(tpl: str, ...)",     documentation="Formats a string with placeholders."),
    CompletionItem(label="read",  kind=CompletionItemKind.Function,   sort_text="02", detail="fn read() -> str",             documentation="Reads a line from stdin."),
]


def _get_word_at_cursor(line: str, char: int) -> str:
    m = re.search(r"(\w+)$", line[:char])
    return m.group(1) if m else ""


@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: LanguageServer, params: CompletionParams):
    uri = params.text_document.uri
    if uri not in documents:
        return None

    doc = documents[uri]
    lines = doc.splitlines()
    line = lines[params.position.line] if params.position.line < len(lines) else ""
    prefix = _get_word_at_cursor(line, params.position.character)

    items = [c for c in COMPLETIONS if c.label.startswith(prefix)] if prefix else COMPLETIONS
    return CompletionList(is_incomplete=False, items=items)


# ---------------------------------------------------------------------------
# Hover
# ---------------------------------------------------------------------------

@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params):
    uri = params.text_document.uri
    if uri not in documents:
        return None

    doc = documents[uri]
    lines = doc.splitlines()
    line = lines[params.position.line] if params.position.line < len(lines) else ""
    word = _get_word_at_cursor(line, params.position.character)

    hover_map = {
        "fn":      "### fn — Function Definition\nDeclares a new function.\n```\nfn name(param: Type) -> ReturnType {\n    // body\n}\n```",
        "let":     "### let — Variable Binding\nDeclares an immutable variable. Use `let mut` for mutable.\n```\nlet x = 42;\nlet mut y = 7;\n```",
        "struct":  "### struct — Data Structure\nDefines a composite data type.\n```\nstruct User {\n    name: String,\n    age: u32,\n}\n```",
        "enum":    "### enum — Enumerated Type\nDefines a type with a fixed set of variants.\n```\nenum Color {\n    Red,\n    Green,\n    Blue,\n}\n```",
        "if":      "### if — Conditional\n```\nif condition {\n    // true branch\n} else {\n    // false branch\n}\n```",
        "for":     "### for — Iteration Loop\n```\nfor item in collection {\n    // body\n}\n```",
        "while":   "### while — Conditional Loop\n```\nwhile condition {\n    // body\n}\n```",
        "return":  "### return — Return from Function\nExits the current function, optionally returning a value.\n```\nreturn expr;\n```",
        "impl":    "### impl — Implementation Block\nAdds methods to a type.\n```\nimpl MyType {\n    fn method(&self) { }\n}\n```",
        "pub":     "### pub — Public Visibility\nMakes the following declaration accessible from outside its module.",
        "mod":     "### mod — Module Declaration\nDeclares a submodule.\n```\nmod my_module;\n```",
        "print":   "### print(msg: str)\nPrints a message to standard output (no trailing newline).",
        "println": "### println(msg: str)\nPrints a message to standard output with a trailing newline.",
        "format":  "### format(template: str, ...args) -> str\nReturns a formatted string using `{}` placeholders.",
    }

    if word not in hover_map:
        return None

    return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=hover_map[word]))


# ---------------------------------------------------------------------------
# Go-to-definition
# ---------------------------------------------------------------------------

FUNC_PATTERN = re.compile(r"^\s*fn\s+(\w+)\s*\(", re.MULTILINE)
STRUCT_PATTERN = re.compile(r"^\s*struct\s+(\w+)", re.MULTILINE)


@server.feature(TEXT_DOCUMENT_DEFINITION)
def goto_definition(ls: LanguageServer, params):
    uri = params.text_document.uri
    if uri not in documents:
        return None

    text = documents[uri]
    lines = text.splitlines()
    line = lines[params.position.line] if params.position.line < len(lines) else ""
    word = _get_word_at_cursor(line, params.position.character)

    if not word:
        return None

    for pattern, ident_group in [(FUNC_PATTERN, 1), (STRUCT_PATTERN, 1)]:
        for m in pattern.finditer(text):
            if m.group(ident_group) == word:
                start_line = text[: m.start()].count("\n")
                col = m.start() - (text[: m.start()].rfind("\n") + 1 if "\n" in text[: m.start()] else 0)
                return Location(
                    uri=uri,
                    range=Range(
                        start=Position(line=start_line, character=col),
                        end=Position(line=start_line, character=col + len(m.group(0).strip().split()[0])),
                    ),
                )
    return None


# ---------------------------------------------------------------------------
# Document Symbols
# ---------------------------------------------------------------------------

@server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls: LanguageServer, params):
    uri = params.text_document.uri
    if uri not in documents:
        return None

    text = documents[uri]
    symbols: list[DocumentSymbol] = []

    for pattern, kind, label_prefix in [
        (FUNC_PATTERN, SymbolKind.Function, "fn "),
        (STRUCT_PATTERN, SymbolKind.Struct, "struct "),
    ]:
        for m in pattern.finditer(text):
            name = m.group(1)
            start_line = text[: m.start()].count("\n")
            end_col = len(m.group(0))
            symbols.append(DocumentSymbol(
                name=label_prefix + name,
                kind=kind,
                range=Range(
                    start=Position(line=start_line, character=0),
                    end=Position(line=start_line, character=end_col),
                ),
                selection_range=Range(
                    start=Position(line=start_line, character=len(label_prefix)),
                    end=Position(line=start_line, character=len(label_prefix) + len(name)),
                ),
            ))

    return symbols if symbols else None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Demo LSP server starting on stdio...")
    server.start_io()
