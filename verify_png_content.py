#!/usr/bin/env python3
"""
Verify PNG has actual rendered content
"""

import sys
import os


def verify_png(filename):
    """Check if PNG has non-white pixels"""
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return False

    with open(filename, 'rb') as f:
        data = f.read()

    print(f"\nAnalyzing: {filename}")
    print(f"File size: {len(data)} bytes")

    # Find IDAT chunk
    pos = 8  # Skip PNG signature

    while pos < len(data):
        if pos + 8 > len(data):
            break

        chunk_len = int.from_bytes(data[pos:pos+4], 'big')
        chunk_type = data[pos+4:pos+8]

        if chunk_type == b'IDAT':
            print(f"Found IDAT chunk: {chunk_len} bytes")

            # Decompress
            import zlib
            chunk_data = data[pos+8:pos+8+chunk_len]
            try:
                decompressed = zlib.decompress(chunk_data)
                print(f"Decompressed size: {len(decompressed)} bytes")

                # Count non-white pixels
                # Format: filter byte + RGB triplets per scanline
                non_white = 0
                black = 0
                colored = 0

                i = 0
                scanlines_checked = 0

                while i < len(decompressed) and scanlines_checked < 100:
                    # Skip filter byte
                    i += 1
                    scanlines_checked += 1

                    # Check ~100 pixels per scanline (don't check entire width)
                    for _ in range(min(100, (len(decompressed) - i) // 3)):
                        if i + 2 < len(decompressed):
                            r, g, b = decompressed[i], decompressed[i+1], decompressed[i+2]
                            if r != 255 or g != 255 or b != 255:
                                non_white += 1
                                if r == 0 and g == 0 and b == 0:
                                    black += 1
                                else:
                                    colored += 1
                            i += 3
                        else:
                            break

                    # Skip rest of scanline
                    remaining = (len(decompressed) - i) % (595 * 3)  # Assuming 595px width
                    i += remaining

                print(f"\nPixel analysis (first 100 scanlines):")
                print(f"  Non-white pixels: {non_white}")
                print(f"  Black pixels: {black}")
                print(f"  Colored pixels: {colored}")

                if non_white > 100:
                    print(f"  ✅ PNG has visible content!")
                    return True
                else:
                    print(f"  ❌ PNG appears blank (all white)")
                    return False

            except Exception as e:
                print(f"Error decompressing: {e}")
                return False

        pos += 12 + chunk_len

    print("❌ No IDAT chunk found")
    return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_png_content.py <png_file> [png_file2 ...]")
        sys.exit(1)

    all_good = True
    for filename in sys.argv[1:]:
        result = verify_png(filename)
        if not result:
            all_good = False

    print()
    if all_good:
        print("✅ All PNGs have content!")
    else:
        print("❌ Some PNGs are blank - needs investigation")

    sys.exit(0 if all_good else 1)
