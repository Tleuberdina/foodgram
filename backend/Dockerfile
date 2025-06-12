FROM python:3.12


WORKDIR /app

RUN pip install gunicorn==23.0.0

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

#RUN mkdir -p /app/data

#COPY ./data/ingredients.json /app/data/

#COPY foods/management/ /app/foods/management/

CMD ["gunicorn", "--bind", "0.0.0.0:8800", "backend.wsgi"]
#CMD ["sh", "-c", "python manage.py wait_for_db && \
     #python manage.py import_json /app/data/ingredients.json && \
     #gunicorn --bind 0.0.0.0:8800 backend.wsgi"]
