# Use an official n8n base image
FROM n8nio/n8n

# Switch to root user to install packages
USER root

# Install Python, pip, and any other system dependencies
# Update package list and install python3, python3-pip, and git (if needed for pip installs from git)
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements files for Python script dependencies
# Assuming mem0_handler.py and its dependencies are managed by these requirements files
# Place a copy of relevant parts of requirements.txt or a specific requirements_n8n.txt here
COPY ./requirements_n8n.txt /app/packages/nodes-base/
# Or, if requirements.txt is in the root of the main project:
# COPY ../../requirements.txt /app/packages/nodes-base/requirements_n8n.txt

# RUN pip3 install --no-cache-dir -r /app/packages/nodes-base/requirements_n8n.txt

# Copy the main requirements.txt from project root to a temporary location in the image
# Assuming the Docker build context for this Dockerfile is 'backend/n8n_custom/'
# So, '../../requirements.txt' refers to the project root's requirements.txt
COPY ../../requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy the n8n_scripts directory into the n8n container so workflows can execute them
# The workflows refer to 'backend/n8n_scripts/mem0_handler.py'.
# The Python script itself is located at /app/backend/n8n_scripts/mem0_handler.py in the repo.
# The Execute Command node in n8n will need to call this path.
# We should copy it to a location accessible by n8n, e.g., /home/node/backend/n8n_scripts
# Or, if n8n's working dir is /data, then make paths relative to that or use absolute.
# Let's copy the 'backend' directory into /home/node/ so the path backend/n8n_scripts/mem0_handler.py works.
# COPY ../../backend /home/node/backend
# This copies too much. Let's be specific:
COPY ../../backend/n8n_scripts /home/node/n8n_scripts_local/
# And adjust Execute Command node in n8n workflows to use 'python /home/node/n8n_scripts_local/mem0_handler.py ...'
# For now, the Dockerfile created /opt/n8n_scripts. The workflows use 'backend/n8n_scripts/mem0_handler.py'.
# This implies that the WORKDIR for ExecuteCommand in n8n should be the project root, or paths need to be absolute.
# Let's stick to /opt/n8n_scripts for the Python script location inside the container.
# The n8n workflows should then call `python /opt/n8n_scripts/mem0_handler.py ...`

# Original COPY for scripts:
# RUN mkdir -p /opt/n8n_scripts
# COPY ../n8n_scripts /opt/n8n_scripts/
# This assumed build context is 'backend/n8n_custom' and scripts are in '../n8n_scripts' relative to it.
# Correct path from context 'backend/n8n_custom/' to project's 'backend/n8n_scripts/' is '../../backend/n8n_scripts'.
RUN mkdir -p /opt/lifeboard_scripts
COPY ../../backend/n8n_scripts /opt/lifeboard_scripts/
# Ensure the script is executable if needed, though python execution doesn't require +x typically
RUN chmod -R +x /opt/lifeboard_scripts/

# The n8n Execute Command nodes will need to use `python /opt/lifeboard_scripts/mem0_handler.py ...`

# Ensure Python scripts can find modules if PYTHONPATH is needed, though pip install should handle it.
# ENV PYTHONPATH "${PYTHONPATH}:/opt/n8n_scripts" # Unlikely needed if using modules correctly

# Switch back to the node user
# n8n's base working directory for Execute Command might vary.
# A common location could be /home/node or within n8n's own structure.
# For simplicity, let's put it in a known path like /opt/n8n_scripts
RUN mkdir -p /opt/n8n_scripts
COPY ../n8n_scripts /opt/n8n_scripts/
# Ensure the script is executable if needed, though python execution doesn't require +x typically
RUN chmod -R +x /opt/n8n_scripts/

# Ensure Python scripts can find modules if PYTHONPATH is needed, though pip install should handle it.
# ENV PYTHONPATH "${PYTHONPATH}:/opt/n8n_scripts" # Unlikely needed if using modules correctly

# Switch back to the node user
USER node

# Expose n8n default port
EXPOSE 5678
