"""
Webcam Honeypot
A fake webcam monitoring dashboard that logs visitor information.

Designed to run on Vercel / Flask serverless environment.
"""

from flask import Flask, render_template, request, jsonify, make_response
from datetime import datetime
import io

app = Flask(__name__)


class WebcamHoneypot:

    def __init__(self):
        self.visitors = {}
        self.camera_feeds = self.generate_fake_feeds()
        self.attack_count = 0

    def generate_fake_feeds(self):
        """Generate fake camera names."""

        return [
            {
                "id": 1,
                "name": "Living Room Camera",
                "location": "Home Office"
            },
            {
                "id": 2,
                "name": "Bedroom Camera",
                "location": "Master Bedroom"
            },
            {
                "id": 3,
                "name": "Baby Camera",
                "location": "Nursery"
            },
            {
                "id": 4,
                "name": "Backyard Camera",
                "location": "Garden"
            },
            {
                "id": 5,
                "name": "Security Camera",
                "location": "Front Door"
            }
        ]

    def get_visitor_info(self, req):
        """Collect basic request information."""

        forwarded_for = req.headers.get("X-Forwarded-For")

        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = req.remote_addr or "Unknown"

        info = {
            "ip": ip,
            "user_agent": req.headers.get(
                "User-Agent",
                "Unknown"
            ),
            "referer": req.headers.get(
                "Referer",
                "Direct"
            ),
            "time": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "method": req.method,
            "path": req.path
        }

        return info

    def capture_attacker(self, visitor_info):
        """
        Record visitor information.

        IMPORTANT:
        Vercel serverless functions have a read-only
        filesystem, so we do not save files here.

        Instead, information is printed to runtime logs.
        """

        self.attack_count += 1

        log_entry = (
            f"[{visitor_info['time']}] "
            f"Attack #{self.attack_count} "
            f"from {visitor_info['ip']} - "
            f"{visitor_info['user_agent'][:80]}"
        )

        print(log_entry)

        return visitor_info

    def generate_fake_frame(self, camera_id):
        """Generate a fake camera image."""

        from PIL import Image, ImageDraw

        camera = self.camera_feeds[camera_id - 1]

        # Create fake camera screen
        img = Image.new(
            "RGB",
            (640, 480),
            color="darkgreen"
        )

        draw = ImageDraw.Draw(img)

        # Camera information
        draw.text(
            (20, 20),
            f"Camera: {camera['name']}",
            fill="lime"
        )

        draw.text(
            (20, 50),
            f"Location: {camera['location']}",
            fill="lime"
        )

        draw.text(
            (20, 80),
            "Status: LIVE",
            fill="lime"
        )

        draw.text(
            (20, 110),
            f"Time: {datetime.now().strftime('%H:%M:%S')}",
            fill="lime"
        )

        draw.text(
            (20, 140),
            "Motion: DETECTED",
            fill="red"
        )

        # Fake motion detection boxes
        draw.rectangle(
            [200, 200, 300, 250],
            outline="red",
            width=2
        )

        draw.rectangle(
            [400, 300, 450, 350],
            outline="red",
            width=2
        )

        draw.text(
            (20, 400),
            "INTRUDER DETECTED",
            fill="yellow"
        )

        # Convert image to bytes
        image_bytes = io.BytesIO()

        img.save(
            image_bytes,
            format="JPEG"
        )

        image_bytes.seek(0)

        return image_bytes.getvalue()


# --------------------------------------------------
# INITIALIZE HONEYPOT
# --------------------------------------------------

honeypot = WebcamHoneypot()


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():

    visitor = honeypot.get_visitor_info(request)

    honeypot.capture_attacker(visitor)

    return render_template(
        "index.html",
        cameras=honeypot.camera_feeds,
        attack_count=honeypot.attack_count,
        visitor_ip=visitor["ip"]
    )


# --------------------------------------------------
# CAMERA PAGE
# --------------------------------------------------

@app.route("/camera/<int:camera_id>")
def camera_view(camera_id):

    visitor = honeypot.get_visitor_info(request)

    honeypot.capture_attacker(visitor)

    camera = next(
        (
            camera
            for camera in honeypot.camera_feeds
            if camera["id"] == camera_id
        ),
        None
    )

    if not camera:
        return "Camera not found", 404

    return render_template(
        "camera.html",
        camera=camera,
        attack_count=honeypot.attack_count
    )


# --------------------------------------------------
# FAKE CAMERA FEED
# --------------------------------------------------

@app.route("/camera_feed/<int:camera_id>")
def camera_feed(camera_id):

    if camera_id < 1 or camera_id > len(
        honeypot.camera_feeds
    ):
        return "Camera not found", 404

    visitor = honeypot.get_visitor_info(request)

    honeypot.capture_attacker(visitor)

    frame = honeypot.generate_fake_frame(
        camera_id
    )

    response = make_response(frame)

    response.headers[
        "Content-Type"
    ] = "image/jpeg"

    return response


# --------------------------------------------------
# BROWSER CAMERA ENDPOINT
# --------------------------------------------------

@app.route(
    "/capture_attacker",
    methods=["POST"]
)
def capture_attacker_photo():

    data = request.get_json(
        silent=True
    ) or {}

    photo_data = data.get("photo")

    if not photo_data:

        return jsonify({
            "success": False,
            "error": "No photo provided"
        }), 400

    visitor = honeypot.get_visitor_info(
        request
    )

    print(
        "Camera image received."
    )

    print(
        f"Visitor IP: {visitor['ip']}"
    )

    print(
        f"User Agent: {visitor['user_agent']}"
    )

    # We intentionally DO NOT save the image
    # because Vercel's filesystem is read-only.

    return jsonify({
        "success": True,
        "message": "Camera image received successfully"
    })


# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

@app.route("/stats")
def stats():

    return jsonify({
        "total_attacks": honeypot.attack_count,
        "total_visitors": honeypot.attack_count,
        "photos_captured": 0,
        "cameras": len(
            honeypot.camera_feeds
        ),
        "status": "Honeypot running"
    })


# --------------------------------------------------
# CLEAR LOGS
# --------------------------------------------------

@app.route("/clear_logs")
def clear_logs():

    honeypot.attack_count = 0

    return jsonify({
        "success": True,
        "message": "Statistics cleared"
    })


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "Webcam Honeypot",
        "cameras": len(
            honeypot.camera_feeds
        )
    })


# --------------------------------------------------
# LOCAL DEVELOPMENT
# --------------------------------------------------

if __name__ == "__main__":

    print(
        """
        ============================================
             WEBCAM HONEYPOT - TRAP ACTIVATED
        ============================================

        Fake cameras: 5

        Captures visitor information:
        YES

        Persistent file storage:
        NO - Vercel filesystem is read-only

        Local server:
        http://localhost:5000

        ============================================
        """
    )

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
