.PHONY: docker

builddocker:
	docker build -t lfixer-build-container -f Dockerfile.build .

deb:
	rm -rf out && mkdir out
	make builddocker
	docker run  -v $(PWD)/out/:/out lfixer-build-container

package:
	python3 setup.py --command-packages=stdeb.command bdist_deb
	cp /opt/lfixer/deb_dist/*deb /out

docker:
	make deb
	docker build -t lfixer -f Dockerfile .

flake:
	python3 -m flake8 bin/
	python3 -m flake8 lfixer/

test:
	python3 setup.py test

test_docker:
	make builddocker
	docker run --entrypoint='/usr/bin/python3' -e PYTHONPATH=/opt/lfixer lfixer-build-container -m lfixer.test
