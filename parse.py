# Shelest Oleksii
# xshele02
# IPP parse.py

import sys
import re
import xml.etree.ElementTree as ET
from lark import Lark, UnexpectedCharacters, UnexpectedInput, Token, Tree

# Druhy chyb
ERR_OK = 0
ERR_SCRIPT = 10
ERR_LEXICAL = 21
ERR_SYNTAX = 22
ERR_MAIN_RUN = 31
ERR_NON_DEF = 32
ERR_ARITA = 33
ERR_COLLISION = 34
ERR_OTHER = 35


def check_args():
    """Funkce pro kontrolu vstupu argumentů"""
    if len(sys.argv) > 2:
        sys.stderr.write("Chyba (10): Příliš velký počet parametrů\n")
        sys.exit(ERR_SCRIPT)
    if len(sys.argv) == 2:
        if '--help' in sys.argv:
            print("Skript typu filtr (parse.py v jazyce Python)\n"
                  "načte ze standardního vstupu zdrojový kod v SOL25\n"
                  "zkontroluje lexikální, syntaktickou a statickou sémantickou správnost kódu\n"
                  "a vypíše na standardní výstup XML reprezentaci programu.")
            sys.exit(ERR_OK)
        else:
            sys.stderr.write("Chyba (10): Špatné parametry\n")
            sys.exit(ERR_SCRIPT)


# Gramatika pro lexer a parser Lark
sol25_grammar = r"""
start: class_def+

class_def: "class" CLASS_IDENT ":" CLASS_IDENT "{" method_def* "}"

method_def: method_selector "[" param_list? "|" statement* "]"

method_selector: IDENT | (METHOD_IDENT)+

param_list: (PARAM_IDENT)*

statement: assignment | message_send | block_stmt
assignment: IDENT ":=" expr "."

expr: simple_expr | message_send

simple_expr: CLASS_IDENT           -> class_literal
           | IDENT                 -> var
           | INTEGER               -> integer
           | STRING                -> string
           | TRUE                  -> true
           | FALSE                 -> false
           | NIL                   -> nil
           | SELF                  -> self
           | SUPER                 -> super
           | "(" expr ")"          -> grouped_expr
           | block

message_send: simple_expr ( non_param_send | param_send )

non_param_send: IDENT

param_send: (METHOD_IDENT expr)+

block_stmt: block "."
block: "[" param_list? "|" statement* "]"

CLASS: "class"
SELF: "self"
SUPER: "super"
NIL: "nil"
TRUE: "true"
FALSE: "false"

CLASS_IDENT: /[A-Z][a-zA-Z0-9_]*/
PARAM_IDENT: /:[a-z_][a-zA-Z0-9_]*/
IDENT: /[a-z_][a-zA-Z0-9_]*/
METHOD_IDENT: /([a-z_][a-zA-Z0-9_]*:)+/
INTEGER: /[+-]?\d+/
STRING: /'([^'\\\n]|\\['\\n])*'/
COMMENT: /"[^"]*"/

%ignore /\s+/
%ignore COMMENT
"""

lexer = Lark(sol25_grammar, start="start", parser="lalr")


def lexical_analysis(code):
    """Funkce pro lexikální kontrolu pomocí Lark """
    try:
        tokens = list(lexer.lex(code))
        # print("Tokens:", tokens)
    except UnexpectedCharacters as e:
        sys.stderr.write("Lexikální chyba (21): neplatný znak nebo token\n")
        sys.exit(ERR_LEXICAL)


def parse_tokens(code):
    """Funkce pro syntaktickou kontrolu pomocí Lark"""
    try:
        tree = lexer.parse(code)
        check_reserved_identifiers(tree)
        return tree

    except UnexpectedInput:
        sys.stderr.write(
            "Syntaktická chyba (22): nesprávná struktura kódu\n")
        sys.exit(ERR_SYNTAX)


KEYWORDS = {"class", "self", "super", "nil", "true", "false"}


