FROM ghcr.io/huggingface/text-generation-inference:0.9.2

COPY layers.py /opt/conda/lib/python3.9/site-packages/text_generation_server/utils/layers.py

COPY sagemaker-entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

HEALTHCHECK --timeout=300 CMD curl -f http://localhost:80/health

ENTRYPOINT ["./entrypoint.sh"]
CMD [ "" ]