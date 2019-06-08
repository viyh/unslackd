# unslackd

## Develop

```
docker run --rm -it -v $(pwd):/src python:3.6 /bin/bash
```

## Deploy

```
python3 -m pip install -r requirements.txt -t ./
zip -x unslackd.yaml -x *.git* -x *.DS_Store* -x */*.pyc* -x */__pycache__* -r unslackd.zip .
```
