#!/usr/bin/env python3
"""
PDF Diagnostic Tool
Analyzes PDF structure to help debug parsing issues
"""

import sys
import re
from pdf_parser import PDFParser


def diagnose_pdf(filename):
    """Run comprehensive diagnostics on a PDF file"""
    print(f"=== Diagnosing: {filename} ===\n")

    try:
        # Read raw PDF
        with open(filename, 'rb') as f:
            data = f.read()

        print(f"File size: {len(data)} bytes")
        print(f"PDF version: {data[:8].decode('latin-1', errors='ignore')}")
        print()

        # Find startxref position
        startxref_match = re.search(rb'startxref\s+(\d+)', data[-1024:])
        if startxref_match:
            xref_pos = int(startxref_match.group(1))
            print(f"startxref position: {xref_pos}")

            # Check what's at that position
            xref_data = data[xref_pos:xref_pos+50]
            print(f"Data at xref position: {xref_data[:40]}")

            if xref_data.startswith(b'xref'):
                print("✓ Uses traditional xref table")
            elif re.match(rb'\d+\s+\d+\s+obj', xref_data):
                print("⚠️  Uses xref stream (PDF 1.5+) - NOT SUPPORTED YET")
                print("   This is a compressed cross-reference format.")
            else:
                print("❌ Unknown xref format")
        else:
            print("❌ No startxref found")

        print()

        # Check for linearization
        if b'/Linearized' in data[:1024]:
            print("⚠️  PDF is linearized (optimized for web)")

        # Check for encryption
        if b'/Encrypt' in data:
            print("⚠️  PDF appears to be encrypted")

        # Check for xref stream markers
        if b'/XRef' in data or b'/Type/XRef' in data:
            print("⚠️  PDF contains xref stream markers (PDF 1.5+)")

        print()

        # Try to parse
        print("Attempting to parse...")
        parser = PDFParser(filename)
        parser.parse()

        print(f"✓ Parsed {len(parser.objects)} objects")
        print(f"✓ Found xref table with {len(parser.xref)} entries")
        print()

        # Check root
        print("Root catalog:")
        if parser.root:
            print(f"  Type: {parser.root.get('Type')}")
            print(f"  Keys: {list(parser.root.keys())}")

            pages_ref = parser.root.get('Pages')
            print(f"  Pages reference: {pages_ref}")

            if pages_ref:
                pages_obj = parser._resolve_reference(pages_ref)
                print(f"\nPages object:")
                print(f"  Type: {type(pages_obj)}")
                if isinstance(pages_obj, dict):
                    print(f"  Type field: {pages_obj.get('Type')}")
                    print(f"  Count field: {pages_obj.get('Count')}")
                    print(f"  Kids field: {pages_obj.get('Kids')}")

                    # Try to get pages
                    print(f"\nAttempting to extract pages...")
                    pages = parser.get_pages()
                    print(f"  Result: Found {len(pages)} pages")

                    if len(pages) == 0:
                        print(f"\n❌ ERROR: No pages found!")
                        print(f"\nDebug info:")
                        print(f"  Pages obj type check:")
                        node_type = pages_obj.get('Type')
                        print(f"    Raw type value: {repr(node_type)}")
                        print(f"    Type of type: {type(node_type)}")
                        if isinstance(node_type, bytes):
                            decoded = node_type.decode('latin-1', errors='ignore')
                            print(f"    Decoded: '{decoded}'")
                            print(f"    Match '/Pages': {decoded == '/Pages'}")
                            print(f"    Match 'Pages': {decoded == 'Pages'}")
                    else:
                        print(f"  ✓ Successfully extracted pages!")
                        for i, page in enumerate(pages[:3], 1):  # Show first 3
                            print(f"\n  Page {i}:")
                            print(f"    Type: {page.get('Type')}")
                            print(f"    MediaBox: {page.get('MediaBox')}")
                            print(f"    Has Contents: {'Contents' in page}")
                else:
                    print(f"  ❌ Pages object is not a dictionary!")
            else:
                print(f"  ❌ No Pages reference found in root!")
        else:
            print("  ❌ No root catalog found!")

        print()

        # Show object types
        print("Object type summary:")
        type_counts = {}
        for obj_num, obj in parser.objects.items():
            if isinstance(obj.value, dict):
                obj_type = obj.value.get('Type', 'Unknown')
                if isinstance(obj_type, bytes):
                    obj_type = obj_type.decode('latin-1', errors='ignore')
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

        for obj_type, count in sorted(type_counts.items()):
            print(f"  {obj_type}: {count}")

    except Exception as e:
        print(f"\n❌ ERROR during parsing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_pdf.py <pdf_file>")
        print("\nThis tool analyzes PDF structure to help debug parsing issues.")
        sys.exit(1)

    for filename in sys.argv[1:]:
        diagnose_pdf(filename)
        print("\n" + "="*60 + "\n")
