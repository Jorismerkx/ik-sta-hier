# Ik sta hier: server (API, live updates, web-push) plus de webapp, in één container.
# Draait op elke host met Docker (Railway, Render, Fly.io). Zet een volume op /data: daar staan de database en de VAPID-sleutels.
FROM node:24-alpine
WORKDIR /app
COPY server/package.json server/package-lock.json server/
RUN cd server && npm ci --omit=dev
COPY index.html style.css config.js app.js plan.js social.js sw.js manifest.webmanifest ./
COPY data/venues.json data/agenda.json data/
COPY img img
COPY server/*.js server/
ENV PORT=8080 DATA_DIR=/data
EXPOSE 8080
CMD ["node", "server/server.js"]
