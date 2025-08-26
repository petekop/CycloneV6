# Cyclone project
# Date: 2025-07-19

from pathlib import Path

from flask import Flask, render_template_string, request

from utils.files import open_utf8

app = Flask(__name__)

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>Fighter Input</title>
    <style>
        body {
            background-color: #000;
            color: white;
            font-family: sans-serif;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            text-align: center;
            margin: 0;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 20px;
        }
        label {
            font-size: 1.3em;
            display: block;
            margin-bottom: 5px;
        }
        input[type="text"] {
            padding: 12px;
            font-size: 1.2em;
            width: 300px;
            margin-bottom: 20px;
            text-align: center;
            border-radius: 8px;
            border: none;
            box-shadow: 0 0 5px rgba(255,255,255,0.2);
        }
        input[type="submit"] {
            padding: 12px 24px;
            font-size: 1.2em;
            background-color: #444;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(255,255,255,0.1);
        }
        input[type="submit"]:hover {
            background-color: #666;
        }
        .message {
            margin-top: 30px;
            font-size: 1.4em;
            line-height: 1.8;
        }
        .success {
            color: #4CAF50;
        }
        .folder {
            font-size: 1em;
            color: #ccc;
            margin-top: 10px;
        }
        .icon-line {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }
    </style>
</head>
<body>
    <h1>Enter Fighter Names</h1>
    <form method="post">
        <label for="red">🔴 Red Corner</label>
        <input type="text" name="red" required>

        <label for="blue">🔵 Blue Corner</label>
        <input type="text" name="blue" required>

        <input type="submit" value="Submit">
    </form>

    {% if saved %}
        <div class="message success">
            ✅ <strong>Saved!</strong><br>
            <div class="icon-line">🔴 <span>Red: {{ red }}</span></div>
            <div class="icon-line">🔵 <span>Blue: {{ blue }}</span></div>
        </div>
        <div class="folder">📁 Folder created:<br>{{ folder }}</div>
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def input_names():
    red = blue = folder_path = ""
    if request.method == "POST":
        red = request.form.get("red", "").strip()
        blue = request.form.get("blue", "").strip()

        folder_name = f"{red.upper()}_RED_{blue.upper()}_BLUE"
        folder_path = Path("CAMSERVER") / folder_name
        Path(folder_path).mkdir(parents=True, exist_ok=True)

        with open_utf8("fighter_names.txt", "w") as f:
            f.write(f"RED={red}\nBLUE={blue}\n")

        return render_template_string(HTML_FORM, saved=True, red=red, blue=blue, folder=folder_path)

    return render_template_string(HTML_FORM, saved=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
