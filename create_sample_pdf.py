#!/usr/bin/env python3
"""
Sample PDF Generator
Creates simple test PDFs using only Python standard library

Usage:
    python create_sample_pdf.py [filename] [--pages N]
"""

import zlib
import argparse


class SimplePDFWriter:
    """Creates basic PDF files"""

    def __init__(self):
        self.objects = [None, None, None]  # Reserve 0 (unused), 1 (catalog), 2 (pages)
        self.pages = []

    def add_object(self, content):
        """Add an object to the PDF"""
        self.objects.append(content)
        obj_num = len(self.objects) - 1
        return obj_num

    def create_page(self, width=595, height=842, content_stream=''):
        """
        Create a page

        Args:
            width: Page width in points (default: A4 width = 595)
            height: Page height in points (default: A4 height = 842)
            content_stream: PDF content stream commands
        """
        # Create content stream object
        compressed_content = zlib.compress(content_stream.encode('latin-1'))

        content_obj = f"""<<
  /Length {len(compressed_content)}
  /Filter /FlateDecode
>>
stream
{compressed_content.decode('latin-1', errors='ignore')}
endstream"""

        content_num = self.add_object(content_obj)

        # Create page object
        page_obj = f"""<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 {width} {height}]
  /Contents {content_num} 0 R
  /Resources <<
    /Font <<
      /F1 <<
        /Type /Font
        /Subtype /Type1
        /BaseFont /Helvetica
      >>
    >>
  >>
>>"""

        page_num = self.add_object(page_obj)
        self.pages.append(page_num)

        return page_num

    def generate(self):
        """Generate the complete PDF"""
        # Create pages object (object 2)
        pages_refs = ' '.join(f'{p} 0 R' for p in self.pages)
        pages_obj = f"""<<
  /Type /Pages
  /Kids [{pages_refs}]
  /Count {len(self.pages)}
>>"""
        self.objects[2] = pages_obj

        # Create catalog object (object 1)
        catalog_obj = """<<
  /Type /Catalog
  /Pages 2 0 R
>>"""
        self.objects[1] = catalog_obj

        # Build PDF
        pdf = [b'%PDF-1.4\n']

        # Track object offsets for xref table
        offsets = [0]  # Object 0 is always free

        # Write objects (skip object 0 which is None)
        for i in range(1, len(self.objects)):
            obj_content = self.objects[i]
            if obj_content is not None:
                offsets.append(len(b''.join(pdf)))
                obj_bytes = f'{i} 0 obj\n{obj_content}\nendobj\n'.encode('latin-1')
                pdf.append(obj_bytes)
            else:
                offsets.append(0)  # Free object

        # xref table position
        xref_pos = len(b''.join(pdf))

        # Create xref table
        xref = f'xref\n0 {len(offsets)}\n'
        xref += '0000000000 65535 f \n'  # Object 0

        for offset in offsets[1:]:
            if offset == 0:
                xref += '0000000000 00000 f \n'  # Free object
            else:
                xref += f'{offset:010d} 00000 n \n'

        pdf.append(xref.encode('latin-1'))

        # Trailer
        trailer = f"""trailer
<<
  /Size {len(offsets)}
  /Root 1 0 R
>>
startxref
{xref_pos}
%%EOF
"""
        pdf.append(trailer.encode('latin-1'))

        return b''.join(pdf)

    def save(self, filename):
        """Save PDF to file"""
        pdf_data = self.generate()
        with open(filename, 'wb') as f:
            f.write(pdf_data)


def create_sample_single_page():
    """Create a simple single-page PDF"""
    pdf = SimplePDFWriter()

    # Create content with shapes and text
    content = """
% Draw a red rectangle
1 0 0 rg
50 700 100 80 re
f

% Draw a blue rectangle
0 0 1 rg
200 700 100 80 re
f

% Draw a green line
0 1 0 RG
5 w
50 600 m
500 600 l
S

% Draw some text placeholders (will appear as rectangles in our renderer)
0 0 0 rg
BT
/F1 24 Tf
50 500 Td
(Hello from PDF!) Tj
ET

BT
/F1 16 Tf
50 450 Td
(This is a test PDF) Tj
ET

% Draw a rectangle outline
0 0 0 RG
2 w
50 300 200 100 re
S

% Fill a rectangle with gray
0.5 g
300 300 150 100 re
f
"""

    pdf.create_page(content_stream=content)
    return pdf


def create_sample_multi_page(num_pages=3):
    """Create a multi-page PDF"""
    pdf = SimplePDFWriter()

    for page_num in range(1, num_pages + 1):
        content = f"""
% Page {page_num} header
0 0 0 rg
BT
/F1 32 Tf
50 750 Td
(Page {page_num}) Tj
ET

% Draw colored rectangles
{(page_num % 3) / 3} 0 {1 - (page_num % 3) / 3} rg
50 600 150 100 re
f

{1 - (page_num % 3) / 3} {(page_num % 3) / 3} 0 rg
250 600 150 100 re
f

% Draw a border
0 0 0 RG
3 w
30 30 535 782 re
S

% Add page number at bottom
BT
/F1 14 Tf
250 30 Td
(Page {page_num} of {num_pages}) Tj
ET

% Draw some diagonal lines
0.7 g
1 w
{50 + page_num * 30} 400 m
{200 + page_num * 30} 500 l
S

{100 + page_num * 30} 400 m
{250 + page_num * 30} 500 l
S
"""

        pdf.create_page(content_stream=content)

    return pdf


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Create sample PDF files for testing the converter'
    )

    parser.add_argument('filename', nargs='?', default='sample.pdf',
                       help='Output PDF filename (default: sample.pdf)')
    parser.add_argument('--pages', type=int, default=1,
                       help='Number of pages (default: 1)')

    args = parser.parse_args()

    if args.pages == 1:
        print(f"Creating single-page PDF: {args.filename}")
        pdf = create_sample_single_page()
    else:
        print(f"Creating {args.pages}-page PDF: {args.filename}")
        pdf = create_sample_multi_page(args.pages)

    pdf.save(args.filename)
    print(f"✓ Created {args.filename}")
    print(f"\nTest the converter with:")
    print(f"  python pdf_to_png.py {args.filename}")


if __name__ == '__main__':
    main()
