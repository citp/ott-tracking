#!/bin/bash
celery -A cloudvisiontextparser worker --loglevel=info -Ofair
