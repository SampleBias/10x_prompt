#!/usr/bin/env python
"""
Generate favicon.ico from SVG
Requires: cairosvg, Pillow
Install with: pip install cairosvg Pillow
"""

import os
from io import BytesIO
try:
    import cairosvg
    from PIL import Image
except ImportError:
    print("Please install required packages: pip install cairosvg Pillow")
    exit(1)

def svg_to_ico(svg_path, ico_path, sizes=[16, 32, 48]):
    """Convert SVG to ICO with multiple sizes"""
    if not os.path.exists(svg_path):
        print(f"Error: SVG file not found at {svg_path}")
        return False
    
    # Create a multisize ICO file
    ico_images = []
    
    for size in sizes:
        png_data = cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)
        ico_images.append(Image.open(BytesIO(png_data)))
    
    # Save as ICO
    ico_dir = os.path.dirname(ico_path)
    if not os.path.exists(ico_dir):
        os.makedirs(ico_dir)
        
    ico_images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in ico_images],
        append_images=ico_images[1:]
    )
    print(f"Generated favicon.ico at {ico_path}")
    return True

if __name__ == "__main__":
    # Paths relative to project root
    svg_path = "static/favicon.svg"
    ico_path = "static/favicon.ico"
    
    # Generate favicon.ico
    svg_to_ico(svg_path, ico_path)
    
    print("Done! Add the following to your HTML head if not already present:")
    print('<link rel="shortcut icon" href="{{ url_for(\'static\', filename=\'favicon.ico\') }}" type="image/x-icon">') 