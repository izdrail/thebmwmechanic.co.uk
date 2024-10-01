#!/bin/sh
# This is mainly for development
build:
	docker image rm -f izdrail/thebmwmechanic.co.uk:latest && docker build -t izdrail/thebmwmechanic.co.uk:latest --no-cache --progress=plain . --build-arg CACHEBUST=$(date +%s)
dev:
	docker-compose up
down:
	docker-compose down
ssh:
	docker exec -it thebmwmechanic.co.uk /bin/zsh
publish:
	docker push izdrail/thebmwmechanic.co.uk:latest
