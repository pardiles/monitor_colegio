# ============================================================
# Dockerfile para Lambda Ingesta
# Python 3.12 + Playwright (Chromium) para SchoolNet
# Node.js incluido para compatibilidad futura con whatsapp-web.js
# ============================================================

FROM public.ecr.aws/lambda/python:3.12

# Instalar dependencias del sistema para Playwright/Chromium
RUN dnf install -y \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    alsa-lib \
    at-spi2-atk \
    libdrm \
    libgbm \
    nss \
    xorg-x11-server-Xvfb \
    mesa-libgbm \
    dbus-glib \
    && dnf clean all

# Instalar Node.js 20 (para futura integración con whatsapp-web.js si se necesita)
RUN dnf install -y nodejs && dnf clean all

# Copiar requirements e instalar dependencias Python
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Instalar Playwright con Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

# Copiar el código fuente
COPY handler.py ${LAMBDA_TASK_ROOT}/
COPY config.py ${LAMBDA_TASK_ROOT}/
COPY sources/ ${LAMBDA_TASK_ROOT}/sources/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/

# Handler de Lambda
CMD ["handler.lambda_handler"]
