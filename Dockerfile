# Specify the base image (Python 3.11 in this case)
FROM python:3.11
# Specify the base image (Python 3.11 in this case)
RUN apt update
RUN apt install curl -y
RUN apt install nodejs -y
RUN apt install npm -y
RUN npm install -y lighthouse -g
RUN apt install mlocate -y
RUN apt install net-tools -y

# NVM Install
#SHELL ["/bin/bash", "--login", "-c"]
#RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.3/install.sh | bash

RUN pip install --upgrade pip
RUN su -c "pip3 install jobspy"
RUN su -c "pip3 install tls_client"
RUN apt install software-properties-common -y
RUN apt install openjdk-17-jdk -y
RUN java --version
WORKDIR /app
# Customization
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.5/zsh-in-docker.sh)" -- \
    -t https://github.com/denysdovhan/spaceship-prompt \
    -a 'SPACESHIP_PROMPT_ADD_NEWLINE="false"' \
    -a 'SPACESHIP_PROMPT_SEPARATE_LINE="false"' \
    -p git \
    -p ssh-agent \
    -p https://github.com/zsh-users/zsh-autosuggestions \
    -p https://github.com/zsh-users/zsh-completions
# Copy your Python application files to the container
COPY . /app/


RUN su -c "pip3 install uvicorn"
RUN su -c "pip3 install pymupdf4llm"
RUN su -c "pip3 install pdfplumber"
RUN su -c "pip3 install markdownify"
RUN su -c "pip install llama-cpp-python"
RUN su -c "pip3 install huggingface-hub"

# Set the working directory inside the container
WORKDIR /app

#Innstall dependencies (if any)
RUN pip install -r requirements.txt

EXPOSE 8000
# Define the command to run when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]