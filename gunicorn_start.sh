#!/bin/bash
nohup gunicorn -w 10 --worker-class=gevent MyLofter.wsgi:application &
