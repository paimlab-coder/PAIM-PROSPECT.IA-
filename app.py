# -*- coding: utf-8 -*-
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

import paim_engine as engine

app = Flask(__name__)
origins = os.environ.get(
    'CORS_ORIGINS',
    'https://paimlab-coder.github.io'
).split(',')
CORS(app, resources={r'/api/*': {'origins': [x.strip() for x in origins if x.strip()]}})

# Render free uses an ephemeral filesystem. Keep runtime files under /tmp.
runtime = Path(tempfile.gettempdir()) / 'paim_prospect_runtime'
runtime.mkdir(parents=True, exist_ok=True)
engine.TARGET = runtime
engine.CACHE = runtime / 'cache_overture'
engine.MUNICIPIOS_CSV = runtime / 'municipios_brasil.csv'
engine.CITY.clear()

_startup_error = None
try:
    engine.load_municipalities()
except Exception as exc:
    _startup_error = f'{type(exc).__name__}: {exc}'

@app.get('/')
def root():
    return jsonify({
        'ok': True,
        'service': 'PAIM IA PROSPECT API',
        'version': '46-github',
        'source': 'Overture Maps',
        'municipalities': len(engine.CITY),
        'startup_error': _startup_error,
    })

@app.get('/api/health')
def health():
    status = 200 if not _startup_error and len(engine.CITY) >= 5500 else 503
    return jsonify({
        'ok': status == 200,
        'version': '46-github',
        'source': 'Overture Maps',
        'municipalities': len(engine.CITY),
        'error': _startup_error,
    }), status

@app.post('/api/prospect')
def prospect_api():
    if _startup_error:
        return jsonify({'ok': False, 'error': _startup_error}), 503
    payload = request.get_json(silent=True) or {}
    try:
        city = str(payload.get('city', '')).strip()
        uf = str(payload.get('uf', '')).strip().upper()
        segment = str(payload.get('segment', '')).strip()
        km = max(5, min(100, int(payload.get('km', 20))))
        limit = max(1, min(1500, int(payload.get('limit', 50))))
        min_score = max(0, min(100, int(payload.get('min_score', 0))))
        if not city or not uf or not segment:
            return jsonify({'ok': False, 'error': 'UF, cidade e segmento são obrigatórios.'}), 400
        data = engine.prospect(city, uf, segment, km, limit, min_score)
        return jsonify(data)
    except Exception as exc:
        return jsonify({'ok': False, 'error': f'{type(exc).__name__}: {exc}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
