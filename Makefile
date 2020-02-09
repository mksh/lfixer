.PHONY: docker


deb:
	rm -rf out && mkdir out
	docker build -t lfixer-build-container -f Dockerfile.build .
	docker run  -v $(PWD)/out/:/out lfixer-build-container

package:
	python3 setup.py --command-packages=stdeb.command bdist_deb
	cp /opt/lfixer/deb_dist/*deb /out

docker: deb
	docker build -t lfixer -f Dockerfile .

flake:
	flake8 bin/
	flake8 lfixer/
