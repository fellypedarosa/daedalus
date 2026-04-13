---
tags: [computer_science, formats, encodings, binary]
date_created: 2026-04-12
---
# Digital Formats and Encodings

The fundamental nature of data representation in computing, moving from raw bits to human-legible text and executable logic.

## The Binary Axiom
Every file, regardless of its extension, is a sequence of bits (binary). The distinction between "text" and "binary" is purely a matter of interpretation by the software (Shell, Editor, OS). See [[Hardware_Architecture]] for how bits are stored in [[Memory_Management|RAM]] and registers.
- **Text Files**: Binary data that maps to a specific character table (ASCII, Unicode).
- **Executables**: Binary data representing machine instructions (Assembly) and metadata for the OS. See [[Operating_System_Internals#The Process Lifecycle|Process Lifecycle]] and [[Programming_Languages_Ecosystem]].
- **Media Files**: Binary data following a specific structural protocol (JPEG, MP4).

## Character Encodings
The evolution of mapping bits to glyphs.
- **ASCII (American Standard Code for Information Interchange)**: 
    - 7-bit standard (128 characters). Sufficient for English but limited for global use.
- **ISO-8859 / Extended ASCII**: 8-bit variations for Latin-based languages (Português, Español).
- **Language-Specific Extensions**: 
    - **EUC-JP / Shift-JIS**: Japanese encodings. Shift-JIS was widely used due to Microsoft/ASCII Corp collaboration but introduced ambiguity when mixing with ASCII.
- **Unicode**: The modern universal standard.
    - **UTF-8**: Variable length (1 to 4 bytes). Backwards compatible with ASCII. Efficient for Western languages.
    - **UTF-16/32**: Larger fixed/variable lengths for complex character sets.

### Security: Homograph Attacks
Since different scripts can have similar-looking characters (glifs), attackers use Unicode to spoof domains.
- **Example**: A Cyrillic "а" (U+0430) looks identical to a Latin "a" (U+0061) but has a different binary representation.
- **IDN (Internationalized Domain Names)**: Browsers and registrars now implement protections against these types of typosquatting/spoofing.

## Binary Identification: Magic Numbers
The OS identifies file types primarily through headers (magic bytes) at the beginning of the file, not just extensions. This is critical for [[Linux_Internals_and_FHS|Linux Internals]] where file extensions are often optional.
| Format | Magic Bytes (Hex) | Description |
| :--- | :--- | :--- |
| **ELF** | `7F 45 4C 46` | Executable and Linking Format (Linux). |
| **PE (EXE)** | `4D 5A` | Portable Executable (Windows/DOS "MZ" header). |
| **JPEG** | `FF D8 ... FF D9` | Starts with image data, ends with EOI (End of Image). |
| **JFIF** | `4A 46 49 46` | JPEG File Interchange Format identifier. |

## Execution Mechanics
- **Assembly Mapping**: Each CPU architecture (x86-64, ARM) has a table mapping hex codes to instructions (e.g., `F3 0F 1E FA` = `endbr64`). See [[Compiler_Design]].
- **Shebang (`#!`)**: A text-based "bang" line that tells the Shell which interpreter (Python, Zsh, Node) to use for a script. See [[Shell_Mechanics]].
- **REPL (Read-Eval-Print Loop)**: Interactive shells (Python Console, IRB, Node REPL) that provide a live programming environment.

## Tools
- `file`: Identifies file type via headers.
- `xxd`: Hexadecimal viewer (displays bits as hex and ASCII columns).
- `objdump`: Disassembles binary files into assembly mnemonics.
