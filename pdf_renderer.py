"""
PDF Renderer - Native Python implementation
Renders PDF pages to raster images by interpreting content streams
"""

import re
import math


class Matrix:
    """2D transformation matrix"""

    def __init__(self, a=1, b=0, c=0, d=1, e=0, f=0):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f

    def transform_point(self, x, y):
        """Transform a point using this matrix"""
        new_x = self.a * x + self.c * y + self.e
        new_y = self.b * x + self.d * y + self.f
        return new_x, new_y

    def multiply(self, other):
        """Multiply this matrix by another"""
        return Matrix(
            self.a * other.a + self.b * other.c,
            self.a * other.b + self.b * other.d,
            self.c * other.a + self.d * other.c,
            self.c * other.b + self.d * other.d,
            self.e * other.a + self.f * other.c + other.e,
            self.e * other.b + self.f * other.d + other.f
        )

    def __repr__(self):
        return f"Matrix({self.a}, {self.b}, {self.c}, {self.d}, {self.e}, {self.f})"


class GraphicsState:
    """PDF graphics state"""

    def __init__(self):
        self.ctm = Matrix()  # Current transformation matrix
        self.stroke_color = (0, 0, 0)
        self.fill_color = (0, 0, 0)
        self.line_width = 1
        self.text_matrix = Matrix()
        self.text_line_matrix = Matrix()
        self.font_size = 12
        self.char_space = 0
        self.word_space = 0
        self.leading = 0

    def copy(self):
        """Create a copy of this state"""
        state = GraphicsState()
        state.ctm = Matrix(self.ctm.a, self.ctm.b, self.ctm.c, self.ctm.d, self.ctm.e, self.ctm.f)
        state.stroke_color = self.stroke_color
        state.fill_color = self.fill_color
        state.line_width = self.line_width
        state.text_matrix = Matrix(self.text_matrix.a, self.text_matrix.b, self.text_matrix.c,
                                   self.text_matrix.d, self.text_matrix.e, self.text_matrix.f)
        state.text_line_matrix = Matrix(self.text_line_matrix.a, self.text_line_matrix.b,
                                        self.text_line_matrix.c, self.text_line_matrix.d,
                                        self.text_line_matrix.e, self.text_line_matrix.f)
        state.font_size = self.font_size
        state.char_space = self.char_space
        state.word_space = self.word_space
        state.leading = self.leading
        return state


