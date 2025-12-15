# 🐳 Docker Deployment Guide

This guide provides detailed instructions for deploying the **Federated Deepfake Detection System** using Docker and Docker Compose. This approach ensures a consistent environment for all components: Server, Backend, WebApp, and Clients.

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Engine and Docker Compose)
- **Windows Users**: Ensure WSL 2 backend is enabled for best performance.

## 🛠️ Service Overview

The system is composed of several orchestrated containers. Here is breakdown of each service:

| Service | Container Name | Internal Port | External Port | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Server** | `deepfake-server` | 8080 | 8081 | The central Federated Learning server. Orchestrates training rounds and aggregates model updates from clients. |
| **Backend** | `deepfake-backend` | 8000 | 8000 | FastAPI-based backend. Handles image uploads, runs inference using the global model, and generates Grad-CAM visualizations. |
| **Webapp** | `deepfake-webapp` | 3000 | 3000 | Next.js frontend application. Provides the user interface for uploading images and viewing results. |
| **Client 1** | `deepfake-client_1` | - | - | Simulated FL Client Node 1. Trains the model on its local data partition. |
| **Client 2** | `deepfake-client_2` | - | - | Simulated FL Client Node 2. Trains the model on its local data partition. |
| **Redis** | `deepfake-redis` | 6379 | 6379 | In-memory data store used for caching and message brokerage (if enabled in config). |

## ⚙️ Configuration

You can customize the deployment by modifying the `.env` file in the root directory.

**Example `.env` configuration:**
```env
# Federated Learning Settings
MIN_CLIENTS=2
ROUNDS=10
MAX_CLIENTS=10

# Security
SECRET_KEY=your_secure_random_key_here

# Docker Network (Optional adjustments)
SERVER_ADDRESS=server:8081
```

## 🚀 Running the System

### 1. Build and Start
To build the Docker images and start all services, run the following command in the project root:

```bash
docker-compose up --build
```
*The `--build` flag ensures that any changes to the code are rebuilt into the containers.*

### 2. Verify Deployment
Once the containers are running, you can access the services at the following URLs:

- **Web Interface**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Server Logs**: Check the terminal output to watch the Federated Learning rounds progress.

### 3. Stopping the System
To stop the containers and remove the created networks:
```bash
docker-compose down
```

## ⚠️ Troubleshooting

**Common Issues:**

*   **Port Conflicts**: 
    *   Error: `Bind for 0.0.0.0:8000 failed: port is already allocated`.
    *   **Fix**: Ensure no other application is using ports 3000, 8000, or 8081. You can change the port mapping in `docker-compose.yml` if necessary.

*   **Client Connection Errors**:
    *   Symptom: Clients print `Connection refused` logs.
    *   **Cause**: The clients may start before the server is fully ready.
    *   **Fix**: The clients have built-in retry logic. They will automatically connect once the server is up. No action is needed; just wait a few seconds.

*   **Memory Issues**:
    *   Symptom: Containers exit unexpectedly with code 137.
    *   **Fix**: Increase the memory limit in Docker Desktop settings (Settings -> Resources -> Memory).
