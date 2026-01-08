from flask import Flask, render_template_string
import requests

app = Flask(__name__)

CONTROLLER_URL = "http://127.0.0.1:18080/"

HTML = """
<!doctype html>
<html>
<head>
    <title>Study Room Status</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .room {
            border: 1px solid #ddd;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 8px;
        }
        .free { color: green; font-weight: bold; }
        .busy { color: red; font-weight: bold; }
    </style>
</head>
<body>

<h1>📚 Study Room Status</h1>

{% for r in rooms %}
<div class="room">
    <h2>{{ r.room_id }}</h2>
    <p>👥 {{ r.students }} / {{ r.capacity }}</p>
    <p>🌡 {{ r.temperature }} °C</p>

    {% if r.available | int == 1 %}
        <p class="free">AVAILABLE</p>
    {% else %}
        <p class="busy">NOT AVAILABLE</p>
    {% endif %}
</div>
{% endfor %}

</body>
</html>
"""

@app.route("/")
def dashboard():
    try:
        resp = requests.get(CONTROLLER_URL, timeout=5)
        rooms = resp.json()
    except Exception as e:
        return f"<h2>Controller not reachable</h2><p>{e}</p>"

    return render_template_string(HTML, rooms=rooms)


if __name__ == "__main__":
    print("=== STUDENT DASHBOARD (FLASK) STARTED ===")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)