def check_reserved_identifiers(tree):
    """Funkce, která kontroluje, zda jsou klíčová slova použita tam, kde by být použita neměla"""
    for node in tree.iter_subtrees():
        if node.data == "assignment":
            var_name = node.children[0]
            if isinstance(var_name, str) and var_name in KEYWORDS:
                sys.stderr.write(
                    f"Syntaktická chyba (22): <{var_name}> nemůže být proměnnou\n")
                sys.exit(ERR_SYNTAX)

        if node.data == "param_list":
            for param in node.children:
                param_name = param.value.lstrip(
                    ":")
                if param_name in KEYWORDS:
                    sys.stderr.write(
                        f"Syntaktická chyba (22): <{param_name}> nemůže být parametrem v bloku\n")
                    sys.exit(ERR_SYNTAX)

        if node.data == "method_selector":
            method_name = node.children[0].value.strip(":")
            if method_name in KEYWORDS:
                sys.stderr.write(
                    f"Syntaktická chyba (22): <{method_name}> nemůže být názvem selektoru\n")
                sys.exit(ERR_SYNTAX)

        if node.data == "non_param_send":
            method_name = node.children[0].value
            if method_name in KEYWORDS:
                sys.stderr.write(
                    f"Syntaktická chyba (22): <{method_name}> nelze použít jako selektor\n")
                sys.exit(ERR_SYNTAX)


def check_main_class(ast):
    """Funkce, která kontroluje přítomnost třídy Main s povinným selektorem run"""
    main_found = False
    for cls in ast.find_data("class_def"):
        class_name = cls.children[0].value
        if class_name == "Main":
            for method in cls.find_data("method_def"):
                selector = method.children[0]
                if selector.data == "method_selector" and selector.children[0].value == "run":
                    main_found = True
                    break
    if not main_found:
        sys.stderr.write(
            "Sémantická chyba (31): chybí třída Main s metodou run\n")
        sys.exit(ERR_MAIN_RUN)


# Vestavěné třídy spolu s jejich selektory a jejich aritou
BUILTIN_METHODS = {
    "Object": {
        "new": 0,
        "from:": 1,
        "identicalTo:": 1,
        "equalTo:": 1,
        "asString": 0,
        "isNumber": 0,
        "isString": 0,
        "isBlock": 0,
        "isNil": 0
    },
    "Integer": {
        "equalTo:": 1,
        "greaterThan:": 1,
        "plus:": 1,
        "minus:": 1,
        "multiplyBy:": 1,
        "divBy:": 1,
        "asString": 0,
        "asInteger": 0,
        "timesRepeat:": 1
    },
    "String": {
        "read": 0,
        "print": 0,
        "equalTo:": 1,
        "asString": 0,
        "asInteger": 0,
        "concatenateWith:": 1,
        "startsWith:endsBefore:": 2
    },
    "Block": {
        "whileTrue:": 1,
        "value": 0,
        "value:": 1,
        "value:value:": 2,
        "value:value:value:": 3,
    },
    "True": {
        "not": 0,
        "and:": 1,
        "or:": 1,
        "ifTrue:ifFalse:": 2
    },
    "False": {
        "not": 0,
        "and:": 1,
        "or:": 1,
        "ifTrue:ifFalse:": 2
    },
    "Nil": {
        "asString": 0
    }
}


GLOBAL_OBJECTS = {"nil", "true", "false"}


def semantic_check_variables(node, local_vars=None, formal_params=None):
    """Funkce, která slouží k kontrole použití proměnných v kódu a jejich rozsahu platnosti"""
    if local_vars is None:
        local_vars = set()
    if formal_params is None:
        formal_params = set()

    if isinstance(node, Tree):
        if node.data in {"block", "block_stmt", "method_def"}:
            new_local_vars = set()
            new_formal_params = set()

            for child in node.children:
                if hasattr(child, "data") and child.data == "param_list":
                    for param in child.children:
                        param_name = param.value.lstrip(":")
                        if param_name in new_formal_params:
                            sys.stderr.write(
                                f"Sémantická chyba(35): Parametr bloku <{param_name}> je již deklarován v bloku <{node.children[0].children[0].value}>\n")
                            sys.exit(ERR_OTHER)
                        new_formal_params.add(param_name)
            for child in node.children:
                semantic_check_variables(
                    child, local_vars=new_local_vars, formal_params=new_formal_params)
            return

        if node.data == "assignment":
            var_name = node.children[0].value

            if var_name in formal_params:
                sys.stderr.write(
                    f"Sémantická chyba (34): proměnná <{var_name}> je již deklarována jako parametr a nelze ji změnit\n"
                )
                sys.exit(ERR_COLLISION)

            local_vars.add(var_name)

            semantic_check_variables(
                node.children[1], local_vars, formal_params)

            return

        if node.data == "var":
            var_name = node.children[0].value

            if var_name not in local_vars and var_name not in formal_params and var_name not in GLOBAL_OBJECTS:
                sys.stderr.write(
                    f"Sémantická chyba (32): proměnná <{var_name}> není definována před použitím\n"
                )
                sys.exit(ERR_NON_DEF)
            return

        for child in node.children:
            semantic_check_variables(child, local_vars, formal_params)


