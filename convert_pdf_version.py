#!/usr/bin/env python3
"""
Convert PDF to older version (1.4) for compatibility
Uses Ghostscript if available, otherwise provides instructions
"""

import sys
import os
import subprocess


def check_ghostscript():
    """Check if Ghostscript is installed"""
    try:
        result = subprocess.run(['gs', '--version'], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False


def convert_pdf(input_file, output_file=None):
    """Convert PDF to version 1.4 using Ghostscript"""
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        return False

    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_v1.4{ext}"

    if not check_ghostscript():
        print("❌ Ghostscript not found!")
        print("\nGhostscript is required to convert PDF versions.")
        print("\nInstall instructions:")
        print("  macOS:   brew install ghostscript")
        print("  Ubuntu:  sudo apt-get install ghostscript")
        print("  Windows: Download from https://www.ghostscript.com/")
        print("\nAlternatively, try online conversion:")
        print("  - https://smallpdf.com/compress-pdf")
        print("  - Adobe Acrobat: File → Save As → Reduced Size PDF")
        print("  - Preview (macOS): Export → Reduce File Size")
        return False

    print(f"Converting {input_file} to PDF 1.4 format...")
    print(f"Output: {output_file}")

    cmd = [
        'gs',
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        '-dNOPAUSE',
        '-dBATCH',
        '-dQUIET',
        f'-sOutputFile={output_file}',
        input_file
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Successfully converted to {output_file}")
            print(f"\nNow try: python3 pdf_to_png.py {output_file}")
            return True
        else:
            print(f"❌ Ghostscript error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python convert_pdf_version.py <input.pdf> [output.pdf]")
        print("\nConverts PDF to version 1.4 for compatibility with the converter.")
        print("Requires Ghostscript to be installed.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    success = convert_pdf(input_file, output_file)
    sys.exit(0 if success else 1)
