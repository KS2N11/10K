FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port 5173 (Vite default port)
EXPOSE 5173

# Start Vite development server with host flag to allow external access
CMD ["npm", "run", "dev", "--", "--host"]