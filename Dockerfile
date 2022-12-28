# -- build dependencies with debian(multiarch) --
FROM python:3.8-slim AS build
LABEL maintainer=me@tcw.im
ARG PIPMIRROR=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements /requirements
RUN pip install --timeout 30 --index $PIPMIRROR --user --no-cache-dir --no-warn-script-location -r /requirements/all.txt

# -- app environment(multiarch) --
FROM python:3.8-alpine
ENV LOCAL_PKG="/root/.local"
ENV sapic_isrun=true
COPY --from=build ${LOCAL_PKG} ${LOCAL_PKG}
RUN apk upgrade --no-cache && \
    apk add --no-cache libgcc libstdc++ gcompat && \
    ln -sf ${LOCAL_PKG}/bin/flask ${LOCAL_PKG}/bin/gunicorn /bin/ && \
    ln -sf $(which python) /python && \
    sed -i "s#$(which python)#/python#" /bin/gunicorn
WORKDIR /picbed
COPY src /picbed
EXPOSE 9514
ENTRYPOINT ["gunicorn", "app:app", "-c", "sapicd.py"]
