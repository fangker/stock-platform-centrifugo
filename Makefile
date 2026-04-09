IMAGE_DIR := source/image
REDIS_IMAGE := redis:7-alpine
BRIDGE_IMAGE := centrifugo-bridge

.PHONY: build run push clean export-image

build:
	docker compose build bridge

run:
	docker compose up

push:
	docker tag $(IMAGE_NAME) $(IMAGE_NAME):$(TAG)
	docker push $(IMAGE_NAME):$(TAG)

clean:
	docker compose down -rmi local
	docker rmi $(IMAGE_NAME):$(TAG) 2>/dev/null || true

export-image: build | $(IMAGE_DIR)
	docker save $(REDIS_IMAGE) -o $(IMAGE_DIR)/redis-7-alpine.tar
	docker save $(BRIDGE_IMAGE) -o $(IMAGE_DIR)/centrifugo-bridge.tar

$(IMAGE_DIR):
	mkdir -p $(IMAGE_DIR)