def semantic_check_method_arities(ast):
    """Funkce pro kontrolu arity selektoru"""
    for node in ast.find_data("method_def"):
        selector_node = node.children[0]
        if selector_node.children[0].type == "IDENT":
            expected_params = 0
        else:
            expected_params = selector_node.children[0].value.count(
                ":")  # počet dvojteček = počet parametrů

        param_list_node = None
        for child in node.children:
            if hasattr(child, "data") and child.data == "param_list":
                param_list_node = child
                break

        actual_params = len(
            param_list_node.children) if param_list_node is not None else 0

        if expected_params != actual_params:
            sys.stderr.write(
                "Sémantická chyba (33): počet parametrů v bloku neodpovídá počtu parametrů v bloku.\n"
            )
            sys.exit(ERR_ARITA)


def gather_class_info(ast):
    """Funkce pro sběr informací o všech třídách a jejich selektorů"""
    builtin_classes = set(BUILTIN_METHODS.keys())
    classes = {}

    for builtin in builtin_classes:
        classes[builtin] = {
            "parent": "Object" if builtin != "Object" else None,
            "methods": BUILTIN_METHODS.get(builtin, {})
        }
    for class_node in ast.find_data("class_def"):
        class_name = class_node.children[0].value
        parent_class = class_node.children[1].value
        methods = {}

        for method_node in class_node.find_data("method_def"):
            selector_node = method_node.children[0]
            if selector_node.children[0].type == "IDENT":
                selector = selector_node.children[0].value
                arity = 0
            else:
                selector = "".join(
                    token.value for token in selector_node.children)
                arity = selector.count(":")
            if selector in methods:
                sys.stderr.write(
                    f"Sémantická chyba (35): selektor <{selector}> již existuje'\n")
                sys.exit(ERR_OTHER)
            else:
                methods[selector] = arity
        if class_name in builtin_classes or class_name in classes:
            sys.stderr.write(
                f"Sémantická chyba (35): třída <{class_name}> již existuje'\n")
            sys.exit(ERR_OTHER)
        elif parent_class == class_name:
            sys.stderr.write(
                f"Sémantická chyba (35): třída <{class_name}> dědí sama sebe\n")
            sys.exit(ERR_OTHER)
        else:
            classes[class_name] = {"parent": parent_class, "methods": methods}

    return classes


def check_circular_inheritance(classes):
    """Funkce pro kontrolu kruhového dědění tříd."""
    def is_circular(class_name, visited_classes):
        if class_name in visited_classes:
            return True
        visited_classes.add(class_name)

        parent = classes.get(class_name, {}).get('parent')
        if parent is None:
            return False
        return is_circular(parent, visited_classes)

    for class_names in classes:
        visited_classes = set()
        if is_circular(class_names, visited_classes):
            sys.stderr.write(
                f"Sémantická chyba (35): kruhové dědění zjištěno u třídy <{class_names}>\n")
            sys.exit(ERR_OTHER)


def semantic_check_class_usage(ast, defined_classes):
    """Funkce, která kontroluje správnost inicializace tříd v kódu a jejich použití"""
    builtin_classes = set(BUILTIN_METHODS.keys())

    for node in ast.find_data("class_literal"):
        class_name = node.children[0].value
        if class_name not in defined_classes and class_name not in builtin_classes:
            sys.stderr.write(
                f"Sémantická chyba (32): použití nedefinované třídy <{class_name}>\n")
            sys.exit(ERR_NON_DEF)

    for class_node in ast.find_data("class_def"):
        class_name = class_node.children[0].value
        parent_class = class_node.children[1].value
        if parent_class not in defined_classes and parent_class not in builtin_classes:
            sys.stderr.write(
                f"Sémantická chyba (32): třída <{class_name}> dědí nedefinovanou třídu <{parent_class}>\n")
            sys.exit(ERR_NON_DEF)
        if parent_class == class_name:
            sys.stderr.write(
                f"Sémantická chyba (35): třída <{class_name}> dědí sama sebe'\n")
            sys.exit(ERR_OTHER)


