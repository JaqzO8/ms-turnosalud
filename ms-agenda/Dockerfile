FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json ./
COPY src ./src
RUN npm run build
ENV PORT=3001 DRIVER=pg HOST=0.0.0.0
EXPOSE 3001
CMD ["node", "dist/server.js"]
