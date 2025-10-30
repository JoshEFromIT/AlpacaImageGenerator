# PDF to PNG Converter

A native Python PDF to PNG converter that uses **only the Python standard library** - no external dependencies required!

## Features

- ✅ **Zero external dependencies** - Uses only Python standard library
- ✅ **Automatic PDF conversion** - Automatically handles PDF 1.5+ formats (requires Ghostscript)
- ✅ **Multi-page PDF support** - Converts all pages in a document
- ✅ **Custom resolution** - Adjustable DPI settings
- ✅ **Native implementation** - Pure Python with native PNG encoding and PDF parsing
- ✅ **Simple CLI interface** - Easy to use command-line tool

## Components

The converter consists of four main modules:

1. **`png_encoder.py`** - Native PNG encoder using zlib compression
2. **`pdf_parser.py`** - PDF structure parser (objects, pages, content streams)
3. **`pdf_renderer.py`** - PDF content stream renderer (converts PDF to raster)
4. **`pdf_to_png.py`** - Main converter script (CLI interface)

## Installation

No installation required! Just clone the repository:

```bash
git clone <repository-url>
cd AlpacaImageGenerator
```

## Requirements

- Python 3.6 or higher
- No pip packages needed!
- **Optional**: Ghostscript (for automatic PDF 1.5+ conversion)
  - macOS: `brew install ghostscript`
  - Ubuntu: `sudo apt-get install ghostscript`
  - Windows: https://www.ghostscript.com/

## Usage

### Basic Usage

Convert a PDF to PNG:

```bash
python pdf_to_png.py input.pdf
```

This creates:
- `page.png` (for single-page PDFs)
- `page_001.png`, `page_002.png`, etc. (for multi-page PDFs)

### Custom Output Prefix

```bash
python pdf_to_png.py document.pdf output
```

Creates: `output_001.png`, `output_002.png`, etc.

### Custom Resolution

```bash
python pdf_to_png.py document.pdf --dpi 150
```

Higher DPI = higher quality (and larger file size)

### Custom Page Size

```bash
python pdf_to_png.py document.pdf --width 800 --height 1000
```

### Full Example

```bash
python pdf_to_png.py report.pdf report --dpi 150
```

### Automatic PDF Conversion

The converter **automatically detects and converts** modern PDFs (PDF 1.5+) that use compressed cross-reference streams:

```bash
# Just use it normally - conversion happens automatically!
python pdf_to_png.py modern_document.pdf output

# If PDF 1.6 is detected:
# ⚠️  PDF uses modern format (1.5+) - converting to compatible version...
# ✓ Successfully converted to compatible format
# Found 3 page(s)
# Processing page 1/3... ✓ Saved to output_1.png
```

**Requirements**: Install Ghostscript for automatic conversion:
- macOS: `brew install ghostscript`
- Ubuntu: `sudo apt-get install ghostscript`

**Without Ghostscript**: The converter will provide helpful instructions for manual conversion.

**Disable auto-conversion** (if needed):
```bash
python pdf_to_png.py document.pdf --no-auto-convert
```

## Command-Line Options

```
positional arguments:
  input                 Input PDF file
  output                Output file prefix (default: page)

optional arguments:
  -h, --help            Show help message
  --dpi DPI             Resolution in DPI (default: 72)
  --width WIDTH         Page width in points (default: auto from PDF)
  --height HEIGHT       Page height in points (default: auto from PDF)
  --no-auto-convert     Disable automatic PDF version conversion
```

## Testing Individual Modules

### Test PNG Encoder

```bash
python png_encoder.py
```

Creates `test_output.png` with a gradient pattern.

### Test PDF Parser

```bash
python pdf_parser.py sample.pdf
```

Displays PDF structure and page information.

### Test PDF Renderer

```bash
python pdf_renderer.py
```

Creates `test_render.png` with test shapes.

## Limitations

This is a **simplified implementation** using only standard library components:

### What Works Well

- ✅ Basic PDF structure parsing
- ✅ Simple text rendering (placeholder)
- ✅ Basic graphics (rectangles, lines, fills)
- ✅ Color support (RGB, grayscale)
- ✅ PNG encoding with compression
- ✅ Multi-page documents

### Known Limitations

- ⚠️ **PDF 1.5+ (xref streams)**: Modern PDFs with compressed cross-reference streams are not supported (see Troubleshooting below)
- ⚠️ **Font rendering**: Text is rendered as simplified placeholders (no actual font glyphs)
- ⚠️ **Complex graphics**: Advanced path operations are simplified
- ⚠️ **Images**: Embedded images in PDFs are not extracted/rendered
- ⚠️ **Advanced features**: No support for transparency, patterns, gradients, etc.
- ⚠️ **Compressed objects**: Limited support for some PDF compression methods

### Why These Limitations?