def find_method_in_class(class_name, selector, classes):
    """Funkce pro vyhledávání selektoru ve třídách"""
    if class_name in classes:
        if selector in classes[class_name]["methods"]:
            return classes[class_name]["methods"][selector]
        else:
            parent_class = classes[class_name]["parent"]
            return find_method_in_class(parent_class, selector, classes)
        return None


def method_exists_in_class_or_builtin(class_name, selector, classes):
    """Funkce, která vrací True, pokud selektor existuje, nebo False, pokud neexistuje."""
    if find_method_in_class(class_name, selector, classes) is not None:
        return True

    for builtin_class, methods in BUILTIN_METHODS.items():
        if selector in methods:
            return True

    return False

##############################################################################################################################################
# XML
##############################################################################################################################################


def generate_xml(tree, classes):
    """Funkce, ve které začíná generování kódu XML"""
    description = find_first_comment(
        input_code)  # vezmeme první komentář v kódu
    if description:
        program_elem = ET.Element(
            "program", language="SOL25", description=description)
    else:
        program_elem = ET.Element("program", language="SOL25")
    # zpracování tříd a selektorů v kódu
    for class_node in tree.find_data("class_def"):
        class_name = class_node.children[0].value
        parent_name = class_node.children[1].value
        class_elem = ET.SubElement(
            program_elem, "class", name=class_name, parent=parent_name)
        for method_node in class_node.find_data("method_def"):
            selector_node = method_node.children[0]
            if selector_node.children[0].type == "IDENT":
                selector = selector_node.children[0].value
            else:
                selector = "".join(
                    token.value for token in selector_node.children)
            method_elem = ET.SubElement(
                class_elem, "method", selector=selector)
            # začneme zpracovávat bloky uvnitř
            block_elem = generate_method_block(
                method_node, class_name, classes)
            method_elem.append(block_elem)
    return program_elem


def generate_method_block(method_node, class_name, classes):
    """Funkce pro vytvoření elementu v XML pro popis bloku(selektoru)"""
    params = []
    statements = []

    for child in method_node.children:
        if hasattr(child, "data"):
            if child.data == "param_list":
                params = child.children
            elif child.data == "statement":
                for stmt in child.children:
                    if hasattr(stmt, "data") and stmt.data in {"assignment", "message_send", "block_stmt"}:
                        statements.append(stmt)

    arity = len(params)
    block_elem = ET.Element("block", arity=str(arity))

    # Přidáme parametry metody do XML
    for idx, param in enumerate(params, start=1):
        param_name = param.value.lstrip(":")
        ET.SubElement(block_elem, "parameter", name=param_name, order=str(idx))

    order = 1

    # Zpracujeme příkazy uvnitř metody
    for stmt in statements:
        cmd_elem = generate_command(
            stmt, order, class_name, classes)
        block_elem.append(cmd_elem)
        order += 1

    return block_elem


def generate_command(cmd_node, order, class_name, classes):
    """Funkce pro vytvoření prvku v XML pro popis příkazu přiřazení"""
    if cmd_node.data == "assignment":
        assign_elem = ET.Element("assign", order=str(order))

        var_token = cmd_node.children[0]
        ET.SubElement(assign_elem, "var", name=var_token.value)
        expr_inner = generate_expr(
            cmd_node.children[1], class_name, classes, var_token.value)

        # Pokud je prvek již "expr", přímo ho použijeme
        if expr_inner.tag == "expr":
            expr_elem = expr_inner
        else:
            expr_elem = ET.Element("expr")
            expr_elem.append(expr_inner)

        assign_elem.append(expr_elem)
        return assign_elem

    return generic_elem


