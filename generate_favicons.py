#!/usr/bin/env python3
"""
Generate all required favicon files from SVG source.
Requires: pip install Pillow cairosvg
"""

import io
from pathlib import Path
from PIL import Image
import cairosvg

# File paths
SCRIPT_DIR = Path(__file__).parent
STATIC_DIR = SCRIPT_DIR / "static"
SVG_PATH = STATIC_DIR / "favicon.svg"

# Sizes to generate
SIZES = {
    "favicon-16x16.png": 16,
    "favicon-32x32.png": 32,
    "favicon-48x48.png": 48,
    "apple-touch-icon.png": 180,
    "icon-192.png": 192,
    "icon-512.png": 512,
}

def svg_to_png(svg_path: Path, output_path: Path, size: int):
    """Convert SVG to PNG at specified size."""
    png_data = cairosvg.svg2png(
        url=str(svg_path),
        output_width=size,
        output_height=size,
    )
    
    with open(output_path, "wb") as f:
        f.write(png_data)
    
    print(f"✓ Created {output_path.name} ({size}x{size})")

def create_ico(png_paths: list, output_path: Path):
    """Create multi-size .ico file from PNG files."""
    images = []
    for png_path in png_paths:
        img = Image.open(png_path)
        images.append(img)
    
    # Save as .ico with multiple sizes
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(img.width, img.height) for img in images]
    )
    
    print(f"✓ Created {output_path.name} (multi-size)")

def main():
    print("🎨 Generating favicon files from SVG...\n")
    
    if not SVG_PATH.exists():
        print(f"❌ SVG file not found: {SVG_PATH}")
        return
    
    # Generate PNG files
    png_paths = []
    for filename, size in SIZES.items():
        output_path = STATIC_DIR / filename
        svg_to_png(SVG_PATH, output_path, size)
        
        # Track 16, 32, 48 for .ico
        if size in [16, 32, 48]:
            png_paths.append(output_path)
    
    # Create multi-size .ico
    print()
    ico_path = STATIC_DIR / "favicon.ico"
    create_ico(png_paths, ico_path)
    
    print("\n✅ All favicon files generated successfully!")
    print(f"\nFiles created in: {STATIC_DIR}")

if __name__ == "__main__":
    main()
