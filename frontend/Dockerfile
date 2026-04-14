FROM node:20-slim

WORKDIR /app


# Copy package files (ignore lockfile for cross-platform compatibility)
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Ensure rewrites are compiled with the container backend host
ARG BACKEND_URL=http://backend:5000
ENV BACKEND_URL=${BACKEND_URL}

# Build the application
# We need to ensure environment variables are available at build time if they are embedded,
# but for rewrites they are read at runtime in next.config.mjs if we don't hardcode them.
# The rewrite uses process.env.BACKEND_URL which is good.
RUN npm run build

# Set production environment for runtime
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

# Expose port
EXPOSE 3000

# Run application
CMD ["npm", "start"]