def generate_expr(expr_node, global_class_name, classes, var_token):
    """Funkce pro generování výrazu v XML"""

    # Pokud uzel obsahuje tokeny a první není uzel se strukturou
    if expr_node.children and not hasattr(expr_node.children[0], "data"):
        expr_elem = ET.Element("expr")
        for token in expr_node.children:
            expr_elem.append(process_token(token, global_class_name, classes))
        return expr_elem

    # Zpracování "self" a "super"
    if hasattr(expr_node, "type") and expr_node.type == "SELF":
        return ET.Element("var", name="self")
    if expr_node.data == "self":
        return ET.Element("var", name="self")
    if hasattr(expr_node, "type") and expr_node.type == "SUPER":
        return ET.Element("var", name="super")
    if expr_node.data == "super":
        return ET.Element("var", name="super")
    # Zpracování třídy
    if expr_node.data == "class_literal":
        class_name = expr_node.children[0].value
        return ET.Element("literal", **{"class": "class", "value": class_name})

    if expr_node.children and hasattr(expr_node.children[0], "data"):
        first_child = expr_node.children[0]
        if first_child.data == "integer":
            if first_child.children and hasattr(first_child.children[0], "data"):
                value = first_child.children[0].value
            else:
                value = first_child.children[0].value if first_child.children else ""
            return ET.Element("literal", **{"class": "Integer", "value": value})
        elif first_child.data == "string":
            value = first_child.children[0].value if first_child.children else ""
            value = value[1:-1] if value.startswith(
                "'") and value.endswith("'") else value
            return ET.Element("literal", **{"class": "String", "value": value})
        elif first_child.data == "true":
            return ET.Element("literal", **{"class": "True", "value": "true"})
        elif first_child.data == "false":
            return ET.Element("literal", **{"class": "False", "value": "false"})
        elif first_child.data == "nil":
            return ET.Element("literal", **{"class": "Nil", "value": "nil"})
        elif first_child.data == "var":
            return ET.Element("var", name=first_child.children[0].value)
        elif first_child.data == "block":
            return generate_method_block(first_child, global_class_name, classes)
        elif first_child.data == "message_send":
            return generate_message_send(first_child, global_class_name, classes, var_token)

    # Pokud je uzel již "expr", nevytvářejte nový "expr"
    if expr_node.data == "expr":
        return generate_expr(expr_node.children[0], global_class_name, classes, var_token)

    expr_elem = ET.Element("expr")

    for child in expr_node.children:
        if isinstance(child, Tree):
            child_expr = generate_expr(
                child, global_class_name, classes, var_token)

            # Pokud je prvek již "expr", přímo ho použijeme
            if child_expr.tag == "expr":
                expr_elem.extend(child_expr)
            else:
                expr_elem.append(child_expr)
        else:
            expr_elem.append(ET.Element("literal", value=child.value))

    # Pokud je jediným potomkem již "expr", nevytváříme další vrstvu
    if len(expr_elem) == 1 and expr_elem[0].tag == "expr":
        return expr_elem[0]

    return expr_elem


def generate_message_send(message_send_node, class_name, classes, var_token):
    """Funkce pro vytvoření prvku XML send"""
    receiver_node = message_send_node.children[0]
    receiver_expr = generate_expr(
        receiver_node, class_name, classes, var_token)

    param_send_node = message_send_node.children[1]
    selector, arguments = extract_message_send_details(param_send_node)

    # Zpracování speciálních případů "new", "from:", "read"
    if (selector == "new") or (selector == "from:"):
        from_class = receiver_node.children[0].value
        if var_token in classes:
            del classes[var_token]
        classes[var_token] = {
            "parent": from_class, "methods": {}}
    elif (selector == "read"):
        from_class = receiver_node.children[0].value
        if (find_method_in_class(from_class, selector, classes) == None):
            sys.stderr.write(
                f"Sémantická chyba (32): selektor <{selector}> není inicializován ani ve třídě <{from_class}> ani v rodičovských třídách\n")
            sys.exit(ERR_NON_DEF)

    # Kontrola, zda selektor existuje v rodičovské třídě
    if (receiver_node.data == "super"):
        parent_class = classes[class_name]["parent"]
        if (method_exists_in_class_or_builtin(parent_class, selector, classes)):
            send_elem = ET.Element("send", selector=selector)
        else:
            sys.stderr.write(
                f"Sémantická chyba (32): selektor <{selector}> není inicializován v rodičovských třídách třídy <{class_name}>\n")
            sys.exit(ERR_NON_DEF)

    # Kontrola, zda metoda existuje v aktuální třídě nebo ve vestavěných třídách
    elif (method_exists_in_class_or_builtin(class_name, selector, classes)):
        send_elem = ET.Element("send", selector=selector)

    # Kontrola, zda metoda existuje ve třídě příjemce zprávy
    elif (receiver_node.children[0].value in classes):
        if (method_exists_in_class_or_builtin(receiver_node.children[0].value, selector, classes)):
            send_elem = ET.Element("send", selector=selector)
        else:
            sys.stderr.write(
                f"Sémantická chyba (32): selektor <{selector}> není inicializován ani ve třídě <{classes[receiver_node.children[0].value]['parent']}> ani v rodičovských třídách\n")
            sys.exit(ERR_NON_DEF)

    # Pokud je příjemcem zprávy "self"
    elif (receiver_node.data == "self"):
        send_elem = ET.Element("send", selector=selector)
    else:
        sys.stderr.write(
            f"Sémantická chyba (32): Chyba při používání neznámého selektoru <{selector}>\n")
        sys.exit(ERR_NON_DEF)

    if receiver_expr.tag != "expr":
        receiver_expr_container = ET.Element("expr")
        receiver_expr_container.append(receiver_expr)
        send_elem.append(receiver_expr_container)
    else:
        send_elem.append(receiver_expr)

    for idx, arg in enumerate(arguments, start=1):
        arg_expr = generate_expr(arg, class_name, classes, var_token)
        arg_elem = ET.Element("arg", order=str(idx))

        if arg_expr.tag == "expr":
            arg_elem.append(arg_expr)
        else:
            arg_expr_container = ET.Element("expr")
            arg_expr_container.append(arg_expr)
            arg_elem.append(arg_expr_container)

        send_elem.append(arg_elem)

    return send_elem


