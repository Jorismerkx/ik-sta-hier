/* push.js — web-push (VAPID): meldingen naar de telefoon, ook als de app dicht is.
   Werkt in Chrome/Android en in Safari op iPhone als de app op het beginscherm staat (iOS 16.4+). */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const webpush = require('web-push');

// SOS-ritme (kort-kort-kort, lang-lang-lang, kort-kort-kort): valt op tussen de bassen
const SOS = [90, 60, 90, 60, 90, 180, 260, 80, 260, 80, 260, 180, 90, 60, 90, 60, 90];

function init(dataDir, subject) {
  let keys = process.env.VAPID_PUBLIC && process.env.VAPID_PRIVATE
    ? { publicKey: process.env.VAPID_PUBLIC, privateKey: process.env.VAPID_PRIVATE } : null;
  const file = path.join(dataDir, 'vapid.json');
  if (!keys && fs.existsSync(file)) keys = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (!keys) { keys = webpush.generateVAPIDKeys(); fs.writeFileSync(file, JSON.stringify(keys)); }
  webpush.setVapidDetails(subject, keys.publicKey, keys.privateKey);
  return keys.publicKey;
}

/** Stuur een melding naar alle telefoons van deze gebruikers. Verlopen abonnementen worden opgeruimd. */
async function send(db, userIds, msg) {
  const payload = JSON.stringify({ ...msg, vibrate: msg.urgent ? SOS : [120, 60, 120] });
  const jobs = [];
  for (const id of userIds) {
    for (const sub of db.subsOf(id)) {
      jobs.push(webpush.sendNotification(sub, payload, { TTL: 60 * 30, urgency: msg.urgent ? 'high' : 'normal' })
        .catch(e => { if (e.statusCode === 404 || e.statusCode === 410) db.dropSub(sub.endpoint); }));
    }
  }
  await Promise.all(jobs);
}

module.exports = { init, send };
