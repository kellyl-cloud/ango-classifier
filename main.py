from flask import Flask, request, jsonify, send_from_directory
import urllib.request, json, os, base64, urllib.parse

app = Flask(__name__, static_folder='.')
ANGO_KEY = ""
OPENAI_KEY = ""
ANGO_BASE = "https://imeritapi.ango.ai"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/set-keys', methods=['POST','OPTIONS'])
def set_keys():
    global ANGO_KEY, OPENAI_KEY
    if request.method == 'OPTIONS':
        return cors('')
    data = request.json
    ANGO_KEY = data.get('angoKey','')
    OPENAI_KEY = data.get('openaiKey','')
    return cors(jsonify({"ok":True}))

@app.route('/ango')
def ango():
    project = request.args.get('project','')
    page = request.args.get('page','1')
    url = f"{ANGO_BASE}/v2/project/{project}/tasks?page={page}&limit=50&stage=Complete"
    req = urllib.request.Request(url, headers={"apikey": ANGO_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return cors(jsonify(json.loads(r.read())))
    except urllib.error.HTTPError as e:
        return cors(jsonify({"error": e.read().decode()})), e.code

@app.route('/audio')
def audio():
    audio_url = request.args.get('url','')
    headers = {"apikey": ANGO_KEY} if "ango.ai" in audio_url else {}
    req = urllib.request.Request(audio_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=55) as r:
            raw = r.read(1024 * 1024)
            ct = r.headers.get("Content-Type","audio/wav")
        return cors(jsonify({"base64": base64.b64encode(raw).decode(), "mimeType": ct}))
    except Exception as e:
        return cors(jsonify({"error": str(e)})), 500

@app.route('/openai-audio', methods=['POST','OPTIONS'])
def openai_audio():
    if request.method == 'OPTIONS':
        return cors('')
    data = request.json
    audio_bytes = base64.b64decode(data['audio'])
    mime = data.get('mimeType','audio/wav')
    fmt = 'mp3' if 'mp3' in mime else 'wav'
    boundary = b'----B' + os.urandom(4).hex().encode()
    parts  = b'--'+boundary+b'\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n'
    parts += b'--'+boundary+b'\r\nContent-Disposition: form-data; name="response_format"\r\n\r\njson\r\n'
    parts += b'--'+boundary+b'\r\nContent-Disposition: form-data; name="file"; filename="audio.'+fmt.encode()+b'"\r\nContent-Type: '+mime.encode()+b'\r\n\r\n'+audio_bytes+b'\r\n'
    parts += b'--'+boundary+b'--\r\n'
    req = urllib.request.Request('https://api.openai.com/v1/audio/transcriptions', parts,
        {'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'})
    try:
        with urllib.request.urlopen(req, timeout=55) as r:
            result = json.loads(r.read().decode('utf-8'))
            return cors(jsonify(result))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return cors(jsonify({"error": error_body})), e.code

@app.route('/openai', methods=['POST','OPTIONS'])
def openai():
    if request.method == 'OPTIONS':
        return cors('')
    data = request.json
    req = urllib.request.Request(data['url'], json.dumps(data['body']).encode(),
        {'Authorization': f'Bearer {OPENAI_KEY}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=55) as r:
            return cors(jsonify(json.loads(r.read().decode('utf-8'))))
    except urllib.error.HTTPError as e:
        return cors(jsonify({"error": e.read().decode()})), e.code

def cors(response):
    from flask import make_response
    if isinstance(response, str):
        response = make_response(response)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
