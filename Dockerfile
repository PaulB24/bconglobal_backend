FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements.txt


RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
#RUN pip install --no-cache-dir uwsgi==2.0.20

RUN apt-get update && apt-get install -y --no-install-recommends\
  ntp\
  && apt-get install -y postgresql-client\
  && apt-get clean\
  && rm -rf /var/lib/apt/lists/*


#RUN apt-get update -y
#RUN apt-get install ntp -y --no-install-recommends

#RUN apt-get update -y
#RUN apt install ntp -y
#RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .



