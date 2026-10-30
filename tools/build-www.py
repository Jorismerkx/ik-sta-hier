"""Kopieert de webapp naar www/ voor Capacitor (iOS/Android). Gebruik: python tools/build-www.py"""
import os, shutil
ROOT = os.path.join(os.path.dirname(__file__), '..'); WWW = os.path.join(ROOT, 'www')
if os.path.exists(WWW): shutil.rmtree(WWW)
os.makedirs(os.path.join(WWW, 'data'))
for f in ['index.html', 'style.css', 'config.js', 'app.js', 'plan.js', 'qr.js', 'social.js', 'manifest.webmanifest', 'sw.js']: shutil.copy(os.path.join(ROOT, f), WWW)
for f in ['venues.json', 'agenda.json']: shutil.copy(os.path.join(ROOT, 'data', f), os.path.join(WWW, 'data'))
shutil.copytree(os.path.join(ROOT, 'img'), os.path.join(WWW, 'img'))
print('www klaar')
