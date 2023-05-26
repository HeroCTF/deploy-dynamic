# Deploy dynamic CTF challenges

## Features

- Multi containers 
- Multi exposed ports
- Each challenges are in a seperate network
- Supports `env` variables
- Supports memory limitation (`mem_limit`)
- Relation between containers using `hostname`
- Max instances time and duration
- Configure website name & favicon

## Getting started

1. Move [.env.sample](.env.sample) to `.env` and configure it.
2. Move [config.sample.json](config.sample.json) to `config.json` and configure it.
3. (optional) Add your HTTPs certificates (`fullchain.pem` and `privkey.pem`) to [nginx/certs](nginx/certs).
4. (optional) Change the [favicon](./app/static/img/favicon.ico).
5. Run the application:

Using `docker-compose`:

```bash
docker-compose build
docker-compose up -d
# or
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

Using `docker`:

```bash
docker build . -t deployapp

docker run --rm -p 5000:5000 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --env-file .env deployapp
```

Using `python3`:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt

export DATABASE_URI="sqlite:////tmp/sqlite.db"
export DEBUG=1
sudo -E python3 app.py
```

## Deployment

List of hosts:

- `master`: Web application.
- `slaves`: Where instances/containers are started.

> You need at least one host, the master and the slave can be the same host but its not recommended in production.
> You can setup as many slave as you want, each time a challenge is run, a slaves is taken randomly to host it.

Firewall configuration:

- `master`: expose HTTP/HTTPs ports (default: 80, 443)
- `slaves`: expose containers range (default: 10000-15000) and docker API to master (default: 2375)

> WARNING: Do NOT expose a docker API on internet !!!


## Todo

- Info page for a running container (admin), to see if crash and logs and RCE container
- pylint
- add more docs about `config.json` format

## Made with

- [Flask](https://flask.palletsprojects.com/)
- [docker-py](https://docker-py.readthedocs.io/en/stable/)

## Authors

- xanhacks (Maintainer)
- Log\_s (Contributor)