def extract_message_send_details(param_send_node):
    """Funkce pro získání informací o selektoru (název selektoru a jeho argumenty)"""
    selector_parts = []
    arguments = []
    current = param_send_node

    while True:
        for child in current.children:
            if isinstance(child, Token) and (child.type == "METHOD_IDENT" or child.type == "IDENT"):
                selector_parts.append(child.value)
            elif isinstance(child, Tree) and child.data == "expr":
                if child.children and isinstance(child.children[0], Tree) and child.children[0].data == "message_send":
                    message_node = child.children[0]
                    if message_node.children:
                        arguments.append(message_node.children[0])
                    if len(message_node.children) > 1:
                        nested = message_node.children[1]
                        if isinstance(nested, Tree) and nested.data == "param_send":
                            current = nested
                            break
                else:
                    if child.children:
                        arguments.append(child.children[0])
        else:
            break

    return "".join(selector_parts), arguments


def process_token(token, class_name, classes):
    """Funkce pro správné zpracování tokenu pro další použití v XML"""
    if token.type == "INTEGER":
        return ET.Element("literal", **{"class": "Integer", "value": token.value})
    elif token.type == "STRING":
        value = token.value[1:-1] if token.value.startswith(
            "'") and token.value.endswith("'") else token.value
        return ET.Element("literal", **{"class": "String", "value": value})
    elif token.type == "TRUE":
        return ET.Element("literal", **{"class": "True", "value": "true"})
    elif token.type == "FALSE":
        return ET.Element("literal", **{"class": "False", "value": "false"})
    elif token.type == "NIL":
        return ET.Element("literal", **{"class": "Nil", "value": "nil"})
    elif token.type == "SELF":
        return ET.Element("var", name="self")
    elif token.type == "SUPER":
        return ET.Element("var", name="super")
    elif token.type == "IDENT":
        return ET.Element("var", name=token.value)
    elif token.type == "CLASS_IDENT":
        return ET.Element("literal", **{"class": "class", "value": token.value})
    elif token.type == "block":
        return generate_method_block(token.value, class_name, classes)
    else:
        return ET.Element("literal", **{"class": token.type, "value": token.value})


def find_first_comment(code):
    """Funkce pro extrakci prvního komentáře v kódu"""
    comment_pattern = re.compile(r'"([^"]*)"')
    match = comment_pattern.search(code)
    if match:
        comment = match.group(1)
        comment = comment.replace("\\n", "&nbsp;")
        return comment
    return None


if __name__ == "__main__":
    check_args()
    input_code = sys.stdin.read()
    lexical_analysis(input_code)
    tree = parse_tokens(input_code)

    check_main_class(tree)
    semantic_check_variables(tree)
    semantic_check_method_arities(tree)

    classes = gather_class_info(tree)
    check_circular_inheritance(classes)
    defined_classes = set(classes.keys())
    semantic_check_class_usage(tree, defined_classes)

    xml_root = generate_xml(tree, classes)
    xml_str = ET.tostring(xml_root, encoding="utf-8").decode("utf-8")
    sys.stdout.write('<?xml version="1.0" encoding="UTF-8"?>')
    sys.stdout.write(xml_str)