To avoid external dependencies:
- Real font rendering requires font file parsing (TrueType, OpenType)
- Image decoding requires JPEG/JPEG2000/CCITT decoders
- Advanced graphics require complex polygon filling algorithms

For production use, consider libraries like **pdf2image** or **PyMuPDF** which use external tools like **poppler** or **MuPDF**.

## How It Works

### 1. PDF Parsing (`pdf_parser.py`)

The parser reads the PDF binary format:

1. Locates the cross-reference (xref) table
2. Parses PDF objects (dictionaries, arrays, streams)
3. Builds the page tree
4. Extracts content streams for each page
5. Decompresses streams using zlib (FlateDecode)

### 2. Content Rendering (`pdf_renderer.py`)

The renderer interprets PDF drawing operators:

1. Tokenizes the content stream
2. Maintains graphics state (colors, transforms, etc.)
3. Executes operators (moveto, lineto, rectangle, text, etc.)
4. Rasterizes to pixel buffer

### 3. PNG Encoding (`png_encoder.py`)

The encoder creates PNG files:

1. Adds PNG signature
2. Creates IHDR chunk (image header)
3. Creates IDAT chunk (compressed image data with filtering)
4. Creates IEND chunk (end marker)
5. Calculates CRC checksums for integrity

## Architecture

```
PDF File
   ↓
[PDF Parser] → Extracts pages and content streams
   ↓
[PDF Renderer] → Interprets operators, renders to pixels
   ↓
[PNG Encoder] → Compresses and writes PNG file
   ↓
PNG Files
```

## Example Output

For a 3-page PDF:

```
$ python pdf_to_png.py document.pdf output --dpi 100

Loading PDF: document.pdf
Found 3 page(s)
Processing page 1/3... ✓ Saved to output_1.png (595x842)
Processing page 2/3... ✓ Saved to output_2.png (595x842)
Processing page 3/3... ✓ Saved to output_3.png (595x842)

Conversion complete! Generated 3 file(s):
  - output_1.png
  - output_2.png
  - output_3.png
```

## Technical Details

### PDF Operators Supported

**Graphics State**: `q`, `Q`, `cm`, `w`
**Color**: `rg`, `RG`, `g`, `G`
**Path Construction**: `m`, `l`, `re`, `h`
**Path Painting**: `S`, `f`, `F`, `B`, `n`
**Text**: `BT`, `ET`, `Tf`, `Td`, `TD`, `Tm`, `T*`, `Tj`, `TJ`, `'`, `TL`, `Tc`, `Tw`

### PNG Chunks Created

- **IHDR**: Image header (width, height, bit depth, color type)
- **IDAT**: Image data (compressed with zlib)
- **IEND**: End of file marker

## License

This project is provided as-is for educational purposes.

## Contributing

Contributions are welcome! Areas for improvement:

1. Better text rendering (basic font support)
2. Bezier curve support for path operations
3. Better polygon filling algorithms
4. Support for more PDF compression filters
5. Error handling and validation

## Troubleshooting

### "PDF uses modern format (1.5+) but Ghostscript not found"

**Problem**: Your PDF uses PDF 1.5+ format with compressed cross-reference streams. The converter detected this and wants to auto-convert, but Ghostscript isn't installed.

**Solution - Install Ghostscript** (recommended):
```bash
# macOS
brew install ghostscript

# Ubuntu/Debian
sudo apt-get install ghostscript

# Then just run the converter normally - it will auto-convert:
python pdf_to_png.py your_file.pdf output
```

**Alternative - Manual Conversion**:

If you can't install Ghostscript, convert manually:

1. **macOS Preview**: Open → File → Export as PDF → Save
2. **Online tools**: https://smallpdf.com/compress-pdf
3. **Helper script** (requires Ghostscript): `python3 convert_pdf_version.py input.pdf`

### "No pages found in PDF"

**If auto-conversion is disabled**, you'll see diagnostic information showing:
- Number of objects parsed
- Whether a root catalog was found
- Page tree structure

**Solution**: Enable auto-conversion (it's on by default) or manually convert the PDF.

**Diagnostic tool**:
```bash
python3 diagnose_pdf.py your_file.pdf
```

This will show:
- PDF version
- xref table format (traditional vs stream)
- Whether Ghostscript is available
- Detailed structure information

### "Error parsing PDF"

The PDF may use features not supported by this basic parser (encryption, linearization, etc.)

### Output images are blank

The PDF may use advanced rendering features not implemented in this basic renderer.

### Text appears as rectangles

This is expected - true font rendering requires external font libraries.

## Alternatives

For production use with full PDF support:

```bash
# Using pdf2image (requires poppler)
pip install pdf2image

# Using PyMuPDF
pip install pymupdf
```

## Credits

Implemented using only Python standard library:
- `zlib` - Compression/decompression
- `struct` - Binary data handling
- `re` - Regular expressions for parsing

No external packages required!
