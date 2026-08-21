from flask import Flask, render_template, request, jsonify, make_response
import os
import json
from datetime import datetime

app = Flask(__name__)

# Local/demo storage directories.
# Note: Vercel's filesystem is temporary, so don't treat these
# files as permanent storage in production.
os.makedirs("captured/attackers", exist_ok=True)
os.makedirs("captured/logs", exist_ok=True)


class WebcamHoneypot:
    def __init__(self):
        self.visitors = {}
        self.camera_feeds = self.generate_fake_feeds()
        self.attack_count = 0

    def generate_fake_feeds(self):
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
        forwarded_for = req.headers.get("X-Forwarded-For")

        ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else req.remote_addr
        )

        return {
            "ip": ip,
            "user_agent": req.headers.get(
                "User-Agent",
                "Unknown"
            ),
            "referer": req.headers.get(
                "Referer",
                "Direct"
            ),
            "time": datetime.utcnow().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "method": req.method,
            "path": req.path
        }

    def capture_attacker(self, visitor_info):
        self.attack_count += 1

        timestamp = datetime.utcnow().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        filename = (
            f"captured/attackers/"
            f"attacker_{timestamp}.json"
        )

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    visitor_info,
                    f,
                    indent=2
                )

            log_entry = (
                f"[{visitor_info['time']}] "
                f"Attack #{self.attack_count} "
                f"from {visitor_info['ip']} - "
                f"{visitor_info['user_agent'][:50]}...\n"
            )

            with open(
                "captured/logs/attacks.log",
                "a",
                encoding="utf-8"
            ) as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Storage warning: {e}")

        print(
            f"Attack detected: "
            f"#{self.attack_count} "
            f"from {visitor_info['ip']}"
        )

        return filename

    def generate_fake_frame(self, camera_id):
        """
        Generate a fake camera frame.

        This uses Pillow instead of OpenCV.
        """
        from PIL import Image, ImageDraw

        if camera_id < 1 or camera_id > len(self.camera_feeds):
            return None

        camera = self.camera_feeds[camera_id - 1]

        image = Image.new(
            "RGB",
            (640, 480),
            "darkgreen"
        )

        draw = ImageDraw.Draw(image)

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
            datetime.utcnow().strftime(
                "Time: %H:%M:%S"
            ),
            fill="lime"
        )

        draw.text(
            (20, 140),
            "Motion: DETECTED",
            fill="red"
        )

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

        import io

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG"
        )

        output.seek(0)

        return output.getvalue()


honeypot = WebcamHoneypot()


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

    if camera is None:
        return "Camera not found", 404

    return render_template(
        "camera.html",
        camera=camera,
        attack_count=honeypot.attack_count
    )


@app.route("/camera_feed/<int:camera_id>")
def camera_feed(camera_id):
    visitor = honeypot.get_visitor_info(request)

    honeypot.capture_attacker(visitor)

    frame = honeypot.generate_fake_frame(camera_id)

    if frame is None:
        return "Camera not found", 404

    response = make_response(frame)

    response.headers["Content-Type"] = "image/jpeg"

    return response


@app.route("/capture_attacker", methods=["POST"])
def capture_attacker_photo():
    """
    Receives a camera image only when the browser has
    obtained camera permission from the user.
    """

    data = request.get_json(silent=True) or {}

    photo_data = data.get("photo")

    if not photo_data:
        return jsonify({
            "success": False,
            "error": "No photo provided"
        }), 400

    try:
        import base64

        if "," in photo_data:
            photo_data = photo_data.split(",", 1)[1]

        photo_bytes = base64.b64decode(photo_data)

        timestamp = datetime.utcnow().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        filename = (
            f"captured/attackers/"
            f"photo_{timestamp}.jpg"
        )

        with open(filename, "wb") as f:
            f.write(photo_bytes)

        visitor = honeypot.get_visitor_info(request)

        info_filename = (
            f"captured/attackers/"
            f"info_{timestamp}.json"
        )

        with open(
            info_filename,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                visitor,
                f,
                indent=2
            )

        return jsonify({
            "success": True,
            "message": "Photo received",
            "filename": filename
        })

    except Exception as e:
        print(f"Photo processing error: {e}")

        return jsonify({
            "success": False,
            "error": "Unable to process photo"
        }), 500


@app.route("/stats")
def stats():
    try:
        attacker_files = os.listdir(
            "captured/attackers"
        )

        photo_files = [
            f
            for f in attacker_files
            if f.startswith("photo_")
        ]

        log_lines = []

        log_path = "captured/logs/attacks.log"

        if os.path.exists(log_path):
            with open(
                log_path,
                "r",
                encoding="utf-8"
            ) as f:
                log_lines = f.readlines()[-50:]

        return jsonify({
            "total_attacks": honeypot.attack_count,
            "total_visitors": len(attacker_files),
            "photos_captured": len(photo_files),
            "recent_logs": log_lines,
            "cameras": len(honeypot.camera_feeds)
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/clear_logs")
def clear_logs():
    import shutil

    try:
        shutil.rmtree(
            "captured/attackers",
            ignore_errors=True
        )

        shutil.rmtree(
            "captured/logs",
            ignore_errors=True
        )

        os.makedirs(
            "captured/attackers",
            exist_ok=True
        )

        os.makedirs(
            "captured/logs",
            exist_ok=True
        )

        honeypot.attack_count = 0

        return "All logs cleared!"

    except Exception as e:
        return f"Error clearing logs: {e}", 500


if __name__ == "__main__":
    print(
        """
        ============================================
             WEBCAM HONEYPOT - TRAP ACTIVATED
        ============================================
        Fake cameras: 5
        Visitor information: enabled
        Browser camera capture: permission required
        Local development: http://localhost:5000
        ============================================
        """
    )

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
