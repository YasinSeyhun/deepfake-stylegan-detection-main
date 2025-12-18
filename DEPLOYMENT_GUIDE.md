# Deployment Guide: External Server with Gitea & Docker

This guide explains how to set up the Deepfake Detection System on an external Linux server using Gitea for version control and Docker for deployment. It also covers how to enable automated updates (CI/CD-like behavior) so that pushing code from your local IDE updates the running services.

## 1. Prerequisites (Server Side)

*   **OS:** Ubuntu 22.04 LTS (Recommended) or any modern Linux distro.
*   **Hardware:** 
    *   CPU: 4+ Cores (for 2 clients + server)
    *   RAM: 32GB+ (Required for EfficientNet-B4 training)
    *   GPU: NVIDIA GPU (Strongly Recommended for training speed)
*   **Software:**
    *   Docker Engine & Docker Compose
    *   Git

## 2. Gitea Setup (Git Server)

You will push your code to a Gitea instance on the server instead of GitHub.

1.  **Install Gitea:** Follow the official [Gitea Docker Installation](https://docs.gitea.com/installation/install-with-docker).
2.  **Create Repository:** Create a new repo (e.g., `deepfake-detection`).
3.  **Local Git Remote:** Add this remote to your local IDE.
    ```bash
    git remote add production http://<server-ip>:3000/<username>/deepfake-detection.git
    ```

## 3. Automated Updates (The "Magic" Part)

To make the Docker containers update automatically when you push to Gitea, we have two main options. **Option B (Watchtower + Gitea Action)** is recommended for simplicity in this context.

### Option A: Webhook + Script (Simple)

1.  Create a shell script `deploy.sh` on the server:
    ```bash
    #!/bin/bash
    cd /path/to/project
    git pull origin main
    docker-compose up --build -d
    ```
2.  Set up a lightweight webhook listener (e.g., using `adnanh/webhook`) that executes this script when Gitea triggers a "push" event.

### Option B: Gitea Actions (Recommended for CI/CD)

1.  Enable Gitea Actions in `app.ini`.
2.  Create a file `.gitea/workflows/deploy.yaml` in your project:
    ```yaml
    name: Deploy to Production
    on: [push]
    jobs:
      deploy:
        runs-on: ubuntu-latest
        steps:
          - name: Check out code
            uses: actions/checkout@v3
          - name: Deploy
            run: |
              ssh user@<server-ip> "cd /app/deepfake && git pull && docker-compose up --build -d"
    ```

## 4. Manual Deployment (First Run)

1.  Clone the repo on the server:
    ```bash
    git clone http://localhost:3000/<username>/deepfake-detection.git
    cd deepfake-detection
    ```
2.  Run the system:
    ```bash
    docker-compose up --build -d
    ```

## 5. Troubleshooting Common Server Issues

*   **Ports:** Ensure ports `8000` (Backend), `8080/8081` (Flower), and `3000` (Web App/Gitea) are open in the server firewall (`ufw allow 8000`).
*   **Permissions:** Ensure the user running docker has permissions (`sudo usermod -aG docker $USER`).
