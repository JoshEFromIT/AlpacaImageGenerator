"""
PNG Encoder - Native Python implementation using only standard library
Implements PNG file format specification with zlib compression
"""

import zlib
import struct


class PNGEncoder:
    """Encodes image data into PNG format"""

    PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

    def __init__(self, width, height, bit_depth=8, color_type=2):
        """
        Initialize PNG encoder

        Args:
            width: Image width in pixels
            height: Image height in pixels
            bit_depth: Bits per sample (default 8)
            color_type: 0=grayscale, 2=RGB, 6=RGBA (default 2)
        """
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.color_type = color_type

    def _create_chunk(self, chunk_type, data):
        """Create a PNG chunk with length, type, data, and CRC"""
        chunk_data = chunk_type + data
        crc = zlib.crc32(chunk_data) & 0xffffffff
        return struct.pack('>I', len(data)) + chunk_data + struct.pack('>I', crc)

    def _create_ihdr(self):
        """Create IHDR (header) chunk"""
        data = struct.pack('>IIBBBBB',
                          self.width,
                          self.height,
                          self.bit_depth,
                          self.color_type,
                          0,  # compression method
                          0,  # filter method
                          0)  # interlace method
        return self._create_chunk(b'IHDR', data)

    def _create_idat(self, image_data):
        """Create IDAT (image data) chunk with filtering and compression"""
        # Add filter byte (0 = None) to each scanline
        scanline_width = self.width * self._bytes_per_pixel()
        filtered_data = bytearray()

        for y in range(self.height):
            filtered_data.append(0)  # Filter type 0 (None)
            start = y * scanline_width
            end = start + scanline_width
            filtered_data.extend(image_data[start:end])

        # Compress with zlib
        compressed = zlib.compress(bytes(filtered_data), 9)
        return self._create_chunk(b'IDAT', compressed)

    def _create_iend(self):
        """Create IEND (end) chunk"""
        return self._create_chunk(b'IEND', b'')

    def _bytes_per_pixel(self):
        """Calculate bytes per pixel based on color type"""
        if self.color_type == 0:  # Grayscale
            return 1
        elif self.color_type == 2:  # RGB
            return 3
        elif self.color_type == 6:  # RGBA
            return 4
        return 3

    def encode(self, image_data):
        """
        Encode image data to PNG format

        Args:
            image_data: Raw pixel data as bytes (RGB or RGBA)

        Returns:
            PNG file as bytes
        """
        png_data = bytearray()
        png_data.extend(self.PNG_SIGNATURE)
        png_data.extend(self._create_ihdr())
        png_data.extend(self._create_idat(image_data))
        png_data.extend(self._create_iend())

        return bytes(png_data)

    def save(self, image_data, filename):
        """
        Encode and save image data to PNG file

        Args:
            image_data: Raw pixel data as bytes
            filename: Output filename
        """
        png_bytes = self.encode(image_data)
        with open(filename, 'wb') as f:
            f.write(png_bytes)


def create_test_image():
    """Create a simple test image (gradient)"""
    width, height = 400, 300
    image_data = bytearray()

    for y in range(height):
        for x in range(width):
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = 128
            image_data.extend([r, g, b])

    return bytes(image_data), width, height


if __name__ == '__main__':
    # Test the encoder
    print("Testing PNG encoder...")
    image_data, width, height = create_test_image()
    encoder = PNGEncoder(width, height, color_type=2)
    encoder.save(image_data, 'test_output.png')
    print(f"Created test_output.png ({width}x{height})")
