FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
