FROM node:18-alpine

# Create app directory
WORKDIR /usr/src/app

# Copy package definition first to leverage Docker layer caching
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy rest of the files
COPY dist ./dist
COPY policies ./policies
COPY README.md ./README.md

# Expose the API port
EXPOSE 3000

# Start the API by default
CMD ["npm", "run", "api"]