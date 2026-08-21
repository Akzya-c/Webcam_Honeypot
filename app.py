"""
Webcam Honeypot - Catch attackers trying to watch your cameras!
When someone accesses your fake cameras, you capture THEIR image.
"""
from flask import Flask, render_template, request, jsonify, send_file, make_response
import cv2
import os
import json
from datetime import datetime
import base64
import threading
import time
import socket
import requests

app = Flask(__name__)

# Create folders for captured data
os.makedirs('captured/attackers', exist_ok=True)
os.makedirs('captured/logs', exist_ok=True)

class WebcamHoneypot:
    def __init__(self):
        self.visitors = {}
        self.camera_feeds = self.generate_fake_feeds()
        self.attack_count = 0
        
    def generate_fake_feeds(self):
        """Generate fake camera names"""
        return [
            {'id': 1, 'name': 'Living Room Camera', 'location': 'Home Office'},
            {'id': 2, 'name': 'Bedroom Camera', 'location': 'Master Bedroom'},
            {'id': 3, 'name': 'Baby Camera', 'location': 'Nursery'},
            {'id': 4, 'name': 'Backyard Camera', 'location': 'Garden'},
            {'id': 5, 'name': 'Security Camera', 'location': 'Front Door'},
        ]
    
    def get_visitor_info(self, request):
        """Get information about the visitor"""
        info = {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'referer': request.headers.get('Referer', 'Direct'),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'headers': dict(request.headers),
            'cookies': request.cookies,
            'method': request.method,
            'path': request.path
        }
        
        # Try to get real IP if behind proxy
        if request.headers.get('X-Forwarded-For'):
            info['ip'] = request.headers.get('X-Forwarded-For').split(',')[0]
        
        return info
    
    def capture_attacker(self, visitor_info):
        """Try to capture attacker's image"""
        self.attack_count += 1
        
        # Method 1: Try to access their camera via browser (requires user permission)
        # We'll handle this in JavaScript
        
        # Method 2: Save their info for now
        filename = f"captured/attackers/attacker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(visitor_info, f, indent=2)
        
        # Log the attack
        log_entry = f"[{visitor_info['time']}] Attack #{self.attack_count} from {visitor_info['ip']} - {visitor_info['user_agent'][:50]}...\n"
        with open('captured/logs/attacks.log', 'a') as f:
            f.write(log_entry)
        
        print(f"📸 Attack captured! #{self.attack_count} from {visitor_info['ip']}")
        return filename
    
    def generate_fake_frame(self, camera_id):
        """Generate a fake camera frame"""
        # Create a simple image with camera info
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
        
        # Create blank image
        img = Image.new('RGB', (640, 480), color='darkgreen')
        draw = ImageDraw.Draw(img)
        
        # Add camera info
        camera = self.camera_feeds[camera_id - 1]
        draw.text((20, 20), f"Camera: {camera['name']}", fill='lime')
        draw.text((20, 50), f"Location: {camera['location']}", fill='lime')
        draw.text((20, 80), f"Status: LIVE", fill='lime')
        draw.text((20, 110), f"Time: {datetime.now().strftime('%H:%M:%S')}", fill='lime')
        draw.text((20, 140), f"Motion: DETECTED", fill='red')
        
        # Add fake "motion" rectangles
        draw.rectangle([200, 200, 300, 250], outline='red', width=2)
        draw.rectangle([400, 300, 450, 350], outline='red', width=2)
        
        # Add "hacker detected" if this is a trap
        draw.text((20, 400), "⚠️ INTRUDER DETECTED ⚠️", fill='yellow')
        
        # Convert to bytes
        import io
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return img_byte_arr

# Initialize honeypot
honeypot = WebcamHoneypot()

@app.route('/')
def index():
    """Main dashboard showing all cameras"""
    visitor = honeypot.get_visitor_info(request)
    honeypot.capture_attacker(visitor)
    
    return render_template('index.html', 
                         cameras=honeypot.camera_feeds,
                         attack_count=honeypot.attack_count,
                         visitor_ip=visitor['ip'])

@app.route('/camera/<int:camera_id>')
def camera_view(camera_id):
    """Individual camera view"""
    visitor = honeypot.get_visitor_info(request)
    honeypot.capture_attacker(visitor)
    
    camera = next((c for c in honeypot.camera_feeds if c['id'] == camera_id), None)
    if not camera:
        return "Camera not found", 404
    
    return render_template('camera.html', 
                         camera=camera,
                         attack_count=honeypot.attack_count)

@app.route('/camera_feed/<int:camera_id>')
def camera_feed(camera_id):
    """Stream fake camera feed"""
    # This is the trap! When someone requests the feed, capture them
    visitor = honeypot.get_visitor_info(request)
    honeypot.capture_attacker(visitor)
    
    # Return fake frame
    frame = honeypot.generate_fake_frame(camera_id)
    response = make_response(frame)
    response.headers['Content-Type'] = 'image/jpeg'
    return response

@app.route('/capture_attacker', methods=['POST'])
def capture_attacker_photo():
    """Capture attacker's photo from their browser"""
    data = request.json
    photo_data = data.get('photo')
    
    if photo_data:
        # Remove header from base64
        photo_data = photo_data.split(',')[1]
        
        # Decode and save
        import base64
        photo_bytes = base64.b64decode(photo_data)
        
        filename = f"captured/attackers/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        with open(filename, 'wb') as f:
            f.write(photo_bytes)
        
        print(f"📸 ATTACKER PHOTO CAPTURED! Saved to {filename}")
        
        # Also save their info
        visitor = honeypot.get_visitor_info(request)
        info_filename = f"captured/attackers/info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(info_filename, 'w') as f:
            json.dump(visitor, f, indent=2)
        
        return jsonify({'success': True, 'filename': filename})
    
    return jsonify({'success': False})

@app.route('/stats')
def stats():
    """View attack statistics"""
    # Count captured data
    attacker_files = len(os.listdir('captured/attackers'))
    photo_files = len([f for f in os.listdir('captured/attackers') if f.startswith('photo_')])
    
    # Read log file
    log_lines = []
    if os.path.exists('captured/logs/attacks.log'):
        with open('captured/logs/attacks.log', 'r') as f:
            log_lines = f.readlines()[-50:]  # Last 50 lines
    
    return jsonify({
        'total_attacks': honeypot.attack_count,
        'total_visitors': attacker_files,
        'photos_captured': photo_files,
        'recent_logs': log_lines,
        'cameras': len(honeypot.camera_feeds)
    })

@app.route('/clear_logs')
def clear_logs():
    """Clear all captured data (for testing)"""
    import shutil
    shutil.rmtree('captured/attackers')
    shutil.rmtree('captured/logs')
    os.makedirs('captured/attackers', exist_ok=True)
    os.makedirs('captured/logs', exist_ok=True)
    honeypot.attack_count = 0
    return "All logs cleared!"

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════╗
    ║     📸 WEBCAM HONEYPOT - TRAP ACTIVATED    ║
    ╠════════════════════════════════════════════╣
    ║ • Fake cameras: 5                           ║
    ║ • Captures attacker info                     ║
    ║ • Takes attacker photos (if allowed)         ║
    ║ • Live at: http://localhost:5000            ║
    ╚════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)