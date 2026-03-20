# 🧠 SOL25 Parser (XML Generator)

A Python-based parser for the **SOL25 language** that performs **lexical, syntactic, and semantic analysis**, and generates an **XML representation** of the input program.

---

## ✨ Features

- **Lexical Analysis:** Tokenization using the `lark` parsing library  
- **Syntax Analysis:** Grammar-based parsing (LALR)  
- **Semantic Checks:**
  - Undefined variables detection  
  - Method arity validation  
  - Class inheritance validation (including circular inheritance)  
  - Reserved keyword misuse detection  
- **Object-Oriented Model Support:**
  - Classes with inheritance  
  - Methods with selectors  
  - Blocks and parameters  
- **XML Output:** Converts valid SOL25 code into structured XML  

---

## 🛠️ Technologies Used

- Python 3  
- `lark` (parser & lexer)  
- `xml.etree.ElementTree` (XML generation)  
- `re` (regular expressions)  

---

## 📁 Project Structure

| File | Description |
|------|------------|
| `parse.py` | Main script handling parsing, semantic checks, and XML generation |

---

## 🚀 Usage

### Requirements

- Python 3.x  
- Install dependencies:

```bash
pip install lark
```

---

### Running the Parser

```bash
python3 parse.py < input.sol
```

---

### Help

```bash
python3 parse.py --help
```

---

## 📥 Input

- Source code in **SOL25 language** via standard input  

---

## 📤 Output

- XML representation printed to **standard output**  
- XML header is included:

```xml
<?xml version="1.0" encoding="UTF-8"?>
```
|

---

## 🧩 Supported Language Features

- Class definitions with inheritance  
- Method selectors (unary & keyword-based)  
- Blocks with parameters  
- Message sending (Smalltalk-like syntax)  
- Literals:
  - Integer  
  - String  
  - Boolean (`true`, `false`)  
  - `nil`  
- Special keywords:
  - `self`, `super`  

---

## 🔒 Semantic Rules Enforced

- `Main` class must exist with `run` method  
- No use of undefined variables  
- No redefinition of parameters  
- No circular inheritance  
- Method selectors must match parameter count  
- Built-in classes and methods are validated  

---

## 🏗️ Built-in Classes

The parser includes predefined classes:

- `Object`
- `Integer`
- `String`
- `Block`
- `True`
- `False`
- `Nil`

Each with predefined selectors and arity.

---
