# Docker Hub Publishing Setup

This repository uses GitHub Actions to automatically publish Docker images to Docker Hub when a new release is created.

## Prerequisites

1. A Docker Hub account
2. Access to this GitHub repository's settings

## Setup Instructions

### Step 1: Create a Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com)
2. Go to **Account Settings** → **Security** → **Access Tokens**
3. Click **New Access Token**
4. Give it a descriptive name (e.g., "GitHub Actions - RaceCraft")
5. Set permissions to **Read & Write**
6. Click **Generate**
7. **Copy the token immediately** (you won't be able to see it again)

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following two secrets:

   **Secret 1:**
   - Name: `DOCKERHUB_USERNAME`
   - Value: Your Docker Hub username

   **Secret 2:**
   - Name: `DOCKERHUB_TOKEN`
   - Value: The access token you created in Step 1

### Step 3: Create a Release

Once the secrets are configured, the workflow will automatically run when you publish a release:

1. Go to your repository's **Releases** page
2. Click **Draft a new release**
3. Create a new tag (e.g., `v1.0.0`)
4. Fill in release title and description
5. Click **Publish release**

The GitHub Actions workflow will automatically:
- Build the Docker image
- Push it to Docker Hub with tags:
  - `latest`
  - The version from your tag (e.g., `1.0.0`, `1.0`, `1`)
- Update the Docker Hub repository description

## Verifying the Workflow

After publishing a release:

1. Go to the **Actions** tab in your repository
2. Click on the "Docker Hub Publish" workflow run
3. Monitor the progress and check for any errors
4. Once complete, verify the image appears on Docker Hub

## Pulling the Published Image

After successful publication, anyone can pull the image:

```bash
# Pull the latest version
docker pull <your-dockerhub-username>/<repository-name-lowercase>:latest
# For this repository: docker pull <your-dockerhub-username>/racecraft:latest

# Pull a specific version
docker pull <your-dockerhub-username>/<repository-name-lowercase>:1.0.0
# For this repository: docker pull <your-dockerhub-username>/racecraft:1.0.0
```

**Note:** The image name is automatically derived from the GitHub repository name and converted to lowercase, as required by Docker Hub. For example, the repository `RaceCraft` becomes the Docker image `racecraft`.

## Troubleshooting

### Workflow fails with "authentication required"
- Verify your `DOCKERHUB_TOKEN` is correct
- Ensure the token has Read & Write permissions
- Check that the token hasn't expired

### Image name issues
- The workflow uses `<DOCKERHUB_USERNAME>/<repository-name-lowercase>` as the image name
- For this repository, it will be `<DOCKERHUB_USERNAME>/racecraft` (lowercase)
- Docker Hub requires lowercase repository names, so the workflow automatically converts the GitHub repository name to lowercase

### Build failures
- Check the Dockerfile is valid
- Review the workflow logs in the Actions tab
- Ensure all required files are present in the repository
