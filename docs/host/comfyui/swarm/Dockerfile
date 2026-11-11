# Frontend only: the existing CUDA-enabled ComfyUI container remains the GPU backend.
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS build
ARG SWARM_REF=f86858dfe53f8c6138481f4ceae7e4ce9fa71d20
ADD https://codeload.github.com/mcmonkeyprojects/SwarmUI/tar.gz/${SWARM_REF} /tmp/swarm.tar.gz
RUN mkdir /SwarmUI \
 && tar -xzf /tmp/swarm.tar.gz -C /SwarmUI --strip-components=1
WORKDIR /SwarmUI
RUN dotnet publish src/SwarmUI.csproj -c Release -o /SwarmUI/src/bin/live_release

FROM mcr.microsoft.com/dotnet/aspnet:8.0-bookworm-slim
ENV HOME=/SwarmUI/Data/home \
    DOTNET_CLI_TELEMETRY_OPTOUT=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1
WORKDIR /SwarmUI
COPY --from=build --chown=1000:1000 /SwarmUI /SwarmUI
COPY entrypoint.sh /usr/local/bin/swarm-start
USER 1000:1000
EXPOSE 7801
ENTRYPOINT ["sh", "/usr/local/bin/swarm-start"]
