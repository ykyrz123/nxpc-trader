FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY nxpc_volume_trader.py entrypoint.sh ./
RUN chmod +x entrypoint.sh
RUN touch /app/nxpc_trader.log
ENTRYPOINT ["/app/entrypoint.sh"]
