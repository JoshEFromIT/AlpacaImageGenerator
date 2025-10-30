#!/usr/bin/env python3
"""
PDF to PNG Converter
Converts multi-page PDF documents to PNG images using only Python standard library

Usage:
    python pdf_to_png.py input.pdf [output_prefix] [--dpi DPI] [--width WIDTH] [--height HEIGHT]

Examples:
    python pdf_to_png.py document.pdf
    python pdf_to_png.py document.pdf output --dpi 150
    python pdf_to_png.py document.pdf page --width 800 --height 1000
"""

import sys
import os
import argparse
import subprocess
import tempfile
import re
from pdf_parser import PDFParser
from pdf_renderer import PDFRenderer
from png_encoder import PNGEncoder


class PDFToPNGConverter:
    """Converts PDF files to PNG images"""

    def __init__(self, dpi=72, width=None, height=None, auto_convert=True):
        """
        Initialize converter

        Args:
            dpi: Resolution in dots per inch (default 72)
            width: Override page width in points (default: use PDF page size)
            height: Override page height in points (default: use PDF page size)
            auto_convert: Automatically convert PDF 1.5+ to 1.4 if needed (default True)
        """
        self.dpi = dpi
        self.default_width = width or 595  # A4 width
        self.default_height = height or 842  # A4 height
        self.auto_convert = auto_convert
        self.temp_files = []  # Track temp files for cleanup

    def __del__(self):
        """Cleanup temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

    def _check_ghostscript(self):
        """Check if Ghostscript is installed"""
        try:
            result = subprocess.run(['gs', '--version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    def _needs_conversion(self, pdf_path):
        """Check if PDF needs conversion (uses xref streams)"""
        try:
            with open(pdf_path, 'rb') as f:
                data = f.read(min(1024, os.path.getsize(pdf_path)))
                # Check PDF version
                version_match = re.match(rb'%PDF-(\d+\.\d+)', data)
                if version_match:
                    version = float(version_match.group(1))
                    if version >= 1.5:
                        # Likely uses xref streams
                        return True

            # Also check by looking at xref position
            with open(pdf_path, 'rb') as f:
                data = f.read()
                # Find startxref
                match = re.search(rb'startxref\s+(\d+)', data[-1024:])
                if match:
                    xref_pos = int(match.group(1))
                    if xref_pos < len(data):
                        xref_data = data[xref_pos:xref_pos+20]
                        # If doesn't start with 'xref', it's likely a stream
                        if not xref_data.startswith(b'xref'):
                            return True

            return False
        except:
            return False

    def _convert_pdf_version(self, input_path):
        """Convert PDF to version 1.4 using Ghostscript"""
        # Create temp file for converted PDF
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='converted_')
        os.close(temp_fd)
        self.temp_files.append(temp_path)

        print(f"⚠️  PDF uses modern format (1.5+) - converting to compatible version...")

        cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dNOPAUSE',
            '-dBATCH',
            '-dQUIET',
            f'-sOutputFile={temp_path}',
            input_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"✓ Successfully converted to compatible format")
                return temp_path
            else:
                print(f"✗ Conversion failed: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print(f"✗ Conversion timed out")
            return None
        except Exception as e:
            print(f"✗ Conversion error: {e}")
            return None

    def convert(self, pdf_path, output_prefix='page'):
        """
        Convert PDF to PNG images

        Args:
            pdf_path: Path to input PDF file
            output_prefix: Prefix for output PNG files

        Returns:
            List of output file paths
        """
        print(f"Loading PDF: {pdf_path}")

        # Check if PDF needs conversion and auto-convert if enabled
        original_path = pdf_path
        converted = False

        if self.auto_convert and self._needs_conversion(pdf_path):
            if self._check_ghostscript():
                converted_path = self._convert_pdf_version(pdf_path)
                if converted_path:
                    pdf_path = converted_path
                    converted = True
                else:
                    print("\n❌ Automatic conversion failed!")
                    print("   Manual conversion options:")
                    print("   1. Install/update Ghostscript: brew install ghostscript")
                    print("   2. Use Preview: Open → Export as PDF")
                    print("   3. Run: python3 convert_pdf_version.py", original_path)
                    return []
            else:
                print("\n⚠️  PDF uses modern format (1.5+) but Ghostscript not found!")
                print("   Please install Ghostscript to enable automatic conversion:")
                print("   macOS:   brew install ghostscript")
                print("   Ubuntu:  sudo apt-get install ghostscript")
                print("   Windows: https://www.ghostscript.com/")
                print("\n   Or manually convert using:")
                print("   - Preview (macOS): Open → Export as PDF")
                print("   - Online: https://smallpdf.com/compress-pdf")
                return []

        # Parse PDF
        try:
            parser = PDFParser(pdf_path)
            parser.parse()
        except Exception as e:
            error_msg = str(e)
            if "cross-reference streams" in error_msg or "xref" in error_msg.lower():
                print(f"Error: {e}")
                if not converted:
                    print("\n💡 Tip: This PDF uses a format not supported yet.")
                    print("   Install Ghostscript for automatic conversion:")
                    print("   brew install ghostscript")
            else:
                print(f"Error parsing PDF: {e}")
            return []

        # Get pages
        pages = parser.get_pages()
        num_pages = len(pages)

        if num_pages == 0:
            print("No pages found in PDF")
            print("\nDiagnostic information:")
            print(f"  - Parsed {len(parser.objects)} objects")
            print(f"  - Root catalog: {parser.root is not None}")
            if parser.root:
                print(f"  - Root type: {parser.root.get('Type')}")
                pages_ref = parser.root.get('Pages')
                print(f"  - Pages reference: {pages_ref}")
                if pages_ref:
                    pages_obj = parser._resolve_reference(pages_ref)
                    print(f"  - Pages object type: {type(pages_obj)}")
                    if isinstance(pages_obj, dict):
                        print(f"  - Pages Type field: {pages_obj.get('Type')}")
                        print(f"  - Pages Count: {pages_obj.get('Count')}")
                        print(f"  - Pages Kids: {pages_obj.get('Kids')}")
            print("\nTry running: python3 diagnose_pdf.py your_file.pdf")
            print("This will provide detailed diagnostics to help fix the issue.")
            return []

        print(f"Found {num_pages} page(s)")

        output_files = []

        # Convert each page
        for page_num, page in enumerate(pages, 1):
            print(f"Processing page {page_num}/{num_pages}...", end=' ')

            try:
                # Get page size
                width, height = self._get_page_size(page)

                # Create renderer
                renderer = PDFRenderer(width, height, self.dpi)

                # Get page content
                content = parser.get_page_content(page)

                # Render content
                if content:
                    renderer.render_content_stream(content)
                else:
                    print("(blank page)", end=' ')

                # Generate output filename
                if num_pages == 1:
                    output_file = f"{output_prefix}.png"
                else:
                    # Use zero-padded page numbers
                    padding = len(str(num_pages))
                    output_file = f"{output_prefix}_{page_num:0{padding}d}.png"

                # Save as PNG
                encoder = PNGEncoder(renderer.width, renderer.height, color_type=2)
                encoder.save(renderer.get_image_data(), output_file)

                output_files.append(output_file)
                print(f"✓ Saved to {output_file} ({renderer.width}x{renderer.height})")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        return output_files

    def _get_page_size(self, page):
        """
        Get page size from page dictionary

        Args:
            page: Page dictionary from PDF

        Returns:
            Tuple of (width, height) in points
        """
        # Try to get MediaBox
        media_box = page.get('MediaBox')

        if media_box:
            # MediaBox is an array [x0, y0, x1, y1]
            if isinstance(media_box, list) and len(media_box) >= 4:
                try:
                    x0 = self._to_number(media_box[0])
                    y0 = self._to_number(media_box[1])
                    x1 = self._to_number(media_box[2])
                    y1 = self._to_number(media_box[3])
                    width = abs(x1 - x0)
                    height = abs(y1 - y0)
                    return width, height
                except:
                    pass

        # Default to A4 size
        return self.default_width, self.default_height

    def _to_number(self, value):
        """Convert value to number"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(value)
        except:
            return 0.0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Convert PDF to PNG images using only Python standard library',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.pdf
  %(prog)s document.pdf output --dpi 150
  %(prog)s document.pdf page --width 800 --height 1000

Output:
  For single page PDFs: <prefix>.png
  For multi-page PDFs: <prefix>_001.png, <prefix>_002.png, etc.
        """
    )

    parser.add_argument('input', help='Input PDF file')
    parser.add_argument('output', nargs='?', default='page',
                       help='Output file prefix (default: page)')
    parser.add_argument('--dpi', type=int, default=72,
                       help='Resolution in DPI (default: 72)')
    parser.add_argument('--width', type=int,
                       help='Page width in points (default: auto from PDF)')
    parser.add_argument('--height', type=int,
                       help='Page height in points (default: auto from PDF)')
    parser.add_argument('--no-auto-convert', action='store_true',
                       help='Disable automatic PDF version conversion (requires Ghostscript)')

    args = parser.parse_args()

    # Check input file exists
    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}")
        return 1

    # Create converter
    converter = PDFToPNGConverter(
        dpi=args.dpi,
        width=args.width,
        height=args.height,
        auto_convert=not args.no_auto_convert
    )

    # Convert
    output_files = converter.convert(args.input, args.output)

    if output_files:
        print(f"\nConversion complete! Generated {len(output_files)} file(s):")
        for f in output_files:
            print(f"  - {f}")
        return 0
    else:
        print("\nConversion failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