class PDFRenderer:
    """Renders PDF pages to raster images"""

    def __init__(self, width=595, height=842, dpi=72):
        """
        Initialize renderer

        Args:
            width: Page width in points (default: A4 width)
            height: Page height in points (default: A4 height)
            dpi: Resolution in dots per inch
        """
        self.page_width = width
        self.page_height = height
        self.dpi = dpi
        self.scale = dpi / 72.0  # PDF uses 72 points per inch

        # Image dimensions
        self.width = int(width * self.scale)
        self.height = int(height * self.scale)

        # Image buffer (RGB)
        self.image = bytearray([255, 255, 255] * self.width * self.height)

        # Graphics state
        self.state = GraphicsState()
        self.state_stack = []

        # Current path
        self.current_path = []
        self.current_point = (0, 0)

    def set_pixel(self, x, y, color):
        """Set a pixel in the image buffer"""
        x = int(x)
        y = int(y)

        if 0 <= x < self.width and 0 <= y < self.height:
            # Flip Y coordinate (PDF has origin at bottom-left)
            y = self.height - 1 - y
            idx = (y * self.width + x) * 3
            self.image[idx] = color[0]
            self.image[idx + 1] = color[1]
            self.image[idx + 2] = color[2]

    def draw_line(self, x0, y0, x1, y1, color):
        """Draw a line using Bresenham's algorithm"""
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.set_pixel(x0, y0, color)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def fill_rect(self, x, y, width, height, color):
        """Fill a rectangle"""
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)

        for dy in range(height):
            for dx in range(width):
                self.set_pixel(x + dx, y + dy, color)

    def draw_rect(self, x, y, width, height, color):
        """Draw a rectangle outline"""
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)

        # Top
        for dx in range(width):
            self.set_pixel(x + dx, y, color)
        # Bottom
        for dx in range(width):
            self.set_pixel(x + dx, y + height - 1, color)
        # Left
        for dy in range(height):
            self.set_pixel(x, y + dy, color)
        # Right
        for dy in range(height):
            self.set_pixel(x + width - 1, y + dy, color)

    def draw_text(self, text, x, y, color, size):
        """Draw text (simplified - just draws a rectangle as placeholder)"""
        # Since we don't have font rendering, we'll draw a simple representation
        # This is a placeholder - real implementation would need font parsing

        x = int(x * self.scale)
        y = int(y * self.scale)
        size = int(size * self.scale)

        char_width = size * 0.6
        char_height = size

        for i, char in enumerate(text):
            cx = x + int(i * char_width)
            # Draw a simple rectangle for each character
            self.fill_rect(cx, y, max(int(char_width * 0.8), 1), max(int(char_height), 1), color)

    def render_content_stream(self, content):
        """
        Render a PDF content stream

        Args:
            content: Content stream as bytes
        """
        if isinstance(content, str):
            content = content.encode('latin-1')

        # Tokenize the content stream
        tokens = self._tokenize(content)

        # Process operators
        operand_stack = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Check if it's an operator
            if self._is_operator(token):
                self._execute_operator(token, operand_stack)
                operand_stack = []
            else:
                # It's an operand
                operand_stack.append(token)

            i += 1

    def _tokenize(self, content):
        """Tokenize PDF content stream"""
        tokens = []

        # Handle both bytes and strings
        if isinstance(content, bytes):
            content_str = content.decode('latin-1', errors='ignore')
        else:
            content_str = content

        # Pattern to match PDF tokens
        pattern = r'(<<|>>|[\[\]{}()]|/[^\s\[\]{}()<>/%]+|[^\s\[\]{}()<>/%]+)'
        matches = re.finditer(pattern, content_str)

        for match in matches:
            token = match.group(1)
            tokens.append(token)

        return tokens

    def _is_operator(self, token):
        """Check if token is an operator"""
        # Common PDF operators (not exhaustive)
        operators = {
            # Graphics state
            'q', 'Q', 'cm', 'w', 'J', 'j', 'M', 'd', 'ri', 'i', 'gs',
            # Color
            'CS', 'cs', 'SC', 'SCN', 'sc', 'scn', 'G', 'g', 'RG', 'rg', 'K', 'k',
            # Path construction
            'm', 'l', 'c', 'v', 'y', 'h', 're',
            # Path painting
            'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n',
            # Clipping
            'W', 'W*',
            # Text
            'BT', 'ET', 'Tc', 'Tw', 'Tz', 'TL', 'Tf', 'Tr', 'Ts',
            'Td', 'TD', 'Tm', 'T*', 'Tj', 'TJ', "'", '"',
            # XObject
            'Do',
            # Marked content
            'BDC', 'BMC', 'EMC', 'MP', 'DP'
        }
        return token in operators

    def _execute_operator(self, op, operands):
        """Execute a PDF operator"""
        try:
            # Graphics state operators
            if op == 'q':
                # Save graphics state
                self.state_stack.append(self.state.copy())

            elif op == 'Q':
                # Restore graphics state
                if self.state_stack:
                    self.state = self.state_stack.pop()

            elif op == 'cm':
                # Concat matrix
                if len(operands) >= 6:
                    a, b, c, d, e, f = [self._to_number(x) for x in operands[:6]]
                    new_matrix = Matrix(a, b, c, d, e, f)
                    self.state.ctm = self.state.ctm.multiply(new_matrix)

            elif op == 'w':
                # Set line width
                if operands:
                    self.state.line_width = self._to_number(operands[0])

            # Color operators
            elif op == 'rg':
                # Set RGB fill color
                if len(operands) >= 3:
                    r = int(self._to_number(operands[0]) * 255)
                    g = int(self._to_number(operands[1]) * 255)
                    b = int(self._to_number(operands[2]) * 255)
                    self.state.fill_color = (r, g, b)

            elif op == 'RG':
                # Set RGB stroke color
                if len(operands) >= 3:
                    r = int(self._to_number(operands[0]) * 255)
                    g = int(self._to_number(operands[1]) * 255)
                    b = int(self._to_number(operands[2]) * 255)
                    self.state.stroke_color = (r, g, b)

            elif op == 'g':
                # Set gray fill color
                if operands:
                    gray = int(self._to_number(operands[0]) * 255)
                    self.state.fill_color = (gray, gray, gray)

            elif op == 'G':
                # Set gray stroke color
                if operands:
                    gray = int(self._to_number(operands[0]) * 255)
                    self.state.stroke_color = (gray, gray, gray)

            # Path construction operators
            elif op == 'm':
                # Move to
                if len(operands) >= 2:
                    x = self._to_number(operands[0]) * self.scale
                    y = self._to_number(operands[1]) * self.scale
                    x, y = self.state.ctm.transform_point(x, y)
                    self.current_point = (x, y)
                    self.current_path = [(x, y)]

            elif op == 'l':
                # Line to
                if len(operands) >= 2:
                    x = self._to_number(operands[0]) * self.scale
                    y = self._to_number(operands[1]) * self.scale
                    x, y = self.state.ctm.transform_point(x, y)
                    self.current_path.append((x, y))
                    self.current_point = (x, y)

            elif op == 're':
                # Rectangle
                if len(operands) >= 4:
                    x = self._to_number(operands[0]) * self.scale
                    y = self._to_number(operands[1]) * self.scale
                    w = self._to_number(operands[2]) * self.scale
                    h = self._to_number(operands[3]) * self.scale

                    x, y = self.state.ctm.transform_point(x, y)

                    self.current_path = [
                        (x, y),
                        (x + w, y),
                        (x + w, y + h),
                        (x, y + h),
                        (x, y)
                    ]

            elif op == 'h':
                # Close path
                if self.current_path:
                    self.current_path.append(self.current_path[0])

            # Path painting operators
            elif op == 'S':
                # Stroke path
                self._stroke_path()
                self.current_path = []

            elif op == 'f' or op == 'F':
                # Fill path
                self._fill_path()
                self.current_path = []

            elif op == 'B':
                # Fill and stroke path
                self._fill_path()
                self._stroke_path()
                self.current_path = []

            elif op == 'n':
                # End path without painting
                self.current_path = []

            # Text operators
            elif op == 'BT':
                # Begin text
                self.state.text_matrix = Matrix()
                self.state.text_line_matrix = Matrix()

            elif op == 'ET':
                # End text
                pass

            elif op == 'Tf':
                # Set font and size
                if len(operands) >= 2:
                    # operands[0] is font name, operands[1] is size
                    self.state.font_size = self._to_number(operands[1])

            elif op == 'Td':
                # Move text position
                if len(operands) >= 2:
                    tx = self._to_number(operands[0])
                    ty = self._to_number(operands[1])
                    translate = Matrix(1, 0, 0, 1, tx, ty)
                    self.state.text_line_matrix = self.state.text_line_matrix.multiply(translate)
                    self.state.text_matrix = self.state.text_line_matrix

            elif op == 'TD':
                # Move text position and set leading
                if len(operands) >= 2:
                    tx = self._to_number(operands[0])
                    ty = self._to_number(operands[1])
                    self.state.leading = -ty
                    translate = Matrix(1, 0, 0, 1, tx, ty)
                    self.state.text_line_matrix = self.state.text_line_matrix.multiply(translate)
                    self.state.text_matrix = self.state.text_line_matrix

            elif op == 'Tm':
                # Set text matrix
                if len(operands) >= 6:
                    a, b, c, d, e, f = [self._to_number(x) for x in operands[:6]]
                    self.state.text_matrix = Matrix(a, b, c, d, e, f)
                    self.state.text_line_matrix = self.state.text_matrix

            elif op == 'T*':
                # Move to start of next line
                translate = Matrix(1, 0, 0, 1, 0, self.state.leading)
                self.state.text_line_matrix = self.state.text_line_matrix.multiply(translate)
                self.state.text_matrix = self.state.text_line_matrix

            elif op == 'Tj':
                # Show text
                if operands:
                    text = self._extract_text(operands[0])
                    self._show_text(text)

            elif op == 'TJ':
                # Show text with individual glyph positioning
                if operands:
                    array = operands[0]
                    if array.startswith('['):
                        # Parse array
                        items = self._parse_array(array)
                        for item in items:
                            if isinstance(item, str) and (item.startswith('(') or item.startswith('<')):
                                text = self._extract_text(item)
                                self._show_text(text)

            elif op == "'":
                # Move to next line and show text
                translate = Matrix(1, 0, 0, 1, 0, self.state.leading)
                self.state.text_line_matrix = self.state.text_line_matrix.multiply(translate)
                self.state.text_matrix = self.state.text_line_matrix
                if operands:
                    text = self._extract_text(operands[0])
                    self._show_text(text)

            elif op == 'TL':
                # Set text leading
                if operands:
                    self.state.leading = self._to_number(operands[0])

            elif op == 'Tc':
                # Set character spacing
                if operands:
                    self.state.char_space = self._to_number(operands[0])

            elif op == 'Tw':
                # Set word spacing
                if operands:
                    self.state.word_space = self._to_number(operands[0])

        except Exception as e:
            # Silently ignore errors to continue processing
            pass

    def _stroke_path(self):
        """Stroke the current path"""
        for i in range(len(self.current_path) - 1):
            x0, y0 = self.current_path[i]
            x1, y1 = self.current_path[i + 1]
            self.draw_line(x0, y0, x1, y1, self.state.stroke_color)

    def _fill_path(self):
        """Fill the current path (simplified)"""
        if len(self.current_path) >= 3:
            # For rectangles, we can easily fill
            # For complex paths, this is simplified
            min_x = min(p[0] for p in self.current_path)
            min_y = min(p[1] for p in self.current_path)
            max_x = max(p[0] for p in self.current_path)
            max_y = max(p[1] for p in self.current_path)

            width = max_x - min_x
            height = max_y - min_y

            if width > 0 and height > 0:
                self.fill_rect(min_x, min_y, width, height, self.state.fill_color)

    def _show_text(self, text):
        """Render text at current text position"""
        x = self.state.text_matrix.e
        y = self.state.text_matrix.f

        # Transform to device space
        x, y = self.state.ctm.transform_point(x, y)

        self.draw_text(text, x / self.scale, y / self.scale,
                      self.state.fill_color, self.state.font_size)

        # Advance text position (simplified)
        char_width = len(text) * self.state.font_size * 0.6
        translate = Matrix(1, 0, 0, 1, char_width, 0)
        self.state.text_matrix = self.state.text_matrix.multiply(translate)

    def _extract_text(self, token):
        """Extract text from a PDF string token"""
        if token.startswith('('):
            # Literal string
            return token[1:-1] if token.endswith(')') else token[1:]
        elif token.startswith('<'):
            # Hex string
            hex_str = token[1:-1] if token.endswith('>') else token[1:]
            hex_str = hex_str.replace(' ', '')
            try:
                return bytes.fromhex(hex_str).decode('latin-1', errors='ignore')
            except:
                return ''
        return str(token)

    def _parse_array(self, array_str):
        """Parse a PDF array string"""
        items = []
        if not array_str.startswith('['):
            return items

        content = array_str[1:-1] if array_str.endswith(']') else array_str[1:]
        # Simple tokenization
        pattern = r'(\([^)]*\)|<[^>]*>|[^\s\[\]()]+)'
        for match in re.finditer(pattern, content):
            items.append(match.group(1))

        return items

    def _to_number(self, token):
        """Convert token to number"""
        try:
            if '.' in str(token):
                return float(token)
            else:
                return int(token)
        except:
            return 0

    def get_image_data(self):
        """Get the rendered image as bytes"""
        return bytes(self.image)


if __name__ == '__main__':
    # Test renderer
    renderer = PDFRenderer(200, 200)

    # Draw some test shapes
    renderer.fill_rect(10, 10, 50, 50, (255, 0, 0))
    renderer.draw_line(0, 0, 200, 200, (0, 255, 0))
    renderer.draw_rect(100, 100, 80, 60, (0, 0, 255))

    # Save test image
    from png_encoder import PNGEncoder
    encoder = PNGEncoder(renderer.width, renderer.height)
    encoder.save(renderer.get_image_data(), 'test_render.png')
    print(f"Created test_render.png ({renderer.width}x{renderer.height})")
