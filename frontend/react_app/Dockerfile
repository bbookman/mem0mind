# Stage 1: Build the React app
FROM node:18 AS builder
WORKDIR /app
COPY package.json yarn.lock ./
# Using yarn as create-react-app default, adjust if using npm
RUN yarn install --frozen-lockfile
COPY . .
RUN yarn build

# Stage 2: Serve the static files with Nginx
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html

# Add a basic Nginx configuration (optional, but good for SPAs)
# Create an nginx.conf file if more specific config is needed, e.g., for client-side routing.
# For MVP, default Nginx config might be okay.
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
