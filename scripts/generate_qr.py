#!/usr/bin/env python3
"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
QR Code Generation Script

Generates QR codes for all Vyas rooms that link to the report page.
QR codes are saved as PNG files in the qr_codes/ directory.

Usage:
    python scripts/generate_qr.py --all          # Generate QR codes for all rooms
    python scripts/generate_qr.py --floor 4      # Generate QR codes for 4th floor
    python scripts/generate_qr.py --room VY404   # Generate QR code for specific room
"""
import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import qrcode
from PIL import Image, ImageDraw, ImageFont
from app import create_app, db
from app.models import Building, Floor, Room


# Configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000
QR_CODE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'qr_codes')


def ensure_qr_directory():
    """Ensure QR code directory exists."""
    if not os.path.exists(QR_CODE_DIR):
        os.makedirs(QR_CODE_DIR)
        print(f"📁 Created directory: {QR_CODE_DIR}")


def generate_qr_code(room, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """
    Generate a QR code for a room.
    
    Args:
        room: Room model instance
        host: Server hostname
        port: Server port
    
    Returns:
        PIL Image object
    """
    # Generate URL
    room_number = room.number
    url = f"http://{host}:{port}/report?room={room_number}"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Generate image
    img = qr.make_image(fill_color="#0b4d8c", back_color="white")
    
    # Add text label at the bottom
    width, height = img.size
    new_height = height + 70
    new_img = Image.new('RGB', (width, new_height), 'white')
    new_img.paste(img, (0, 0))
    
    # Add text
    draw = ImageDraw.Draw(new_img)
    
    # Try to use a nice font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Room label
    room_label = f"Vyas {room_number}"
    bbox = draw.textbbox((0, 0), room_label, font=font_large)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, height + 10), room_label, fill="#0b4d8c", font=font_large)
    
    # Floor label
    floor_label = room.floor.name if room.floor else ""
    bbox = draw.textbbox((0, 0), floor_label, font=font_small)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, height + 38), floor_label, fill="#6c757d", font=font_small)
    
    # URL label
    url_label = "Scan to report issue"
    bbox = draw.textbbox((0, 0), url_label, font=font_small)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    draw.text((x, height + 55), url_label, fill="#20c997", font=font_small)
    
    return new_img


def save_qr_code(room, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """
    Generate and save QR code for a room.
    
    Returns:
        Path to saved file
    """
    img = generate_qr_code(room, host, port)
    
    # Generate filename
    filename = f"Vyas_{room.number}_QR.png"
    filepath = os.path.join(QR_CODE_DIR, filename)
    
    # Save image
    img.save(filepath, 'PNG')
    
    return filepath


def generate_all_qr_codes(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Generate QR codes for all Vyas rooms."""
    app = create_app()
    
    with app.app_context():
        ensure_qr_directory()
        
        # Get Vyas building
        vyas = Building.query.filter_by(name='Vyas').first()
        if not vyas:
            print("❌ Error: Vyas building not found. Run init_data.py first.")
            return []
        
        rooms = Room.query.join(Floor).filter(Floor.building_id == vyas.id).all()
        
        print("=" * 60)
        print("MIT-WPU Vyas Tracker - QR Code Generation")
        print("=" * 60)
        print(f"\n🌐 Server URL: http://{host}:{port}")
        print(f"📁 Output Directory: {QR_CODE_DIR}")
        print(f"\n🔄 Generating QR codes for {len(rooms)} rooms...\n")
        
        generated_files = []
        
        for room in rooms:
            filepath = save_qr_code(room, host, port)
            generated_files.append(filepath)
            url = f"http://{host}:{port}/report?room={room.number}"
            print(f"  ✅ {room.number} ({room.floor.name})")
            print(f"     File: {os.path.basename(filepath)}")
            print(f"     URL: {url}\n")
        
        print("=" * 60)
        print(f"✅ Generated {len(generated_files)} QR codes successfully!")
        print("=" * 60)
        
        return generated_files


def generate_qr_for_floor(floor_level, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Generate QR codes for all rooms on a specific floor."""
    app = create_app()
    
    with app.app_context():
        vyas = Building.query.filter_by(name='Vyas').first()
        if not vyas:
            print("❌ Error: Vyas building not found.")
            return []
        
        floor = Floor.query.filter_by(building_id=vyas.id, level=floor_level).first()
        if not floor:
            print(f"❌ Error: Floor level {floor_level} not found.")
            return []
        
        rooms = Room.query.filter_by(floor_id=floor.id).all()
        
        ensure_qr_directory()
        
        print("=" * 60)
        print("MIT-WPU Vyas Tracker - QR Code Generation")
        print("=" * 60)
        print(f"\n🏢 Floor: {floor.name}")
        print(f"🚪 Rooms: {len(rooms)}")
        print(f"\n🔄 Generating QR codes...\n")
        
        generated_files = []
        
        for room in rooms:
            filepath = save_qr_code(room, host, port)
            generated_files.append(filepath)
            url = f"http://{host}:{port}/report?room={room.number}"
            print(f"  ✅ {room.number}")
            print(f"     File: {os.path.basename(filepath)}")
            print(f"     URL: {url}\n")
        
        print("=" * 60)
        print(f"✅ Generated {len(generated_files)} QR codes successfully!")
        print("=" * 60)
        
        return generated_files


def generate_qr_for_room(room_number, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Generate QR code for a specific room."""
    app = create_app()
    
    with app.app_context():
        room = Room.query.filter_by(number=room_number.upper()).first()
        
        if not room:
            print(f"❌ Error: Room {room_number} not found.")
            return None
        
        ensure_qr_directory()
        
        filepath = save_qr_code(room, host, port)
        url = f"http://{host}:{port}/report?room={room.number}"
        
        print("=" * 60)
        print("MIT-WPU Vyas Tracker - QR Code Generation")
        print("=" * 60)
        print(f"\n✅ Generated QR code for {room.number}")
        print(f"📁 File: {filepath}")
        print(f"🔗 URL: {url}")
        print("=" * 60)
        
        return filepath


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Generate QR codes for MIT-WPU Vyas Tracker rooms',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_qr.py --all
  python scripts/generate_qr.py --all --host 192.168.1.100 --port 8080
  python scripts/generate_qr.py --floor 4
  python scripts/generate_qr.py --room VY404
        """
    )
    
    parser.add_argument('--all', action='store_true',
                        help='Generate QR codes for all rooms')
    parser.add_argument('--floor', type=int, metavar='LEVEL',
                        help='Generate QR codes for a specific floor (0-7)')
    parser.add_argument('--room', type=str, metavar='NUMBER',
                        help='Generate QR code for a specific room (e.g., VY404)')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                        help=f'Server hostname (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Server port (default: {DEFAULT_PORT})')
    
    args = parser.parse_args()
    
    if args.all:
        generate_all_qr_codes(args.host, args.port)
    elif args.floor is not None:
        generate_qr_for_floor(args.floor, args.host, args.port)
    elif args.room:
        generate_qr_for_room(args.room, args.host, args.port)
    else:
        parser.print_help()
        print("\n❌ Please specify one of: --all, --floor, or --room")


if __name__ == '__main__':
    main()
