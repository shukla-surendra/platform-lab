FROM python:3.12-slim

RUN pip install --no-cache-dir "feast[sqlite]==0.49.0" pandas pyarrow

WORKDIR /feature_repo
COPY feature_repo/ .

RUN python generate_seed_data.py && feast apply

EXPOSE 6566
CMD ["feast", "serve", "-h", "0.0.0.0", "-p", "6566"]
