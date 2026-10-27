/* db.js — SQLite-opslag (ingebouwd in Node, geen extra pakket) voor gebruikers, vrienden, events en de feed. */
'use strict';
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const SCHEMA = `
create table if not exists users (
  id text primary key, name text not null, code text unique not null, token text unique not null, created integer not null);
create table if not exists friends (
  a text not null, b text not null, created integer not null, primary key (a, b));
create table if not exists events (
  id text primary key, owner text not null, title text not null, venue text not null, rooms text not null,
  date text not null, time text, invite text unique not null, created integer not null);
create table if not exists members (
  event text not null, user text not null, joined integer not null, primary key (event, user));
create table if not exists feed (
  id integer primary key autoincrement, event text not null, user text not null, kind text not null,
  room integer, x real, y real, label text, created integer not null);
create index if not exists feed_event on feed (event, id);
create table if not exists subs (
  endpoint text primary key, user text not null, json text not null);
`;

const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // geen 0/O en 1/I: makkelijk over te tikken
const rid = (n = 12) => crypto.randomBytes(n).toString('base64url');
const hash = t => crypto.createHash('sha256').update(t).digest('hex');
const now = () => Date.now();

function open(dir) {
  const db = new DatabaseSync(path.join(dir, 'ish.db'));
  db.exec('pragma journal_mode = wal; pragma foreign_keys = on;');
  db.exec(SCHEMA);
  const q = sql => db.prepare(sql);

  const code = () => {
    for (;;) {
      const c = Array.from(crypto.randomBytes(6), b => CODE_CHARS[b % CODE_CHARS.length]).join('');
      if (!q('select 1 from users where code = ?').get(c)) return c;
    }
  };

  return {
    // ---------- gebruikers ----------
    createUser(name) {
      const id = rid(9), token = rid(24), c = code();
      q('insert into users (id, name, code, token, created) values (?, ?, ?, ?, ?)').run(id, name, c, hash(token), now());
      return { id, name, code: c, token };
    },
    userByToken: token => q('select id, name, code from users where token = ?').get(hash(token)),
    userByCode: c => q('select id, name, code from users where code = ?').get(String(c).toUpperCase()),
    user: id => q('select id, name, code from users where id = ?').get(id),
    rename: (id, name) => q('update users set name = ? where id = ?').run(name, id),

    // ---------- vrienden (altijd twee kanten op) ----------
    befriend(a, b) {
      if (a === b) return;
      const ins = q('insert or ignore into friends (a, b, created) values (?, ?, ?)');
      ins.run(a, b, now()); ins.run(b, a, now());
    },
    unfriend(a, b) { q('delete from friends where (a = ? and b = ?) or (a = ? and b = ?)').run(a, b, b, a); },
    friends: id => q('select u.id, u.name from friends f join users u on u.id = f.b where f.a = ? order by u.name collate nocase').all(id),
    areFriends: (a, b) => !!q('select 1 from friends where a = ? and b = ?').get(a, b),

    // ---------- events ----------
    createEvent({ owner, title, venue, rooms, date, time }) {
      const id = rid(9), invite = rid(8);
      q('insert into events (id, owner, title, venue, rooms, date, time, invite, created) values (?, ?, ?, ?, ?, ?, ?, ?, ?)')
        .run(id, owner, title, venue, JSON.stringify(rooms), date, time || null, invite, now());
      return id;
    },
    event(id) {
      const e = q('select * from events where id = ?').get(id);
      return e && { ...e, rooms: JSON.parse(e.rooms) };
    },
    eventByInvite(invite) {
      const e = q('select * from events where invite = ?').get(invite);
      return e && { ...e, rooms: JSON.parse(e.rooms) };
    },
    deleteEvent(id) {
      q('delete from feed where event = ?').run(id);
      q('delete from members where event = ?').run(id);
      q('delete from events where id = ?').run(id);
    },
    eventsOf: user => q('select e.id from events e join members m on m.event = e.id where m.user = ? order by e.date desc, e.time desc').all(user).map(r => r.id),
    addMember: (event, user) => q('insert or ignore into members (event, user, joined) values (?, ?, ?)').run(event, user, now()).changes > 0,
    removeMember: (event, user) => q('delete from members where event = ? and user = ?').run(event, user),
    isMember: (event, user) => !!q('select 1 from members where event = ? and user = ?').get(event, user),
    members: event => q('select u.id, u.name from members m join users u on u.id = m.user where m.event = ? order by m.joined').all(event),

    // ---------- feed ----------
    addFeed({ event, user, kind, room = null, x = null, y = null, label = null }) {
      const r = q('insert into feed (event, user, kind, room, x, y, label, created) values (?, ?, ?, ?, ?, ?, ?, ?)')
        .run(event, user, kind, room, x, y, label, now());
      return this.feedItem(Number(r.lastInsertRowid));
    },
    feedItem: id => q('select f.*, u.name from feed f join users u on u.id = f.user where f.id = ?').get(id),
    feed: (event, limit = 200) => q('select * from (select f.*, u.name from feed f join users u on u.id = f.user where f.event = ? order by f.id desc limit ?) order by id').all(event, limit),
    lastFeed: event => q('select f.*, u.name from feed f join users u on u.id = f.user where f.event = ? order by f.id desc limit 1').get(event),

    // ---------- pushabonnementen ----------
    addSub: (user, sub) => q('insert or replace into subs (endpoint, user, json) values (?, ?, ?)').run(sub.endpoint, user, JSON.stringify(sub)),
    subsOf: user => q('select endpoint, json from subs where user = ?').all(user).map(r => JSON.parse(r.json)),
    dropSub: endpoint => q('delete from subs where endpoint = ?').run(endpoint),
  };
}

module.exports = { open, rid };
