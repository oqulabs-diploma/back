#### Create a virtual machine, get the ip address

#### Add this ip address to the DNS

#### Generate an ssh key for github

```bash
sudo -i
ssh-keygen -t rsa -b 4096
cat ~/.ssh/id_rsa.pub
```

Add this key to GitHub

#### Prepare the code and install nginx

Note that we need to install nginx first just for /var/www to be created

```bash
sudo -i
apt-get update
apt-get install nginx

cd /var/www
git clone git@github.com:timurbakibayev/oqulabs.git
cd oqulabs
git config pull.rebase true
apt install python3.12-venv
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
cp /var/www/oqulabs/install/example_local_settings.py /var/www/oqulabs/sms/local_settings.py
vi /var/www/oqulabs/sms/local_settings.py

python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser

cp /var/www/oqulabs/install/gunicorn_start /var/www/oqulabs/
chmod +x /var/www/oqulabs/gunicorn_start
```

Check gunicorn_start:

```bash
./gunicorn_start
```

#### Install supervisor

```bash
apt-get install supervisor
cp /var/www/oqulabs/install/supervisor/oqulabs.conf /etc/supervisor/conf.d/
cp /var/www/oqulabs/install/supervisor/s3_oqulabs.conf /etc/supervisor/conf.d/
cp /var/www/oqulabs/install/supervisor/ai_oqulabs.conf /etc/supervisor/conf.d/
supervisorctl reread
supervisorctl update
supervisorctl status
```

#### Setup nginx

```bash
sudo -i
cp /var/www/oqulabs/install/nginx/oqulabs /etc/nginx/sites-enabled/
vi /etc/nginx/sites-enabled/oqulabs
```

edit the file `/etc/nginx/sites-enabled/oqulabs` and change the `server_name`

```bash
nginx -t
service nginx restart
```

#### Install certbot

```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx
```

