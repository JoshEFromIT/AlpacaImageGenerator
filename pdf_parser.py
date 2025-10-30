"""
PDF Parser - Native Python implementation using only standard library
Parses basic PDF structure including objects, pages, and content streams
"""

import re
import zlib
from io import BytesIO


class PDFObject:
    """Represents a PDF object"""
    def __init__(self, obj_num, gen_num, value):
        self.obj_num = obj_num
        self.gen_num = gen_num
        self.value = value

    def __repr__(self):
        return f"PDFObject({self.obj_num}, {self.gen_num}, {type(self.value).__name__})"


class PDFParser:
    """Parses PDF files and extracts structure"""

    def __init__(self, filename=None, data=None):
        """
        Initialize parser with either filename or data

        Args:
            filename: Path to PDF file
            data: PDF data as bytes
        """
        if filename:
            with open(filename, 'rb') as f:
                self.data = f.read()
        elif data:
            self.data = data
        else:
            raise ValueError("Must provide either filename or data")

        self.objects = {}
        self.xref = {}
        self.trailer = {}
        self.root = None

    def parse(self):
        """Parse the PDF file"""
        # Find xref table
        xref_pos = self._find_xref()
        if xref_pos == -1:
            raise ValueError("Could not find xref table")

        # Parse xref and trailer
        self._parse_xref(xref_pos)

        # Parse all objects
        for obj_num, offset in self.xref.items():
            if offset > 0:
                obj = self._parse_object_at(offset)
                if obj:
                    self.objects[obj_num] = obj

        # Get root object
        if 'Root' in self.trailer:
            root_ref = self.trailer['Root']
            self.root = self._resolve_reference(root_ref)

        return self

    def _find_xref(self):
        """Find the position of the xref table"""
        # Search for startxref from end
        match = re.search(rb'startxref\s+(\d+)', self.data[-1024:])
        if match:
            return int(match.group(1))
        return -1

    def _parse_xref(self, pos):
        """Parse cross-reference table"""
        # Read enough data for xref table (expand if needed)
        chunk_size = min(100000, len(self.data) - pos)
        data = self.data[pos:pos+chunk_size]

        # Find xref keyword
        if not data.startswith(b'xref'):
            return

        # Handle different line ending styles
        lines = data.replace(b'\r\n', b'\n').replace(b'\r', b'\n').split(b'\n')
        idx = 1

        # Parse xref entries
        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith(b'trailer'):
                break

            if not line:  # Skip empty lines
                idx += 1
                continue

            # Parse subsection header (start_num count)
            match = re.match(rb'(\d+)\s+(\d+)', line)
            if match:
                start_num = int(match.group(1))
                count = int(match.group(2))
                idx += 1

                # Parse entries
                for i in range(count):
                    if idx >= len(lines):
                        break
                    entry = lines[idx].strip()
                    if not entry:  # Skip empty lines
                        idx += 1
                        continue
                    parts = entry.split()
                    if len(parts) >= 3:
                        offset = int(parts[0])
                        gen_num = int(parts[1])
                        flag = parts[2]
                        # Only add 'n' (in-use) entries
                        if flag == b'n':
                            self.xref[start_num + i] = offset
                    idx += 1
            else:
                idx += 1

        # Parse trailer
        trailer_start = data.find(b'trailer')
        if trailer_start != -1:
            trailer_data = data[trailer_start+7:]
            self.trailer = self._parse_dictionary(trailer_data)

    def _parse_object_at(self, offset):
        """Parse object at given offset"""
        if offset >= len(self.data):
            return None

        data = self.data[offset:offset+100000]  # Read chunk

        # Match object header: "num gen obj"
        match = re.match(rb'(\d+)\s+(\d+)\s+obj', data)
        if not match:
            return None

        obj_num = int(match.group(1))
        gen_num = int(match.group(2))

        # Find object end
        obj_start = match.end()
        obj_end = data.find(b'endobj', obj_start)
        if obj_end == -1:
            obj_end = len(data)

        obj_data = data[obj_start:obj_end]

        # Parse object value
        value = self._parse_value(obj_data)

        return PDFObject(obj_num, gen_num, value)

    def _parse_value(self, data):
        """Parse a PDF value (dictionary, array, string, number, etc.)"""
        data = data.strip()

        if not data:
            return None

        # Stream (dictionary followed by stream data)
        if data.startswith(b'<<') and b'stream' in data:
            return self._parse_stream(data)

        # Dictionary
        if data.startswith(b'<<'):
            return self._parse_dictionary(data)

        # Array
        if data.startswith(b'['):
            return self._parse_array(data)

        # String
        if data.startswith(b'('):
            return self._parse_string(data)

        # Hex string
        if data.startswith(b'<') and not data.startswith(b'<<'):
            return self._parse_hex_string(data)

        # Stream
        if b'stream' in data[:100]:
            return self._parse_stream(data)

        # Reference
        match = re.match(rb'(\d+)\s+(\d+)\s+R', data)
        if match:
            return {'type': 'ref', 'num': int(match.group(1)), 'gen': int(match.group(2))}

        # Boolean
        if data.startswith(b'true'):
            return True
        if data.startswith(b'false'):
            return False

        # Null
        if data.startswith(b'null'):
            return None

        # Name
        if data.startswith(b'/'):
            return self._parse_name(data)

        # Number
        try:
            if b'.' in data[:20]:
                return float(data.split()[0])
            else:
                return int(data.split()[0])
        except:
            pass

        return data

    def _parse_dictionary(self, data):
        """Parse PDF dictionary"""
        result = {}
        data = data.strip()

        if not data.startswith(b'<<'):
            return result

        # Find matching >>
        depth = 0
        end_pos = 0
        for i, byte in enumerate(data):
            if byte == ord('<') and i + 1 < len(data) and data[i + 1] == ord('<'):
                depth += 1
            elif byte == ord('>') and i + 1 < len(data) and data[i + 1] == ord('>'):
                depth -= 1
                if depth == 0:
                    end_pos = i + 2
                    break

        if end_pos == 0:
            end_pos = len(data)

        content = data[2:end_pos-2].strip()

        # Parse key-value pairs
        pos = 0
        while pos < len(content):
            # Skip whitespace
            while pos < len(content) and content[pos:pos+1] in b' \t\r\n':
                pos += 1

            if pos >= len(content):
                break

            # Parse key (name)
            if content[pos:pos+1] != b'/':
                break

            key_match = re.match(rb'/([^\s<>\[\](){}/%]+)', content[pos:])
            if not key_match:
                break

            key = key_match.group(1).decode('latin-1')
            pos += key_match.end()

            # Skip whitespace
            while pos < len(content) and content[pos:pos+1] in b' \t\r\n':
                pos += 1

            # Parse value
            value, value_len = self._parse_value_with_length(content[pos:])
            result[key] = value
            pos += value_len

        return result

    def _parse_value_with_length(self, data):
        """Parse value and return (value, bytes_consumed)"""
        data = data.strip()

        if not data:
            return None, 0

        # Dictionary
        if data.startswith(b'<<'):
            depth = 0
            end_pos = 0
            for i in range(len(data) - 1):
                if data[i] == ord('<') and data[i + 1] == ord('<'):
                    depth += 1
                elif data[i] == ord('>') and data[i + 1] == ord('>'):
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 2
                        break
            value = self._parse_dictionary(data[:end_pos])
            return value, end_pos

        # Array
        if data.startswith(b'['):
            depth = 1
            end_pos = 1
            while end_pos < len(data) and depth > 0:
                if data[end_pos] == ord('['):
                    depth += 1
                elif data[end_pos] == ord(']'):
                    depth -= 1
                end_pos += 1
            value = self._parse_array(data[:end_pos])
            return value, end_pos

        # String
        if data.startswith(b'('):
            depth = 1
            end_pos = 1
            while end_pos < len(data) and depth > 0:
                if data[end_pos] == ord('(') and data[end_pos-1] != ord('\\'):
                    depth += 1
                elif data[end_pos] == ord(')') and data[end_pos-1] != ord('\\'):
                    depth -= 1
                end_pos += 1
            value = self._parse_string(data[:end_pos])
            return value, end_pos

        # Hex string
        if data.startswith(b'<') and not data.startswith(b'<<'):
            end_pos = data.find(b'>')
            if end_pos != -1:
                value = self._parse_hex_string(data[:end_pos + 1])
                return value, end_pos + 1

        # Reference
        match = re.match(rb'(\d+)\s+(\d+)\s+R', data)
        if match:
            value = {'type': 'ref', 'num': int(match.group(1)), 'gen': int(match.group(2))}
            return value, match.end()

        # Name
        if data.startswith(b'/'):
            match = re.match(rb'/([^\s<>\[\](){}/%]+)', data)
            if match:
                return b'/' + match.group(1), match.end()

        # Boolean/null
        if data.startswith(b'true'):
            return True, 4
        if data.startswith(b'false'):
            return False, 5
        if data.startswith(b'null'):
            return None, 4

        # Number
        match = re.match(rb'[+-]?\d+\.?\d*', data)
        if match:
            num_str = match.group(0)
            if b'.' in num_str:
                return float(num_str), len(num_str)
            else:
                return int(num_str), len(num_str)

        return None, 0

    def _parse_array(self, data):
        """Parse PDF array"""
        result = []
        data = data.strip()

        if not data.startswith(b'['):
            return result

        end_pos = data.find(b']')
        if end_pos == -1:
            end_pos = len(data)

        content = data[1:end_pos].strip()
        pos = 0

        while pos < len(content):
            # Skip whitespace
            while pos < len(content) and content[pos:pos+1] in b' \t\r\n':
                pos += 1

            if pos >= len(content):
                break

            value, value_len = self._parse_value_with_length(content[pos:])
            if value_len == 0:
                break
            result.append(value)
            pos += value_len

        return result

    def _parse_string(self, data):
        """Parse PDF string"""
        if not data.startswith(b'('):
            return b''

        end_pos = 1
        depth = 1
        while end_pos < len(data) and depth > 0:
            if data[end_pos] == ord('(') and data[end_pos - 1] != ord('\\'):
                depth += 1
            elif data[end_pos] == ord(')') and data[end_pos - 1] != ord('\\'):
                depth -= 1
            end_pos += 1

        return data[1:end_pos - 1]

    def _parse_hex_string(self, data):
        """Parse PDF hex string"""
        if not data.startswith(b'<'):
            return b''

        end_pos = data.find(b'>')
        if end_pos == -1:
            return b''

        hex_data = data[1:end_pos].replace(b' ', b'').replace(b'\n', b'').replace(b'\r', b'')
        return bytes.fromhex(hex_data.decode('ascii'))

    def _parse_name(self, data):
        """Parse PDF name"""
        match = re.match(rb'/([^\s<>\[\](){}/%]+)', data)
        if match:
            return b'/' + match.group(1)
        return b'/'

    def _parse_stream(self, data):
        """Parse PDF stream object"""
        # Split dictionary and stream data
        stream_start = data.find(b'stream')
        if stream_start == -1:
            return None

        dict_data = data[:stream_start]
        stream_dict = self._parse_dictionary(dict_data)

        # Find stream data (after 'stream' keyword and newline)
        stream_data_start = stream_start + 6
        while stream_data_start < len(data) and data[stream_data_start:stream_data_start+1] in b'\r\n':
            stream_data_start += 1

        # Find endstream
        stream_end = data.find(b'endstream')
        if stream_end == -1:
            stream_end = len(data)

        # Remove trailing newline before endstream
        while stream_end > stream_data_start and data[stream_end - 1:stream_end] in b'\r\n':
            stream_end -= 1

        stream_data = data[stream_data_start:stream_end]

        # Decompress if needed
        if isinstance(stream_dict, dict) and 'Filter' in stream_dict:
            filter_name = stream_dict['Filter']
            if filter_name == b'/FlateDecode' or filter_name == 'FlateDecode':
                try:
                    stream_data = zlib.decompress(stream_data)
                except:
                    pass  # Keep original if decompression fails

        return {'dict': stream_dict, 'data': stream_data}

    def _resolve_reference(self, ref):
        """Resolve an object reference"""
        if isinstance(ref, dict) and ref.get('type') == 'ref':
            obj_num = ref['num']
            if obj_num in self.objects:
                return self.objects[obj_num].value
        return ref

    def get_pages(self):
        """Get all pages from the PDF"""
        if not self.root:
            return []

        pages = []
        pages_ref = self.root.get('Pages')
        if pages_ref:
            pages_obj = self._resolve_reference(pages_ref)
            pages.extend(self._get_pages_recursive(pages_obj))

        return pages

    def _get_pages_recursive(self, node, visited=None):
        """Recursively get pages from page tree"""
        if visited is None:
            visited = set()

        pages = []

        if not isinstance(node, dict):
            return pages

        # Get a unique identifier for this node to prevent infinite recursion
        node_id = id(node)
        if node_id in visited:
            return pages
        visited.add(node_id)

        node_type = node.get('Type')

        # Resolve indirect reference if Type is a reference
        if isinstance(node_type, dict) and node_type.get('type') == 'ref':
            node_type = self._resolve_reference(node_type)

        # Normalize node type for comparison
        if isinstance(node_type, bytes):
            node_type = node_type.decode('latin-1', errors='ignore')

        # Normalize: remove leading slash and whitespace, case-insensitive
        if isinstance(node_type, str):
            node_type_normalized = node_type.strip().lstrip('/').lower()
        else:
            node_type_normalized = ''

        if node_type_normalized == 'pages':
            # Pages node - recurse into kids
            kids = node.get('Kids', [])
            if not kids:
                # Some PDFs might have Kids as an indirect reference
                kids_ref = node.get('Kids')
                if isinstance(kids_ref, dict) and kids_ref.get('type') == 'ref':
                    kids = self._resolve_reference(kids_ref)
                if not isinstance(kids, list):
                    kids = []

            for kid_ref in kids:
                kid = self._resolve_reference(kid_ref)
                pages.extend(self._get_pages_recursive(kid, visited))

        elif node_type_normalized == 'page':
            # Leaf page node
            pages.append(node)

        return pages

    def get_page_content(self, page):
        """Get content stream for a page"""
        contents_ref = page.get('Contents')
        if not contents_ref:
            return b''

        contents = self._resolve_reference(contents_ref)

        # Contents can be a single stream or array of streams
        if isinstance(contents, dict) and 'data' in contents:
            return contents['data']
        elif isinstance(contents, list):
            # Multiple content streams - concatenate
            result = b''
            for item in contents:
                stream = self._resolve_reference(item)
                if isinstance(stream, dict) and 'data' in stream:
                    result += stream['data'] + b'\n'
            return result

        return b''


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <pdf_file>")
        sys.exit(1)

    parser = PDFParser(sys.argv[1])
    parser.parse()

    print(f"Parsed PDF with {len(parser.objects)} objects")
    print(f"Root: {parser.root}")

    pages = parser.get_pages()
    print(f"\nFound {len(pages)} pages")

    for i, page in enumerate(pages):
        content = parser.get_page_content(page)
        print(f"\nPage {i + 1}: {len(content)} bytes of content")
        if content:
            print(f"First 200 chars: {content[:200]}")
